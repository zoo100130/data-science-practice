"""Reddit crawler for Web3 Knowledge Graph.

This crawler uses Reddit's public JSON listing endpoint, so it can run without
OAuth credentials for classroom demos. Respect Reddit's rules and rate limits:
keep request volume small, identify your script with a User-Agent, and avoid
collecting private or personal data.
"""

from __future__ import annotations

import argparse
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "reddit_web3_posts.csv"
DEFAULT_SUBREDDITS = [
    "ethereum",
    "defi",
    "CryptoCurrency",
    "solana",
    "web3",
    "NFT",
]
DEFAULT_USER_AGENT = "web3-kg-coursework/1.0 by zoo100130"
OUTPUT_COLUMNS = [
    "post_id",
    "content_type",
    "parent_post_id",
    "comment_id",
    "subreddit",
    "title",
    "selftext",
    "created_utc",
    "score",
    "url",
    "permalink",
    "num_comments",
    "author",
    "upvote_ratio",
    "stickied",
]


def format_reddit_date(created_utc: object) -> str:
    if not created_utc:
        return ""
    return datetime.fromtimestamp(float(created_utc), tz=timezone.utc).date().isoformat()


def fetch_json(
    url: str,
    params: dict[str, object],
    timeout: int = 20,
    user_agent: str = DEFAULT_USER_AGENT,
) -> object:
    response = requests.get(
        url,
        params=params,
        headers={"User-Agent": user_agent},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def fetch_listing(
    subreddit: str,
    sort: str = "hot",
    limit: int = 25,
    after: str | None = None,
    timeout: int = 20,
    user_agent: str = DEFAULT_USER_AGENT,
) -> dict:
    url = f"https://www.reddit.com/r/{subreddit}/{sort}.json"
    params = {"limit": min(limit, 100)}
    if after:
        params["after"] = after

    payload = fetch_json(url, params=params, timeout=timeout, user_agent=user_agent)
    return payload if isinstance(payload, dict) else {}


def fetch_comments(
    post_id: str,
    limit: int,
    depth: int,
    sort: str,
    timeout: int = 20,
    user_agent: str = DEFAULT_USER_AGENT,
) -> list:
    url = f"https://www.reddit.com/comments/{post_id}.json"
    params = {
        "limit": min(max(limit, 1), 500),
        "depth": max(depth, 1),
        "sort": sort,
    }
    payload = fetch_json(url, params=params, timeout=timeout, user_agent=user_agent)
    return payload if isinstance(payload, list) else []


def parse_post(child: dict) -> dict:
    data = child.get("data", {})

    return {
        "post_id": data.get("id", ""),
        "content_type": "post",
        "parent_post_id": "",
        "comment_id": "",
        "subreddit": data.get("subreddit", ""),
        "title": data.get("title", ""),
        "selftext": data.get("selftext", "") or "",
        "created_utc": format_reddit_date(data.get("created_utc")),
        "score": data.get("score", 0),
        "url": data.get("url", ""),
        "permalink": "https://www.reddit.com" + data.get("permalink", ""),
        "num_comments": data.get("num_comments", 0),
        "author": data.get("author", ""),
        "upvote_ratio": data.get("upvote_ratio", ""),
        "stickied": bool(data.get("stickied", False)),
    }


def parse_comment(child: dict, parent_post: dict) -> dict:
    data = child.get("data", {})
    comment_id = data.get("id", "")
    body = data.get("body", "") or ""
    parent_title = str(parent_post.get("title", ""))[:120]

    return {
        "post_id": comment_id,
        "content_type": "comment",
        "parent_post_id": parent_post.get("post_id", ""),
        "comment_id": comment_id,
        "subreddit": data.get("subreddit", parent_post.get("subreddit", "")),
        "title": f"Comment on: {parent_title}",
        "selftext": body,
        "created_utc": format_reddit_date(data.get("created_utc")),
        "score": data.get("score", 0),
        "url": parent_post.get("url", ""),
        "permalink": "https://www.reddit.com" + data.get("permalink", ""),
        "num_comments": 0,
        "author": data.get("author", ""),
        "upvote_ratio": "",
        "stickied": bool(data.get("stickied", False)),
    }


def is_noise_post(row: dict) -> bool:
    title = str(row.get("title", "")).lower()
    if row.get("stickied"):
        return True
    noise_terms = [
        "daily discussion",
        "general discussion",
        "weekly discussion",
        "megathread",
        "welcome to",
        "subreddit rules",
    ]
    return any(term in title for term in noise_terms)


def is_noise_comment(row: dict) -> bool:
    body = str(row.get("selftext", "")).strip().lower()
    return not body or body in {"[deleted]", "[removed]"} or row.get("stickied")


def iter_comment_children(children: Iterable[dict]) -> Iterable[dict]:
    for child in children:
        if child.get("kind") != "t1":
            continue
        yield child
        replies = child.get("data", {}).get("replies")
        if isinstance(replies, dict):
            nested_children = replies.get("data", {}).get("children", [])
            yield from iter_comment_children(nested_children)


def crawl_comments_for_post(
    parent_post: dict,
    comments_per_post: int,
    comment_depth: int,
    comment_sort: str,
    user_agent: str,
) -> list[dict]:
    if comments_per_post <= 0:
        return []

    payload = fetch_comments(
        post_id=str(parent_post["post_id"]),
        limit=max(comments_per_post * 3, 10),
        depth=comment_depth,
        sort=comment_sort,
        user_agent=user_agent,
    )
    if len(payload) < 2 or not isinstance(payload[1], dict):
        return []

    rows: list[dict] = []
    listing = payload[1].get("data", {})
    for child in iter_comment_children(listing.get("children", [])):
        row = parse_comment(child, parent_post)
        if not is_noise_comment(row):
            rows.append(row)
        if len(rows) >= comments_per_post:
            break
    return rows


def crawl_subreddit(
    subreddit: str,
    sort: str,
    target_posts: int,
    page_limit: int,
    sleep_seconds: float,
    include_stickied: bool,
    comments_per_post: int,
    comment_depth: int,
    comment_sort: str,
    user_agent: str,
) -> list[dict]:
    post_rows: list[dict] = []
    after = None

    while len(post_rows) < target_posts:
        payload = fetch_listing(
            subreddit,
            sort=sort,
            limit=page_limit,
            after=after,
            user_agent=user_agent,
        )
        listing = payload.get("data", {})
        children = listing.get("children", [])
        if not children:
            break

        for child in children:
            if child.get("kind") == "t3":
                row = parse_post(child)
                if include_stickied or not is_noise_post(row):
                    post_rows.append(row)
            if len(post_rows) >= target_posts:
                break

        after = listing.get("after")
        if not after:
            break
        time.sleep(sleep_seconds)

    rows: list[dict] = []
    for post_row in post_rows:
        rows.append(post_row)
        if comments_per_post <= 0:
            continue
        try:
            comment_rows = crawl_comments_for_post(
                parent_post=post_row,
                comments_per_post=comments_per_post,
                comment_depth=comment_depth,
                comment_sort=comment_sort,
                user_agent=user_agent,
            )
            rows.extend(comment_rows)
        except requests.HTTPError as exc:
            print(
                f"    skipped comments for {post_row['post_id']}: "
                f"HTTP {exc.response.status_code}"
            )
        except requests.RequestException as exc:
            print(f"    skipped comments for {post_row['post_id']}: {exc}")
        time.sleep(sleep_seconds)

    return rows


def crawl_many(
    subreddits: Iterable[str],
    sort: str,
    posts_per_subreddit: int,
    page_limit: int,
    sleep_seconds: float,
    include_stickied: bool,
    comments_per_post: int,
    comment_depth: int,
    comment_sort: str,
    user_agent: str,
) -> pd.DataFrame:
    all_rows: list[dict] = []
    for subreddit in subreddits:
        print(f"Crawling r/{subreddit} ({sort})...")
        try:
            rows = crawl_subreddit(
                subreddit=subreddit,
                sort=sort,
                target_posts=posts_per_subreddit,
                page_limit=page_limit,
                sleep_seconds=sleep_seconds,
                include_stickied=include_stickied,
                comments_per_post=comments_per_post,
                comment_depth=comment_depth,
                comment_sort=comment_sort,
                user_agent=user_agent,
            )
            post_count = sum(row.get("content_type") == "post" for row in rows)
            comment_count = sum(row.get("content_type") == "comment" for row in rows)
            print(f"  fetched {post_count} posts and {comment_count} comments")
            all_rows.extend(rows)
        except requests.HTTPError as exc:
            print(f"  skipped r/{subreddit}: HTTP {exc.response.status_code}")
        except requests.RequestException as exc:
            print(f"  skipped r/{subreddit}: {exc}")
        time.sleep(sleep_seconds)

    df = pd.DataFrame(all_rows)
    if df.empty:
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    for column in OUTPUT_COLUMNS:
        if column not in df.columns:
            df[column] = ""
    df = df[OUTPUT_COLUMNS]
    df["score"] = pd.to_numeric(df["score"], errors="coerce").fillna(0).astype(int)
    df["_thread_id"] = df["parent_post_id"].where(df["parent_post_id"] != "", df["post_id"])
    df["_content_order"] = df["content_type"].map({"post": 0, "comment": 1}).fillna(2)
    df = (
        df.drop_duplicates(subset=["content_type", "post_id"])
        .sort_values(
            ["subreddit", "_thread_id", "_content_order", "score"],
            ascending=[True, True, True, False],
        )
        .drop(columns=["_thread_id", "_content_order"])
    )
    return df.reset_index(drop=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Crawl Reddit Web3 posts to CSV.")
    parser.add_argument(
        "--subreddits",
        nargs="+",
        default=DEFAULT_SUBREDDITS,
        help="Subreddits to crawl, without r/ prefix.",
    )
    parser.add_argument("--sort", default="hot", choices=["hot", "new", "top", "rising"])
    parser.add_argument("--posts-per-subreddit", type=int, default=20)
    parser.add_argument("--page-limit", type=int, default=25)
    parser.add_argument("--sleep-seconds", type=float, default=1.0)
    parser.add_argument(
        "--comments-per-post",
        type=int,
        default=0,
        help="Top-level and nested comments to collect for each post. Use 0 to skip comments.",
    )
    parser.add_argument("--comment-depth", type=int, default=2)
    parser.add_argument(
        "--comment-sort",
        default="top",
        choices=["confidence", "top", "new", "controversial", "old", "qa"],
    )
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    parser.add_argument(
        "--include-stickied",
        action="store_true",
        help="Include stickied and recurring discussion posts.",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    df = crawl_many(
        subreddits=args.subreddits,
        sort=args.sort,
        posts_per_subreddit=args.posts_per_subreddit,
        page_limit=args.page_limit,
        sleep_seconds=args.sleep_seconds,
        include_stickied=args.include_stickied,
        comments_per_post=args.comments_per_post,
        comment_depth=args.comment_depth,
        comment_sort=args.comment_sort,
        user_agent=args.user_agent,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(f"Saved {len(df)} rows to {args.output}")


if __name__ == "__main__":
    main()
