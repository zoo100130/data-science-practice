# News Knowledge Graph with Neo4j

This project implements the final proposal shown in `Group1_KnowledgeGraph_Proposal .pptx`.

It builds a news-oriented knowledge graph from Reddit-like posts:

1. Collect or load Reddit/news posts.
2. Clean and preprocess text.
3. Extract named entities and topics.
4. Build graph nodes and relationships.
5. Run community detection.
6. Export Neo4j Cypher, CSV, JSON, and an interactive HTML graph.

## Quick Start

```powershell
cd "C:\Users\haushuk\Desktop\資料科學實務\期末\news_kg_project"
python .\src\pipeline.py
```

Outputs are written to `outputs/`:

- `nodes.csv`
- `edges.csv`
- `graph.json`
- `neo4j_import.cypher`
- `interactive_graph.html`
- `analysis_summary.md`

## Use Your Own Reddit Export

Prepare a CSV with these columns:

- `post_id`
- `subreddit`
- `title`
- `selftext`
- `created_utc`
- `score`
- `url`

Then run:

```powershell
python .\src\pipeline.py --input .\data\your_posts.csv --output .\outputs
```

## Neo4j Import

Open Neo4j Browser and paste the content of:

```text
outputs/neo4j_import.cypher
```

The generated graph contains:

- `Post` nodes
- `Entity` nodes
- `Topic` nodes
- `MENTIONS`, `CO_MENTIONED_WITH`, and `BELONGS_TO` relationships

## Notes

The pipeline uses a deterministic rule-based entity extractor so the prototype can run offline without a Reddit API key or spaCy model. The development document explains how to replace it with PRAW and spaCy/CKIP in a production version.
