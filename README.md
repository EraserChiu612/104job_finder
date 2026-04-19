# 104 Job Finder (Cyberpunk Edition) 🚀

[English](#english) | [繁體中文](#繁體中文)

---

<a name="english"></a>
## English

This is an automated job scraping system and a Cyberpunk-styled local dashboard designed specifically for Taiwan's 104 Job Bank. It can schedule daily data collection for specific job keywords, store them in a local database, track changes in job descriptions and salaries over time, and provide an ultra-cool Web UI for you to easily view, filter, and analyze these jobs.

### 🌟 Key Features

- **Direct API Fetching**: No reliance on heavy browser automation tools (like Selenium/Playwright). It directly calls 104's internal JSON API, making it extremely fast and stable.
- **Exact Match Search**: Filters out junk jobs that merely mention the keyword in their description. It only performs exact matching on the "Job Title".
- **Full Condition Capture**: Stores skills (擅長工具 + 工作技能 + 語言), other conditions (其他條件), experience, education, and job type for every listing.
- **Version History Tracking**: If a job listing changes its salary or description today, the system automatically saves a historical snapshot, letting you know exactly what the company secretly changed.
- **Automated Scheduling**: Built-in APScheduler allows you to set a fixed time every day to collect data silently in the background.
- **Cyberpunk Dashboard**: A local Web interface built with Flask, supporting multi-condition filtering, quick viewing of job details, and change logs.
- **Analytics Tab**: Dedicated data analysis page with interactive charts — skills distribution, market heatmap, salary range, experience/education breakdown, and keyword tag cloud.

### 📊 Analytics Dashboard

Switch to the **數據分析** tab in the header to access:

| Section | Content |
|---|---|
| KPI Row | Active jobs, unique skill count, salary coverage %, average salary, top skill |
| Skills & Tools | Doughnut chart (Top 10) + horizontal bar chart (Top 15) + full ranked table with progress bars |
| Market Distribution | Location bar chart (Top 10), experience doughnut, education doughnut (normalized to minimum level) |
| Salary Distribution | Bar chart by range: 面議, <40K, 40–60K, 60–80K, 80–100K, >100K |
| Other Conditions | Keyword doughnut + horizontal bar + interactive tag cloud sized by frequency |
| Full Text List | Collapsible list of all raw "other conditions" text per job |

All charts support filtering by job role keyword.

### 📂 Directory Structure

```text
104job_finder/
├── crawler/
│   ├── api104.py       # Encapsulation of 104 JSON API requests
│   ├── parser.py       # Job list and detail data parsing
│   └── runner.py       # Main crawler logic
├── storage/
│   └── db.py           # SQLite database operations and Schema
├── dashboard/
│   └── index.html      # Cyberpunk-styled frontend UI
├── data/               # SQLite database storage (jobs.db) (Ignored by Git)
├── logs/               # Execution logs (Ignored by Git)
├── config.yaml         # Crawler and schedule configuration file
├── requirements.txt    # Python dependencies
├── main.py             # Crawler entry point
└── dashboard.py        # Web dashboard entry point (Flask + analytics APIs)
```

### 🚀 Quick Start

#### 1. Install Dependencies

Ensure your environment is Python 3.8+, then run:

```bash
pip install -r requirements.txt
```

#### 2. Configuration

Edit `config.yaml` to enter your desired search keywords, area codes, and salary conditions:

```yaml
keywords:
  - "AI應用工程師"
  - "AI應用規劃師"

areas:
  - "6001001000"  # Taipei City
  - "6001002000"  # New Taipei City
  # ...

filters:
  job_type: 1       # Full-time
  min_salary: 40000 # Minimum monthly salary threshold (0 means 'Negotiable' is also kept)

request:
  max_pages: 20   # Max search pages per keyword to prevent overloading
```

#### 3. Run the Crawler

You can choose to run it manually once or keep it running on a schedule:

- **Run manually once and exit**:
  ```bash
  python main.py --run-now
  ```
- **Start daily schedule (based on time in config.yaml)**:
  ```bash
  python main.py
  ```

#### 4. Start the Dashboard

Start the Flask Server to view the scraped results:

```bash
python dashboard.py
```

Open your browser and navigate to: [http://localhost:5000](http://localhost:5000)

### 🛠️ Development & Maintenance

- **Reset Database**: If you want to clear all data, simply delete the `data/jobs.db` file. It will be automatically recreated the next time the crawler runs.
- **104 API Changes**: If 104 changes its API path in the future, please modify `SEARCH_URL` and `HEADERS` in `crawler/api104.py`.
- **Analytics APIs**: Three endpoints power the analytics tab — `/api/analytics/skills`, `/api/analytics/other`, `/api/analytics/distribution`.

---

<a name="繁體中文"></a>
## 繁體中文

這是一個專門為 104 人力銀行設計的自動化職缺爬蟲系統與賽博龐克風格的本地儀表板。它可以每天定時收集特定關鍵字的職缺，儲存在本地資料庫，追蹤職缺內容與薪資的變更歷史，並提供一個超炫酷的 Web UI 讓你方便地檢視、篩選與分析這些工作。

### 🌟 核心特色

- **API 直連抓取**：不依賴笨重的瀏覽器自動化（Selenium/Playwright），直接調用 104 內部 JSON API，速度極快且穩定。
- **精確搜尋模式**：過濾掉一堆只是內文提到關鍵字的垃圾職缺，只針對「職稱」進行精確比對。
- **完整條件抓取**：完整儲存每個職缺的技能（擅長工具＋工作技能＋語言）、其他條件、工作年資、學歷要求與工作性質。
- **版本歷史追蹤**：如果某個職缺今天修改了薪資或工作內容，系統會自動留存歷史快照 (Snapshot)，讓你知道這間公司偷偷改了什麼。
- **排程自動化**：內建 APScheduler，可以設定每天固定時間在背景默默幫你收資料。
- **Cyberpunk 儀表板**：使用 Flask 打造的本地 Web 介面，支援多重條件篩選、快速查閱職缺詳情與變更紀錄。
- **數據分析頁**：獨立的分析頁面，提供技能分佈、市場熱度、薪資區間、學歷/年資分佈與關鍵字標籤雲等互動圖表。

### 📊 數據分析儀表板

在 header 切換到 **數據分析** 分頁即可使用：

| 區塊 | 內容 |
|---|---|
| KPI 列 | 在職職缺數、技能種數、薪資揭露率、平均薪資、最熱門技能 |
| 技能 / 工具分析 | 甜甜圈圖（Top 10）＋橫向長條圖（Top 15）＋含進度條的完整排名表 |
| 市場分佈 | 地區長條圖（Top 10）、經驗要求甜甜圈、學歷要求甜甜圈（取最低學歷） |
| 薪資區間分佈 | 長條圖：面議 / <40K / 40–60K / 60–80K / 80–100K / >100K |
| 其他條件分析 | 關鍵字甜甜圈＋橫向長條圖＋依頻率縮放的互動式標籤雲 |
| 原文列表 | 可展開 / 收合的所有職缺「其他條件」原始文字列表 |

所有圖表皆支援依職缺關鍵字篩選。

### 📂 目錄結構

```text
104job_finder/
├── crawler/
│   ├── api104.py       # 104 JSON API 的請求封裝
│   ├── parser.py       # 職缺列表與詳情資料解析
│   └── runner.py       # 爬蟲主流程邏輯
├── storage/
│   └── db.py           # SQLite 資料庫操作與 Schema 定義
├── dashboard/
│   └── index.html      # 賽博龐克風格的前端 UI
├── data/               # 存放 SQLite 資料庫 (jobs.db)（不會上傳到 Git）
├── logs/               # 存放執行 Log（不會上傳到 Git）
├── config.yaml         # 爬蟲與排程設定檔
├── requirements.txt    # Python 依賴包
├── main.py             # 爬蟲啟動入口
└── dashboard.py        # Web 儀表板啟動入口（Flask + 分析 API）
```

### 🚀 快速開始

#### 1. 安裝依賴

請確保你的環境是 Python 3.8+，然後執行：

```bash
pip install -r requirements.txt
```

#### 2. 設定 Config

編輯 `config.yaml`，填入你想搜尋的關鍵字、地區代碼與薪資條件：

```yaml
keywords:
  - "AI應用工程師"
  - "AI應用規劃師"

areas:
  - "6001001000"  # 台北市
  - "6001002000"  # 新北市
  # ...

filters:
  job_type: 1       # 全職
  min_salary: 40000 # 月薪最低門檻，0 代表「待遇面議」也保留

request:
  max_pages: 20   # 每個關鍵字搜尋上限頁數，避免過載
```

#### 3. 執行爬蟲

你可以選擇手動執行一次，或讓它常駐排程：

- **手動執行一次即退出**：
  ```bash
  python main.py --run-now
  ```
- **啟動每日排程（依據 config.yaml 的時間）**：
  ```bash
  python main.py
  ```

#### 4. 啟動儀表板

啟動 Flask Server 來查看爬下來的成果：

```bash
python dashboard.py
```

打開瀏覽器前往：[http://localhost:5000](http://localhost:5000)

### 🛠️ 開發與維護

- **重置資料庫**：如果想清除所有資料，直接刪除 `data/jobs.db` 檔案，下次執行爬蟲時會自動重建。
- **104 API 變動**：如果未來 104 修改了 API 路徑，請至 `crawler/api104.py` 修改 `SEARCH_URL` 與 `HEADERS`。
- **分析 API**：三支端點驅動數據分析頁 — `/api/analytics/skills`、`/api/analytics/other`、`/api/analytics/distribution`。
