# News Knowledge Graph 教學文檔

本教學帶你從零開始執行 `news_kg_project`，完成一個以 Reddit/news 貼文為資料來源的新聞知識圖譜原型。完成後你會得到節點表、關係表、Neo4j 匯入腳本、分析摘要，以及可直接用瀏覽器打開的互動圖譜。

## 1. 專案會做什麼

這個專案把新聞或 Reddit 貼文轉換成知識圖譜：

1. 讀取 Reddit/news CSV。
2. 清理標題與內文。
3. 抽取實體，例如人物、組織、地點、事件、產品。
4. 抽取主題，例如 AI、Semiconductors、Geopolitics。
5. 建立圖譜節點與關係。
6. 使用 Louvain 社群偵測找出主題群。
7. 匯出 Neo4j、CSV、JSON、HTML 視覺化與 Markdown 摘要。

## 2. 資料夾結構

```text
news_kg_project/
  data/
    sample_reddit_news.csv
  docs/
    DEVELOPMENT_PROCESS.md
    News_KG_Development_Process.docx
    TUTORIAL.md
  outputs/
    analysis_summary.md
    edges.csv
    graph.json
    interactive_graph.html
    neo4j_import.cypher
    nodes.csv
  src/
    pipeline.py
  README.md
  requirements.txt
```

## 3. 環境準備

請先確認電腦有 Python。建議使用 Python 3.9 以上。

在 PowerShell 執行：

```powershell
python --version
```

如果能看到 Python 版本，代表可以繼續。

安裝套件：

```powershell
cd "C:\Users\haushuk\Desktop\資料科學實務\期末\news_kg_project"
pip install -r requirements.txt
```

本專案需要：

- `pandas`
- `networkx`

## 4. 第一次執行

進入專案資料夾：

```powershell
cd "C:\Users\haushuk\Desktop\資料科學實務\期末\news_kg_project"
```

執行 pipeline：

```powershell
python .\src\pipeline.py
```

成功時會看到類似：

```text
Input posts: 12
Nodes: 54
Edges: 196
Community method: louvain
Outputs written to: ...\outputs
```

## 5. 看懂輸出檔案

執行後會在 `outputs/` 看到這些檔案：

| 檔案 | 用途 |
|---|---|
| `nodes.csv` | 所有節點，包括 Post、Entity、Topic |
| `edges.csv` | 所有關係，包括 MENTIONS、CO_MENTIONED_WITH、BELONGS_TO |
| `graph.json` | 前端或其他工具可讀的完整圖資料 |
| `neo4j_import.cypher` | 可貼進 Neo4j Browser 的匯入腳本 |
| `interactive_graph.html` | 可用瀏覽器打開的互動圖譜 |
| `analysis_summary.md` | 分析摘要、Top Entities、 strongest co-mention relationships |

## 6. 開啟互動圖譜

直接雙擊：

```text
outputs/interactive_graph.html
```

或在瀏覽器開啟該檔案。圖上會看到 Entity 與 Topic 節點，右側有節點數、關係數與圖例。點擊節點可以查看名稱、類型、社群與 mentions。

## 7. 匯入 Neo4j

1. 打開 Neo4j Desktop 或 Neo4j Aura。
2. 開啟 Neo4j Browser。
3. 打開 `outputs/neo4j_import.cypher`。
4. 複製全部內容。
5. 貼到 Neo4j Browser 執行。

匯入後可以查詢：

```cypher
MATCH (n:KGNode)
RETURN labels(n), n.name, n.id
LIMIT 25;
```

查詢最常共同出現的實體關係：

```cypher
MATCH (a:Entity)-[r:CO_MENTIONED_WITH]->(b:Entity)
RETURN a.name AS source, b.name AS target, r.weight AS weight
ORDER BY weight DESC
LIMIT 10;
```

查詢某個主題下的實體：

```cypher
MATCH (e:Entity)-[:BELONGS_TO]->(t:Topic {name: "AI"})
RETURN e.name, e.entity_type, e.community
ORDER BY e.name;
```

## 8. 換成自己的資料

準備一個 CSV，至少要有以下欄位：

