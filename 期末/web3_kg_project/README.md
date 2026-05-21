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

## Crawl Live Reddit Web3 Posts

```powershell
python .\src\reddit_crawler.py --subreddits ethereum defi CryptoCurrency solana web3 NFT --posts-per-subreddit 15 --output .\data\reddit_web3_posts.csv
python .\src\pipeline.py --input .\data\reddit_web3_posts.csv --output .\outputs\reddit_live
python -m http.server 8080
```

Open:

```text
http://localhost:8080/outputs/reddit_live/interactive_graph.html
```

Crawler tutorial notebook:

```text
docs/Reddit_Web3_Crawler_Tutorial.ipynb
```

## Outputs

- `outputs/nodes.csv`
- `outputs/edges.csv`
- `outputs/graph.json`
- `outputs/neo4j_import.cypher`
- `outputs/interactive_graph.html`
- `outputs/analysis_summary.md`
- `outputs/reddit_live/interactive_graph.html` when using crawled Reddit data

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
