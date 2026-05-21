"""Web3 Knowledge Graph pipeline.

This script implements the final-project proposal:
Web3 posts -> preprocessing -> entity extraction -> knowledge graph
construction -> community detection -> Neo4j/CSV/JSON/HTML exports.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

import pandas as pd

try:
    import networkx as nx
except ImportError as exc:  # pragma: no cover - user-facing runtime guard
    raise SystemExit(
        "networkx is required. Install dependencies with: pip install -r requirements.txt"
    ) from exc


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "data" / "sample_web3_posts.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "outputs"

STOPWORDS = {
    "a",
    "about",
    "after",
    "and",
    "are",
    "as",
    "at",
    "be",
    "because",
    "by",
    "can",
    "for",
    "from",
    "has",
    "in",
    "into",
    "is",
    "it",
    "new",
    "of",
    "on",
    "or",
    "said",
    "that",
    "the",
    "their",
    "to",
    "with",
}

ENTITY_STOPWORDS = {
    "A",
    "About",
    "After",
    "All",
    "An",
    "And",
    "Anyone",
    "Are",
    "As",
    "At",
    "Be",
    "Before",
    "Bookmarking",
    "But",
    "By",
    "Can",
    "Could",
    "Daily",
    "Discussion",
    "Do",
    "Does",
    "Don",
    "For",
    "From",
    "Get",
    "Giveaway",
    "Has",
    "Have",
    "Here",
    "How",
    "I",
    "If",
    "In",
    "Is",
    "It",
    "Just",
    "Learn",
    "Like",
    "Looking",
    "May",
    "Megathread",
    "Most",
    "My",
    "New",
    "No",
    "Not",
    "Now",
    "Of",
    "On",
    "One",
    "Or",
    "Please",
    "Post",
    "Question",
    "Should",
    "So",
    "Some",
    "That",
    "Thanks",
    "They",
    "The",
    "This",
    "To",
    "Today",
    "Trading",
    "Want",
    "We",
    "Welcome",
    "What",
    "When",
    "Where",
    "Who",
    "Why",
    "With",
    "Would",
    "You",
    "Your",
    "Everything",
    "Source",
    "Open",
    "Official",
    "Help",
}

ENTITY_TYPE_RULES = {
    "Aave": "Protocol",
    "Actively Validated Services": "Concept",
    "Arbitrum": "Layer2",
    "Avalanche": "Blockchain",
    "Aztec": "Protocol",
    "Base": "Layer2",
    "Binance": "Exchange",
    "Bitcoin": "Blockchain",
    "BlackRock": "Organization",
    "CCIP": "Protocol",
    "Chainlink": "Oracle",
    "Coinbase": "Exchange",
    "Curve": "Protocol",
    "DAI": "Stablecoin",
    "DeFi": "Topic",
    "DePIN": "Topic",
    "EigenLayer": "Protocol",
    "Ethereum": "Blockchain",
    "Fidelity": "Organization",
    "Immutable": "Protocol",
    "Jupiter": "Protocol",
    "Layer 2": "Topic",
    "Ledger": "Wallet",
    "Lido": "Protocol",
    "MakerDAO": "DAO",
    "NFT": "Topic",
    "Optimism": "Layer2",
    "Pectra": "Event",
    "Polygon": "Layer2",
    "Polygon zkEVM": "Layer2",
    "Renzo": "Protocol",
    "Ronin": "Blockchain",
    "SEC": "Regulator",
    "Solana": "Blockchain",
    "Starknet": "Layer2",
    "UNI": "Token",
    "US Treasury": "Organization",
    "USDC": "Stablecoin",
    "USDT": "Stablecoin",
    "Uniswap": "Protocol",
    "Uniswap DAO": "DAO",
    "United States": "Location",
    "zkSync": "Layer2",
    "ether.fi": "Protocol",
    "stETH": "Token",
}

TOPIC_KEYWORDS = {
    "DeFi": {"defi", "liquidity", "lending", "pools", "swaps", "yield", "slippage"},
    "Layer2 Scaling": {"layer", "rollups", "scaling", "fees", "zk", "zkevm"},
    "Governance": {"dao", "governance", "proposal", "votes", "delegates", "treasury"},
    "Security": {"phishing", "seed", "hardware", "wallet", "signing", "risk"},
    "NFT and Gaming": {"nft", "gaming", "marketplace", "assets", "player-owned"},
    "Institutional Crypto": {"etf", "institutional", "blackrock", "fidelity", "sec"},
    "Cross-chain": {"bridge", "bridges", "cross-chain", "interoperability", "ccip"},
    "Restaking": {"restaking", "avs", "validators", "validated", "eigenlayer"},
    "Stablecoins": {"stablecoin", "stablecoins", "usdc", "usdt", "dai"},
}


@dataclass(frozen=True)
class Entity:
    name: str
    entity_type: str


def normalize_text(value: object) -> str:
    text = "" if pd.isna(value) else str(value)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[^A-Za-z0-9\s\-\']", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_") or "unknown"


def load_posts(input_path: Path) -> pd.DataFrame:
    df = pd.read_csv(input_path)
    required = {"post_id", "subreddit", "title", "selftext", "created_utc", "score", "url"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Input CSV is missing required columns: {missing}")

    df = df.copy()
    df["title"] = df["title"].fillna("")
    df["selftext"] = df["selftext"].fillna("")
    df["raw_text"] = df["title"] + " " + df["selftext"]
    df["clean_text"] = df["raw_text"].map(normalize_text)
    return df


def extract_entities(text: str) -> list[Entity]:
    found: dict[str, Entity] = {}

    for name, entity_type in ENTITY_TYPE_RULES.items():
        if re.search(rf"\b{re.escape(name)}\b", text, flags=re.IGNORECASE):
            found[name] = Entity(name, entity_type)

    capital_phrases = re.findall(
        r"\b(?:[A-Z][A-Za-z0-9\-]+)(?:\s+(?:[A-Z][A-Za-z0-9\-]+))*\b", text
    )
    ignored = {
        "Analysts",
        "DAO",
        "Developers",
        "ETF",
        "Proposal",
        "Security",
        "URLs",
        "UX",
        "US",
        "Web3",
        "Ethereum DeFi",
    } | ENTITY_STOPWORDS
    for phrase in capital_phrases:
        phrase = phrase.strip()
        if phrase in ignored or len(phrase) <= 2:
            continue
        if phrase not in found:
            found[phrase] = Entity(phrase, infer_entity_type(phrase))

    return sorted(found.values(), key=lambda ent: ent.name)


def infer_entity_type(name: str) -> str:
    org_suffixes = ("Inc", "Corp", "Corporation", "University", "Agency")
    event_words = {"Conference", "Talks", "Election", "Elections", "Floods"}
    if any(name.endswith(suffix) for suffix in org_suffixes):
        return "Organization"
    if any(word in name.split() for word in event_words):
        return "Event"
    if len(name.split()) >= 2:
        return "Organization"
    return "Entity"


def extract_topics(text: str) -> list[str]:
    tokens = {token.lower() for token in re.findall(r"[A-Za-z][A-Za-z\-]+", text)}
    topics = [
        topic for topic, keywords in TOPIC_KEYWORDS.items() if tokens.intersection(keywords)
    ]
    return topics or ["Web3 General"]


def build_graph_tables(posts: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, nx.Graph]:
    nodes: dict[str, dict[str, object]] = {}
    edge_weights: dict[tuple[str, str, str], dict[str, object]] = {}
    entity_graph = nx.Graph()
    entity_counter: Counter[str] = Counter()

    def add_node(node_id: str, label: str, **attrs: object) -> None:
        current = nodes.setdefault(node_id, {"id": node_id, "label": label})
        current.update(attrs)

    def add_edge(
        source: str,
        target: str,
        relation: str,
        weight: float = 1.0,
        **attrs: object,
    ) -> None:
        key = (source, target, relation)
        current = edge_weights.setdefault(
            key,
            {
                "source": source,
                "target": target,
                "relation": relation,
                "weight": 0.0,
            },
        )
        current["weight"] = float(current["weight"]) + weight
        current.update(attrs)

    for _, post in posts.iterrows():
        post_id = f"post_{post.post_id}"
        add_node(
            post_id,
            "Post",
            name=post.title,
            post_id=post.post_id,
            subreddit=post.subreddit,
            score=int(post.score),
            created_utc=str(post.created_utc),
            url=post.url,
        )

        entities = extract_entities(post.raw_text)
        topics = extract_topics(post.clean_text)
        entity_ids = []

        for entity in entities:
            entity_id = f"entity_{slugify(entity.name)}"
            entity_ids.append(entity_id)
            entity_counter[entity.name] += 1
            add_node(
                entity_id,
                "Entity",
                name=entity.name,
                entity_type=entity.entity_type,
                mentions=int(entity_counter[entity.name]),
            )
            add_edge(post_id, entity_id, "MENTIONS", 1.0)
            entity_graph.add_node(entity_id, name=entity.name, entity_type=entity.entity_type)

        for left, right in combinations(sorted(set(entity_ids)), 2):
            add_edge(left, right, "CO_MENTIONED_WITH", 1.0)
            if entity_graph.has_edge(left, right):
                entity_graph[left][right]["weight"] += 1
            else:
                entity_graph.add_edge(left, right, weight=1)

        for topic in topics:
            topic_id = f"topic_{slugify(topic)}"
            add_node(topic_id, "Topic", name=topic, entity_type="Topic")
            for entity_id in entity_ids:
                add_edge(entity_id, topic_id, "BELONGS_TO", 1.0)

    community_map = detect_communities(entity_graph)
    for node_id, community_id in community_map.items():
        nodes[node_id]["community"] = community_id

    nodes_df = pd.DataFrame(nodes.values()).fillna("")
    edges_df = pd.DataFrame(edge_weights.values()).fillna("")
    return nodes_df, edges_df, entity_graph


def detect_communities(graph: nx.Graph) -> dict[str, int]:
    if graph.number_of_nodes() == 0:
        return {}

    try:
        communities = nx.community.louvain_communities(graph, weight="weight", seed=7)
        method = "louvain"
    except Exception:
        try:
            communities = nx.community.greedy_modularity_communities(graph, weight="weight")
            method = "greedy_modularity"
        except Exception:
            communities = list(nx.community.label_propagation_communities(graph))
            method = "label_propagation"

    community_map = {}
    for community_id, community_nodes in enumerate(communities):
        for node_id in community_nodes:
            community_map[node_id] = community_id
    graph.graph["community_method"] = method
    return community_map


def cypher_escape(value: object) -> str:
    return str(value).replace("\\", "\\\\").replace("'", "\\'")


def export_neo4j_cypher(nodes_df: pd.DataFrame, edges_df: pd.DataFrame, output_path: Path) -> None:
    lines = [
        "// Generated by web3_kg_project/src/pipeline.py",
        "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (n:KGNode) REQUIRE n.id IS UNIQUE;",
        "",
    ]

    for _, node in nodes_df.iterrows():
        label = node["label"]
        props = {
            key: value
            for key, value in node.items()
            if key not in {"label"} and value != "" and not (isinstance(value, float) and math.isnan(value))
        }
        prop_text = ", ".join(
            f"{key}: '{cypher_escape(value)}'" if not isinstance(value, (int, float)) else f"{key}: {value}"
            for key, value in props.items()
        )
        lines.append(f"MERGE (n:{label}:KGNode {{id: '{cypher_escape(node['id'])}'}}) SET n += {{{prop_text}}};")

    lines.append("")
    for _, edge in edges_df.iterrows():
        relation = edge["relation"]
        weight = float(edge["weight"])
        lines.append(
            "MATCH (a:KGNode {id: '"
            + cypher_escape(edge["source"])
            + "'}), (b:KGNode {id: '"
            + cypher_escape(edge["target"])
            + "'}) "
            + f"MERGE (a)-[r:{relation}]->(b) SET r.weight = {weight:.5f};"
        )

    output_path.write_text("\n".join(lines), encoding="utf-8")


def export_graph_json(nodes_df: pd.DataFrame, edges_df: pd.DataFrame, output_path: Path) -> None:
    graph = {
        "nodes": nodes_df.to_dict(orient="records"),
        "edges": edges_df.to_dict(orient="records"),
    }
    output_path.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")


def export_summary(
    posts: pd.DataFrame,
    nodes_df: pd.DataFrame,
    edges_df: pd.DataFrame,
    graph: nx.Graph,
    output_path: Path,
) -> None:
    entity_nodes = nodes_df[nodes_df["label"] == "Entity"].copy()
    entity_nodes["mentions"] = pd.to_numeric(entity_nodes["mentions"], errors="coerce").fillna(0)
    top_entities = entity_nodes.sort_values(["mentions", "name"], ascending=[False, True]).head(10)

    comention_edges = edges_df[edges_df["relation"] == "CO_MENTIONED_WITH"].copy()
    comention_edges["weight"] = pd.to_numeric(comention_edges["weight"], errors="coerce").fillna(0)
    top_edges = comention_edges.sort_values("weight", ascending=False).head(10)

    id_to_name = dict(zip(nodes_df["id"], nodes_df["name"]))
    method = graph.graph.get("community_method", "unknown")

    lines = [
        "# Analysis Summary",
        "",
        f"- Posts analyzed: {len(posts)}",
        f"- Nodes exported: {len(nodes_df)}",
        f"- Edges exported: {len(edges_df)}",
        f"- Entity graph nodes: {graph.number_of_nodes()}",
        f"- Entity graph edges: {graph.number_of_edges()}",
        f"- Community detection method: {method}",
        "",
        "## Top Entities",
        "",
        "| Entity | Type | Mentions | Community |",
        "|---|---:|---:|---:|",
    ]
    for _, row in top_entities.iterrows():
        lines.append(
            f"| {row['name']} | {row['entity_type']} | {int(row['mentions'])} | {row.get('community', '')} |"
        )

    lines += ["", "## Strongest Co-Mention Relationships", "", "| Source | Target | Weight |", "|---|---|---:|"]
    for _, row in top_edges.iterrows():
        lines.append(
            f"| {id_to_name.get(row['source'], row['source'])} | {id_to_name.get(row['target'], row['target'])} | {row['weight']:.0f} |"
        )

    output_path.write_text("\n".join(lines), encoding="utf-8")


def export_html(nodes_df: pd.DataFrame, edges_df: pd.DataFrame, output_path: Path) -> None:
    entity_nodes = nodes_df[nodes_df["label"].isin(["Entity", "Topic"])].copy()
    entity_nodes["mentions_numeric"] = pd.to_numeric(
        entity_nodes.get("mentions", 0), errors="coerce"
    ).fillna(0)
    if len(entity_nodes) > 120:
        topic_nodes = entity_nodes[entity_nodes["label"] == "Topic"]
        top_entities = entity_nodes[entity_nodes["label"] == "Entity"].sort_values(
            ["mentions_numeric", "name"], ascending=[False, True]
        ).head(90)
        entity_nodes = pd.concat([top_entities, topic_nodes], ignore_index=True).drop_duplicates(
            subset=["id"]
        )
    display_node_ids = set(entity_nodes["id"])
    display_edges = edges_df[
        edges_df["source"].isin(display_node_ids) & edges_df["target"].isin(display_node_ids)
    ].copy()

    palette = {
        "Entity": "#4C78A8",
        "Topic": "#F58518",
        "Organization": "#54A24B",
        "Location": "#E45756",
        "Product": "#B279A2",
        "Event": "#72B7B2",
    }

    nodes_payload = []
    for _, row in entity_nodes.iterrows():
        entity_type = row.get("entity_type", row["label"]) or row["label"]
        nodes_payload.append(
            {
                "id": row["id"],
                "name": row["name"],
                "label": row["label"],
                "entity_type": entity_type,
                "community": row.get("community", ""),
                "mentions": row.get("mentions", ""),
                "color": palette.get(entity_type, palette.get(row["label"], "#999999")),
            }
        )

    edges_payload = display_edges.to_dict(orient="records")
    html_doc = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Web3 Knowledge Graph</title>
  <style>
    body {{ margin: 0; font-family: Arial, sans-serif; background: #f7f8fb; color: #1f2937; }}
    header {{ padding: 16px 22px; background: #ffffff; border-bottom: 1px solid #d8dee9; }}
    h1 {{ margin: 0; font-size: 22px; }}
    #wrap {{ display: grid; grid-template-columns: 1fr 320px; height: calc(100vh - 66px); }}
    #graph {{ width: 100%; height: 100%; background: #fbfcfe; }}
    aside {{ border-left: 1px solid #d8dee9; background: white; padding: 16px; overflow: auto; }}
    .legend {{ display: grid; gap: 8px; margin-top: 12px; }}
    .legend div {{ display: flex; align-items: center; gap: 8px; font-size: 13px; }}
    .swatch {{ width: 12px; height: 12px; border-radius: 3px; display: inline-block; }}
    .metric {{ padding: 10px 0; border-bottom: 1px solid #edf0f5; }}
    .metric strong {{ display: block; font-size: 20px; }}
    svg text {{ font-size: 11px; pointer-events: none; }}
    .link {{ stroke: #aeb7c2; stroke-opacity: 0.6; }}
    .node {{ stroke: white; stroke-width: 1.5px; cursor: pointer; }}
  </style>
</head>
<body>
  <header><h1>Web3 Knowledge Graph - Protocol, Chain, DAO, and Topic Network</h1></header>
  <div id="wrap">
    <svg id="graph"></svg>
    <aside>
      <div class="metric"><strong>{len(nodes_payload)}</strong> displayed entity/topic nodes</div>
      <div class="metric"><strong>{len(edges_payload)}</strong> displayed relationships</div>
      <h2>Legend</h2>
      <div class="legend" id="legend"></div>
      <h2>Selected Node</h2>
      <p id="details">Click a node to inspect it.</p>
    </aside>
  </div>
<script>
const nodes = {json.dumps(nodes_payload, ensure_ascii=False)};
const links = {json.dumps(edges_payload, ensure_ascii=False)};
const svg = document.getElementById("graph");
const details = document.getElementById("details");
const width = svg.clientWidth || 900;
const height = svg.clientHeight || 650;
svg.setAttribute("viewBox", `0 0 ${{width}} ${{height}}`);

const types = [...new Map(nodes.map(n => [n.entity_type, n.color])).entries()];
document.getElementById("legend").innerHTML = types.map(([name, color]) =>
  `<div><span class="swatch" style="background:${{color}}"></span>${{name}}</div>`
).join("");

const degree = Object.fromEntries(nodes.map(n => [n.id, 0]));
links.forEach(l => {{ degree[l.source] = (degree[l.source] || 0) + 1; degree[l.target] = (degree[l.target] || 0) + 1; }});
nodes.forEach((node, i) => {{
  const angle = (2 * Math.PI * i) / nodes.length;
  const radius = Math.min(width, height) * (0.25 + 0.2 * ((Number(node.community) || 0) % 3) / 3);
  node.x = width / 2 + Math.cos(angle) * radius;
  node.y = height / 2 + Math.sin(angle) * radius;
}});

function tick() {{
  for (let iter = 0; iter < 160; iter++) {{
    for (const link of links) {{
      const a = nodes.find(n => n.id === link.source);
      const b = nodes.find(n => n.id === link.target);
      if (!a || !b) continue;
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const target = link.relation === "BELONGS_TO" ? 120 : 180;
      const force = (dist - target) * 0.002;
      a.x += dx * force; a.y += dy * force;
      b.x -= dx * force; b.y -= dy * force;
    }}
    for (let i = 0; i < nodes.length; i++) {{
      for (let j = i + 1; j < nodes.length; j++) {{
        const a = nodes[i], b = nodes[j];
        const dx = b.x - a.x, dy = b.y - a.y;
        const dist2 = dx * dx + dy * dy || 1;
        const force = Math.min(2.5, 240 / dist2);
        a.x -= dx * force; a.y -= dy * force;
        b.x += dx * force; b.y += dy * force;
      }}
    }}
    for (const n of nodes) {{
      n.x += (width / 2 - n.x) * 0.003;
      n.y += (height / 2 - n.y) * 0.003;
      n.x = Math.max(24, Math.min(width - 24, n.x));
      n.y = Math.max(24, Math.min(height - 24, n.y));
    }}
  }}
}}
tick();

function line(x1, y1, x2, y2, width) {{
  return `<line class="link" x1="${{x1}}" y1="${{y1}}" x2="${{x2}}" y2="${{y2}}" stroke-width="${{width}}"></line>`;
}}
function circle(n) {{
  const r = 7 + Math.min(10, degree[n.id] || 0);
  const title = `${{n.name}}\\n${{n.entity_type}}\\ncommunity: ${{n.community}}`;
  return `<g><circle class="node" data-id="${{n.id}}" cx="${{n.x}}" cy="${{n.y}}" r="${{r}}" fill="${{n.color}}"><title>${{title}}</title></circle><text x="${{n.x + r + 3}}" y="${{n.y + 4}}">${{n.name}}</text></g>`;
}}
const nodeById = Object.fromEntries(nodes.map(n => [n.id, n]));
svg.innerHTML =
  links.map(l => {{
    const a = nodeById[l.source], b = nodeById[l.target];
    if (!a || !b) return "";
    return line(a.x, a.y, b.x, b.y, 1 + Math.min(4, Number(l.weight) || 1));
  }}).join("") + nodes.map(circle).join("");

svg.addEventListener("click", event => {{
  if (!event.target.classList.contains("node")) return;
  const n = nodeById[event.target.dataset.id];
  details.innerHTML = `<strong>${{n.name}}</strong><br>Type: ${{n.entity_type}}<br>Community: ${{n.community || "N/A"}}<br>Mentions: ${{n.mentions || "N/A"}}`;
}});
</script>
</body>
</html>"""
    output_path.write_text(html_doc, encoding="utf-8")


def run_pipeline(input_path: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    posts = load_posts(input_path)
    nodes_df, edges_df, graph = build_graph_tables(posts)

    nodes_df.to_csv(output_dir / "nodes.csv", index=False, quoting=csv.QUOTE_MINIMAL)
    edges_df.to_csv(output_dir / "edges.csv", index=False, quoting=csv.QUOTE_MINIMAL)
    export_graph_json(nodes_df, edges_df, output_dir / "graph.json")
    export_neo4j_cypher(nodes_df, edges_df, output_dir / "neo4j_import.cypher")
    export_summary(posts, nodes_df, edges_df, graph, output_dir / "analysis_summary.md")
    export_html(nodes_df, edges_df, output_dir / "interactive_graph.html")

    print(f"Input posts: {len(posts)}")
    print(f"Nodes: {len(nodes_df)}")
    print(f"Edges: {len(edges_df)}")
    print(f"Community method: {graph.graph.get('community_method', 'unknown')}")
    print(f"Outputs written to: {output_dir}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a Web3 knowledge graph.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Input CSV path")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output directory")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_pipeline(args.input, args.output)
