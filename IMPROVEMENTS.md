# 精進計畫 (Improvements Roadmap)

## 已完成 ✅

1. **薪資單位統一** — ✅ 已在 `parser.py` 加入 `normalize_salary_to_monthly()` 
   - 轉換時薪/日薪/年薪為月薪
   - 既有 DB 數據需清除重爬

## 待進行 🔄

2. **地區欄位細化** — TODO
   - 從 `jobDetail.addressDetail` 補存詳細地址
   - 目前只有「台北市」層級，需要區別行政區

3. **技能正規化** — TODO
   - 「Python」「python」「Python3」應合併為同一技能
   - 建立技能別名對應表或使用小寫正規化

4. **技能共現分析** — TODO
   - 分析哪些技能常一起出現（共現矩陣）
   - 新增 API endpoint: `/api/analytics/cooccurrence`
   - 新增前端圖表頁面

5. **薪資 × 技能交叉分析** — TODO
   - 統計各技能對應的平均薪資
   - 新增 API endpoint: `/api/analytics/salary-by-skill`
   - 前端新增「技能薪資排行」圖表

6. **時間趨勢圖** — TODO
   - 利用 `crawl_logs` 和 `first_seen_at` 繪製日期趨勢
   - 新增 API endpoint: `/api/analytics/timeline`
   - 前端新增「每日新增職缺」折線圖

7. **公司分析頁** — TODO
   - 統計公司發佈職缺數、平均薪資、熱門技能
   - 新增 API endpoint: `/api/analytics/companies`
   - 前端新增公司排行分頁

---

## 修復注意事項

- **item 1 收尾**：建議刪除 `data/jobs.db` 重新爬蟲，讓新薪資正規化生效
- 或製作 DB migration script 回填舊數據

---

最後更新：2026-04-19
