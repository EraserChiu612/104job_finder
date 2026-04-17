# 104 Job Finder (Cyberpunk Edition)

這是一個專門為 104 人力銀行設計的自動化職缺爬蟲系統與賽博龐克風格的本地儀表板。它可以每天定時收集特定關鍵字的職缺，儲存在本地資料庫，追蹤職缺內容與薪資的變更歷史，並提供一個超炫酷的 Web UI 讓你方便地檢視與篩選這些工作。

## 🌟 核心特色

- **API 直連抓取**：不依賴笨重的瀏覽器自動化（Selenium/Playwright），直接調用 104 內部 JSON API，速度極快且穩定。
- **精確搜尋模式**：過濾掉一堆只是內文提到關鍵字的垃圾職缺，只針對「職稱」進行精確比對。
- **版本歷史追蹤**：如果某個職缺今天修改了薪資或工作內容，系統會自動留存歷史快照 (Snapshot)，讓你知道這間公司偷偷改了什麼。
- **排程自動化**：內建 APScheduler，可以設定每天固定時間在背景默默幫你收資料。
- **Cyberpunk 儀表板**：使用 Flask 打造的本地 Web 介面，支援多重條件篩選、快速查閱職缺詳情與變更紀錄。

## 📂 目錄結構

```text
job_finder/
├── crawler/
│   ├── api104.py       # 104 JSON API 的請求封裝
│   ├── parser.py       # 職缺列表與詳情資料解析
│   └── runner.py       # 爬蟲主流程邏輯
├── storage/
│   └── db.py           # SQLite 資料庫操作與 Schema 定義
├── dashboard/
│   └── index.html      # 賽博龐克風格的前端 UI
├── data/               # 存放 SQLite 資料庫 (jobs.db) (不會上傳到 Git)
├── logs/               # 存放執行 Log (不會上傳到 Git)
├── config.yaml         # 爬蟲與排程設定檔
├── requirements.txt    # Python 依賴包
├── main.py             # 爬蟲啟動入口
└── dashboard.py        # Web 儀表板啟動入口
```

## 🚀 快速開始

### 1. 安裝依賴

請確保你的環境是 Python 3.8+，然後執行：

```bash
pip install -r requirements.txt
```

### 2. 設定 Config

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

### 3. 執行爬蟲

你可以選擇手動執行一次，或讓它常駐排程：

- **手動執行一次即退出**：
  ```bash
  python main.py --run-now
  ```
- **啟動每日排程 (依據 config.yaml 的時間)**：
  ```bash
  python main.py
  ```

### 4. 啟動儀表板

啟動 Flask Server 來查看爬下來的成果：

```bash
python dashboard.py
```
打開瀏覽器前往：[http://localhost:5000](http://localhost:5000) 即可看到超炫的 Cyberpunk 儀表板！

## 🛠️ 開發與維護

- **重置資料庫**：如果想清除所有資料，直接刪除 `data/jobs.db` 檔案，下次執行爬蟲時會自動重建。
- **104 API 變動**：如果未來 104 修改了 API 路徑，請至 `crawler/api104.py` 修改 `SEARCH_URL` 與 `HEADERS`。
