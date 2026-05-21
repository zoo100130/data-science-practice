# Web3 Knowledge Graph 運行教學

這份教學說明如何在本機執行 Web3 Knowledge Graph 專案，並用瀏覽器查看互動式圖譜。

## 1. 專案內容

此專案會將 Web3 / crypto / DeFi 文章資料轉成知識圖譜。

流程如下：

1. 讀取 `data/sample_web3_posts.csv`。
2. 清理文章標題與內容。
3. 抽取 Web3 實體，例如 Ethereum、Polygon、Uniswap、Aave、Chainlink、MakerDAO。
4. 抽取主題，例如 DeFi、Layer2 Scaling、Governance、Security、Restaking。
5. 建立節點與關係。
6. 使用 Louvain 做社群偵測。
7. 匯出互動 HTML、Neo4j Cypher、CSV、JSON 與分析摘要。

## 2. 第一次安裝

打開 PowerShell，進入專案資料夾：

```powershell
cd "C:\Users\haushuk\Desktop\資料科學實務\期末\web3_kg_project"
```

確認 Python 可用：

```powershell
python --version
```

安裝依賴：

```powershell
pip install -r requirements.txt
```

## 3. 執行資料處理 pipeline

在 `web3_kg_project` 資料夾內執行：

```powershell
python .\src\pipeline.py
```

成功時會看到：

```text
Input posts: 15
Nodes: 74
Edges: 293
Community method: louvain
Outputs written to: ...\outputs
```

## 4. 啟動本機網站

仍然在 `web3_kg_project` 資料夾內，執行：

```powershell
python -m http.server 8080
```

看到類似以下訊息代表伺服器已啟動：

```text
Serving HTTP on :: port 8080 ...
```

接著用瀏覽器打開：

```text
http://localhost:8080/outputs/interactive_graph.html
```

你會看到 Web3 Knowledge Graph 的互動圖譜。

## 5. 如何停止伺服器

在正在運行 server 的 PowerShell 視窗按：

```text
Ctrl + C
```

就會停止本機網站。

## 6. 輸出檔案說明

所有輸出都在 `outputs/`：

| 檔案 | 說明 |
|---|---|
| `interactive_graph.html` | 可用瀏覽器打開的互動圖譜 |
| `analysis_summary.md` | 分析摘要與 Top Entities |
| `nodes.csv` | 圖譜節點表 |
| `edges.csv` | 圖譜關係表 |
| `graph.json` | 完整圖譜 JSON |
| `neo4j_import.cypher` | 可匯入 Neo4j 的 Cypher 腳本 |

## 7. 如何看懂互動圖譜

圖譜中有兩種主要節點：

- Entity：Web3 實體，例如 Ethereum、Polygon、Aave、Chainlink。
- Topic：主題，例如 DeFi、Layer2 Scaling、Governance、Security。

關係包含：

- `MENTIONS`：文章提到某個實體。
- `CO_MENTIONED_WITH`：兩個實體在同一篇文章中共同出現。
- `BELONGS_TO`：實體屬於某個主題。

在頁面中點擊節點，可以看到：

- 名稱
- 類型
- community
- mentions 次數

## 8. 匯入 Neo4j

如果你要用 Neo4j 展示：

1. 打開 Neo4j Browser。
2. 打開 `outputs/neo4j_import.cypher`。
3. 複製全部內容。
4. 貼到 Neo4j Browser 執行。

匯入後可以查：

```cypher
MATCH (n:KGNode)
RETURN labels(n), n.name, n.entity_type
LIMIT 25;
```

查最強共同出現關係：

```cypher
MATCH (a:Entity)-[r:CO_MENTIONED_WITH]->(b:Entity)
RETURN a.name AS source, b.name AS target, r.weight AS weight
ORDER BY weight DESC
LIMIT 10;
```

查某個主題，例如 DeFi：

```cypher
MATCH (e:Entity)-[:BELONGS_TO]->(t:Topic {name: "DeFi"})
RETURN e.name, e.entity_type, e.community
ORDER BY e.name;
```

## 9. 換成自己的 Web3 資料

準備一個 CSV，欄位需要包含：

```text
post_id, subreddit, title, selftext, created_utc, score, url
```

放到 `data/your_web3_posts.csv`，然後執行：

```powershell
python .\src\pipeline.py --input .\data\your_web3_posts.csv --output .\outputs
```

再重新整理瀏覽器頁面即可看到新的圖譜。

## 10. 從 Reddit 爬取 Web3 資料

本專案已提供不需要 API key 的 Reddit crawler，會使用 Reddit 公開 JSON endpoint。

執行：

```powershell
python .\src\reddit_crawler.py --subreddits ethereum defi CryptoCurrency solana web3 NFT --posts-per-subreddit 15 --output .\data\reddit_web3_posts.csv
```

爬完後，用真實 Reddit 資料建立圖譜：

```powershell
python .\src\pipeline.py --input .\data\reddit_web3_posts.csv --output .\outputs\reddit_live
```

打開 live graph：

```text
http://localhost:8080/outputs/reddit_live/interactive_graph.html
```

如果你想學爬蟲程式怎麼寫，請打開：

```text
docs/Reddit_Web3_Crawler_Tutorial.ipynb
```

## 11. 常見問題

### 問題 1：ModuleNotFoundError

如果看到：

```text
ModuleNotFoundError: No module named 'pandas'
```

請執行：

```powershell
pip install -r requirements.txt
```

### 問題 2：8080 port 被占用

改用另一個 port：

```powershell
python -m http.server 8090
```

然後打開：

```text
http://localhost:8090/outputs/interactive_graph.html
```

### 問題 3：CSV 欄位不完整

請檢查 CSV 是否有：

```text
post_id, subreddit, title, selftext, created_utc, score, url
```

### 問題 4：Reddit 暫時拒絕請求

請降低請求量，或增加等待時間：

```powershell
python .\src\reddit_crawler.py --sleep-seconds 3 --posts-per-subreddit 8
```

## 12. 展示建議

課堂展示可以照這個順序：

1. 說明主題：Web3 生態資訊分散，適合用 Knowledge Graph 整理。
2. 展示 `sample_web3_posts.csv`。
3. 執行 `python .\src\pipeline.py`。
4. 打開 `interactive_graph.html`。
5. 說明 Ethereum、Polygon、DeFi、Chainlink 等節點的關係。
6. 展示 `analysis_summary.md` 的 Top Entities。
7. 說明可以匯入 Neo4j 做進一步查詢。
