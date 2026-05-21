# News Knowledge Graph Development Process

## 1. Project Goal

Build a news knowledge graph from Reddit-style social media posts. The graph should reveal hidden relationships among people, organizations, locations, events, and topics, and support community detection for discovering topical clusters.

## 2. Requirement Source

The development plan is based on the proposal slides:

- Data source: Reddit API or web scraping.
- Processing: text cleaning, tokenization, filtering, and named entity recognition.
- Graph database: Neo4j and Cypher.
- Algorithms: Louvain and Label Propagation.
- Visualization: Neo4j Bloom, Gephi, or Pyvis-style interactive graph.
- Language and tools: Python, PRAW, py2neo or Neo4j driver, spaCy or CKIP.

## 3. Scope for the Completed Prototype

The prototype implements the full pipeline offline:

- Loads a sample Reddit/news CSV.
- Cleans title and body text.
- Extracts entities and assigns entity types.
- Extracts high-level topics.
- Builds post, entity, and topic nodes.
- Builds mention, co-mention, and topic relationships.
- Runs community detection on the entity co-occurrence graph.
- Exports CSV, JSON, Neo4j Cypher, Markdown summary, and interactive HTML visualization.

The design intentionally supports replacing the sample CSV with real Reddit data later.

## 4. Data Flow

```text
Reddit/API or CSV
  -> raw posts
  -> text preprocessing
  -> entity and topic extraction
  -> graph node and edge construction
  -> community detection
  -> Neo4j / CSV / JSON / HTML outputs
```

## 5. Module Design

| Module | Responsibility | Output |
|---|---|---|
| `pipeline.py` | End-to-end orchestration | All artifacts |
| Data loader | Read Reddit-style CSV | post records |
| Preprocessor | Clean titles and post bodies | normalized text |
| Entity extractor | Identify person, org, location, event, and product entities | entity list per post |
| Graph builder | Create nodes and relationships | graph tables |
| Community detector | Detect topical graph communities | community id per entity |
| Exporters | Write Neo4j Cypher, CSV, JSON, summary, and HTML | deliverables |

## 6. Entity and Relationship Model

### Node Labels

- `Post`
- `Entity`
- `Topic`

### Entity Types

- `Person`
- `Organization`
- `Location`
- `Event`
- `Product`
- `Topic`

### Relationship Types

- `(:Post)-[:MENTIONS]->(:Entity)`
- `(:Entity)-[:CO_MENTIONED_WITH]->(:Entity)`
- `(:Entity)-[:BELONGS_TO]->(:Topic)`

## 7. Algorithm Strategy

The prototype uses NetworkX for community detection when available.

Priority order:

1. Louvain community detection if supported by the installed NetworkX version.
2. Greedy modularity as a fallback.
3. Label propagation as a final fallback.

This keeps the project aligned with the proposal while remaining runnable on a normal laptop.

## 8. Development Steps

1. Initialize project folder and sample dataset.
2. Implement ingestion and preprocessing.
3. Implement rule-based NER fallback.
4. Build nodes and relationships.
5. Run community detection.
6. Export Neo4j Cypher and analysis tables.
7. Generate an interactive HTML visualization.
8. Verify outputs and document the workflow.

## 9. Testing and Verification

Verification checks:

- Pipeline runs without external API credentials.
- `nodes.csv`, `edges.csv`, `graph.json`, and `neo4j_import.cypher` are created.
- Graph contains post, entity, and topic nodes.
- Top entities and communities are reported in `analysis_summary.md`.
- `interactive_graph.html` opens locally and displays nodes and edges.

## 10. Future Improvements

- Replace sample CSV with PRAW-based Reddit collection.
- Use spaCy or CKIP for stronger named entity recognition.
- Store data directly into Neo4j with the official Neo4j Python driver.
- Add date filtering, subreddit filtering, and topic trend charts.
- Build a dashboard for non-technical users.
