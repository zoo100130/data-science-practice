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


def fetch_listing(
    subreddit: str,
    sort: str = "hot",
    limit: int = 25,
    after: str | None = None,
    timeout: int = 20,
    user_agent: str = "web3-kg-coursework/1.0 by zoo100130",
) -> dict:
    url = f"https://www.reddit.com/r/{subreddit}/{sort}.json"
    params = {"limit": min(limit, 100)}
    if after:
        params["after"] = after

    response = requests.get(
        url,
        params=params,
        headers={"User-Agent": user_agent},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def parse_post(child: dict) -> dict:
    data = child.get("data", {})
    created_utc = data.get("created_utc")
    if created_utc:
        created_value = datetime.fromtimestamp(created_utc, tz=timezone.utc).date().isoformat()
    else:
        created_value = ""

    return {
        "post_id": data.get("id", ""),
        "subreddit": data.get("subreddit", ""),
        "title": data.get("title", ""),
        "selftext": data.get("selftext", "") or "",
        "created_utc": created_value,
        "score": data.get("score", 0),
        "url": data.get("url", ""),
        "permalink": "https://www.reddit.com" + data.get("permalink", ""),
        "num_comments": data.get("num_comments", 0),
        "author": data.get("author", ""),
        "upvote_ratio": data.get("upvote_ratio", ""),
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


def crawl_subreddit(
    subreddit: str,
    sort: str,
    target_posts: int,
    page_limit: int,
    sleep_seconds: float,
    include_stickied: bool,
) -> list[dict]:
    rows: list[dict] = []
    after = None

    while len(rows) < target_posts:
        payload = fetch_listing(subreddit, sort=sort, limit=page_limit, after=after)
        listing = payload.get("data", {})
        children = listing.get("children", [])
        if not children:
            break

        for child in children:
            if child.get("kind") == "t3":
                row = parse_post(child)
                if include_stickied or not is_noise_post(row):
                    rows.append(row)
            if len(rows) >= target_posts:
                break

        after = listing.get("after")
        if not after:
            break
        time.sleep(sleep_seconds)

    return rows


def crawl_many(
    subreddits: Iterable[str],
    sort: str,
    posts_per_subreddit: int,
    page_limit: int,
    sleep_seconds: float,
    include_stickied: bool,
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
            )
            print(f"  fetched {len(rows)} posts")
            all_rows.extend(rows)
        except requests.HTTPError as exc:
            print(f"  skipped r/{subreddit}: HTTP {exc.response.status_code}")
        except requests.RequestException as exc:
            print(f"  skipped r/{subreddit}: {exc}")
        time.sleep(sleep_seconds)

    df = pd.DataFrame(all_rows)
    if df.empty:
        return pd.DataFrame(
            columns=[
                "post_id",
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
        )

    df = df.drop_duplicates(subset=["post_id"]).sort_values(
        ["subreddit", "score"], ascending=[True, False]
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
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(f"Saved {len(df)} posts to {args.output}")


if __name__ == "__main__":
    main()