| 欄位 | 說明 |
|---|---|
| `post_id` | 貼文 ID |
| `subreddit` | subreddit 名稱 |
| `title` | 貼文標題 |
| `selftext` | 貼文內容 |
| `created_utc` | 日期或時間 |
| `score` | Reddit 分數 |
| `url` | 原文網址 |

範例：

```csv
post_id,subreddit,title,selftext,created_utc,score,url
p001,worldnews,Taiwan chip exports rise,TSMC and Nvidia were mentioned,2026-05-01,428,https://example.com
```

將檔案放到 `data/your_posts.csv` 後執行：

```powershell
python .\src\pipeline.py --input .\data\your_posts.csv --output .\outputs
```

## 9. 程式流程說明

核心程式是：

```text
src/pipeline.py
```

重要函式：

| 函式 | 功能 |
|---|---|
| `load_posts()` | 讀取 CSV 並建立 raw_text、clean_text |
| `extract_entities()` | 從文章文字抽取實體 |
| `extract_topics()` | 依照關鍵字抽取主題 |
| `build_graph_tables()` | 建立 nodes、edges 與 NetworkX graph |
| `detect_communities()` | 執行 Louvain 或 fallback 社群偵測 |
| `export_neo4j_cypher()` | 匯出 Neo4j Cypher 腳本 |
| `export_html()` | 匯出互動式 HTML 圖譜 |
| `run_pipeline()` | 串接完整流程 |

## 10. 如何解讀分析結果

打開：

```text
outputs/analysis_summary.md
```

目前 sample data 的結果：

- Posts analyzed: 12
- Nodes exported: 54
- Edges exported: 196
- Community detection method: Louvain

Top entities 代表在新聞貼文中出現頻率最高的實體。Strongest co-mention relationships 代表兩個實體經常出現在同一篇貼文中，因此可能存在議題或事件關聯。

例如：

- `Microsoft` 和 `OpenAI` 共同出現，代表 AI infrastructure 主題。
- `Nvidia` 和 `Taiwan` 共同出現，代表半導體與供應鏈主題。
- `United Nations` 和 `United States` 共同出現，代表國際政治與選舉/外交主題。

## 11. 常見錯誤排除

### 找不到 pandas 或 networkx

錯誤類似：

```text
ModuleNotFoundError: No module named 'pandas'
```

解法：

```powershell
pip install -r requirements.txt
```

### CSV 欄位不完整

錯誤類似：

```text
Input CSV is missing required columns
```

請確認 CSV 至少包含：

```text
post_id, subreddit, title, selftext, created_utc, score, url
```

### HTML 打開但圖太擠

資料量很大時，瀏覽器版 HTML 可能變擠。可以：

1. 先用較小資料集展示。
2. 改用 Neo4j Bloom 或 Gephi。
3. 在 Neo4j 中只查詢某個 topic 或 community。

### Neo4j 匯入後看不到圖

先確認資料有匯入：

```cypher
MATCH (n:KGNode)
RETURN count(n);
```

再查詢關係：

```cypher
MATCH ()-[r]->()
RETURN type(r), count(r)
ORDER BY count(r) DESC;
```

## 12. 報告展示建議

展示時可以依照這個順序：

1. 說明問題：Reddit/news 文字很多，實體關係藏在非結構化文本裡。
2. 說明方法：NER 抽實體，建立 Knowledge Graph，使用 Louvain 找社群。
3. 展示 pipeline 輸出：nodes、edges、Neo4j Cypher。
4. 開啟 `interactive_graph.html` 展示圖譜。
5. 展示 `analysis_summary.md` 的 Top Entities 與 co-mention relationships。
6. 說明未來可以串接 PRAW、spaCy/CKIP、Neo4j driver。

## 13. 完成標準

只要以下檔案都存在，代表專案流程已完整跑完：

- `outputs/nodes.csv`
- `outputs/edges.csv`
- `outputs/graph.json`
- `outputs/neo4j_import.cypher`
- `outputs/interactive_graph.html`
- `outputs/analysis_summary.md`

如果還要交作業，可以直接上傳：

```text
News_KG_Final_Project.zip
```
