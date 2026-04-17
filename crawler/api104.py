import time
import random
import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.104.com.tw/jobs/search/api/jobs"
DETAIL_URL = "https://www.104.com.tw/job/ajax/content/{job_id}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.104.com.tw/jobs/search/",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8",
    "X-Requested-With": "XMLHttpRequest",
}


class API104:
    def __init__(self, config: dict):
        req_cfg = config.get("request", {})
        self.delay_min: float = req_cfg.get("delay_min", 1.5)
        self.delay_max: float = req_cfg.get("delay_max", 3.5)
        self.timeout: int = req_cfg.get("timeout", 15)
        self.max_pages: int = req_cfg.get("max_pages", 10)  # 保護用上限

        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    # ------------------------------------------------------------------
    def _sleep(self):
        time.sleep(random.uniform(self.delay_min, self.delay_max))

    # ------------------------------------------------------------------
    def search_jobs(self, keyword: str, areas: list) -> list:
        """回傳該關鍵字所有頁的職缺列表原始資料"""
        all_jobs: list = []
        area_str = ",".join(areas)
        page = 1

        while True:
            params = {
                "keyword": keyword,
                "area": area_str,
                "order": 16,        # 依更新日期排序
                "asc": 0,
                "s9": 1,            # 全職
                "fz": 1,            # 搜尋欄位：職稱
                "kwop": 1,          # 關鍵字模式：完全比對
                "page": page,
                "mode": "s",
                "jobsource": "2018indexpoc",
                "ro": 0,
            }

            try:
                resp = self.session.get(SEARCH_URL, params=params, timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()
            except Exception as exc:
                logger.error("搜尋失敗 keyword=%s page=%d: %s", keyword, page, exc)
                break

            jobs = data.get("data", [])
            if not jobs:
                break

            all_jobs.extend(jobs)
            pagination = data.get("metadata", {}).get("pagination", {})
            total_pages = pagination.get("lastPage", 1)
            total_cnt = pagination.get("total", 0)
            logger.info(
                "keyword=%s  page=%d/%d  本頁=%d筆  總計=%d",
                keyword, page, total_pages, len(jobs), total_cnt,
            )

            if page >= total_pages or page >= self.max_pages:
                break

            page += 1
            self._sleep()

        return all_jobs

    # ------------------------------------------------------------------
    def get_job_detail(self, job_id: str) -> Optional[dict]:
        """取得單一職缺的詳細內容"""
        url = DETAIL_URL.format(job_id=job_id)
        try:
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            logger.error("詳情取得失敗 job_id=%s: %s", job_id, exc)
            return None
