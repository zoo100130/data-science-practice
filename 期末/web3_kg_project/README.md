# Web3 Knowledge Graph

This project builds an offline runnable Web3 knowledge graph prototype.

It converts Web3 / crypto / DeFi posts into graph data:

1. Load Web3 post data from CSV.
2. Clean text.
3. Extract Web3 entities and topics.
4. Build nodes and relationships.
5. Run community detection.
6. Export CSV, JSON, Neo4j Cypher, Markdown summary, and an interactive HTML graph.

## Quick Start

```powershell
cd "C:\Users\haushuk\Desktop\資料科學實務\期末\web3_kg_project"
python .\src\pipeline.py
python -m http.server 8080
```

Then open:

```text
http://localhost:8080/outputs/interactive_graph.html
```

## Outputs

- `outputs/nodes.csv`
- `outputs/edges.csv`
- `outputs/graph.json`
- `outputs/neo4j_import.cypher`
- `outputs/interactive_graph.html`
- `outputs/analysis_summary.md`

## Replace With Your Own Data

Your CSV should contain:

- `post_id`
- `subreddit`
- `title`
- `selftext`
- `created_utc`
- `score`
- `url`

Run:

```powershell
python .\src\pipeline.py --input .\data\your_web3_posts.csv --output .\outputs
```
