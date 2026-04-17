import logging

from .api104 import API104
from .parser import parse_list_item, parse_detail, compute_hash
from storage.db import JobDB

logger = logging.getLogger(__name__)


class CrawlRunner:
    def __init__(self, config: dict, db: JobDB):
        self.config = config
        self.db = db
        self.api = API104(config)
        self.keywords: list = config["keywords"]
        self.areas: list = config["areas"]
        self.min_salary: int = config.get("filters", {}).get("min_salary", 0)

    # ------------------------------------------------------------------
    def run(self):
        logger.info("═" * 50)
        logger.info("爬蟲任務開始")
        for keyword in self.keywords:
            self._crawl_keyword(keyword)
        logger.info("爬蟲任務全部完成")
        logger.info("═" * 50)

    # ------------------------------------------------------------------
    def _crawl_keyword(self, keyword: str):
        log_id = self.db.log_crawl_start(keyword)
        stats = {"total": 0, "new": 0, "updated": 0, "inactive": 0}
        seen_ids: set = set()

        try:
            raw_list = self.api.search_jobs(keyword, self.areas)

            # ── 薪資過濾（client-side）──
            candidates = []
            for item in raw_list:
                base = parse_list_item(item)
                sal = base["salary_min"]
                # sal == 0 代表面議，保留；有數字則需 >= min_salary
                if sal == 0 or sal >= self.min_salary:
                    candidates.append(base)

            logger.info(
                "keyword=%s  總筆數=%d  薪資篩選後=%d",
                keyword, len(raw_list), len(candidates),
            )
            stats["total"] = len(candidates)

            for base in candidates:
                job_id = base["job_id"]
                seen_ids.add(job_id)

                # 取詳情
                raw_detail = self.api.get_job_detail(job_id)
                if not raw_detail:
                    logger.warning("跳過 %s：詳情取得失敗", job_id)
                    continue

                detail = parse_detail(raw_detail)

                # detail 的薪資更準確，若有值則覆蓋
                job = {**base, **{k: v for k, v in detail.items() if v is not None}}
                job["keyword"] = keyword
                job["content_hash"] = compute_hash(job)

                result = self.db.upsert_job(job)

                if result == "new":
                    stats["new"] += 1
                    logger.info("[NEW]     %s @ %s", job["title"], job["company_name"])
                elif result == "updated":
                    stats["updated"] += 1
                    logger.info("[UPDATED] %s @ %s", job["title"], job["company_name"])

                self.api._sleep()

            # ── 標記本次沒看到的職缺為 inactive ──
            stats["inactive"] = self.db.mark_inactive(seen_ids, keyword)

            self.db.log_crawl_finish(log_id, **stats, status="ok")
            logger.info(
                "keyword=%s 完成  new=%d updated=%d inactive=%d",
                keyword, stats["new"], stats["updated"], stats["inactive"],
            )

        except Exception as exc:
            logger.exception("keyword=%s 爬蟲失敗", keyword)
            self.db.log_crawl_finish(log_id, **stats, status="error", error=str(exc))
