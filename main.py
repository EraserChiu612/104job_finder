"""
main.py - 104職缺爬蟲入口

用法:
    python main.py              # 啟動排程模式（每天 09:00 執行）
    python main.py --run-now   # 立即執行一次後離開
    python main.py --query     # 印出目前所有活躍職缺
"""

import argparse
import json
import logging
from pathlib import Path

import yaml
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from crawler.runner import CrawlRunner
from storage.db import JobDB

# --------------------------------------------------------------------------- #
# Logging 設定
# --------------------------------------------------------------------------- #
Path("logs").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/crawler.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# 工具函式
# --------------------------------------------------------------------------- #
def load_config() -> dict:
    with open("config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_crawl(config: dict):
    db = JobDB(config["database"]["path"])
    try:
        CrawlRunner(config, db).run()
    finally:
        db.close()


def query_jobs(config: dict):
    db = JobDB(config["database"]["path"])
    try:
        jobs = db.get_active_jobs()
        print(f"\n目前活躍職缺：{len(jobs)} 筆\n" + "─" * 60)
        for j in jobs:
            skills = json.loads(j.get("skills") or "[]")
            print(
                f"[{j['keyword']}] {j['title']} @ {j['company_name']}\n"
                f"  薪資: {j['salary_desc']}  地區: {j['area']}\n"
                f"  技能: {', '.join(skills[:5]) or '—'}\n"
                f"  連結: {j['job_url']}\n"
                f"  更新: {j['last_updated_at']}\n"
            )
    finally:
        db.close()


# --------------------------------------------------------------------------- #
# 入口
# --------------------------------------------------------------------------- #
def main():
    parser = argparse.ArgumentParser(description="104人力銀行職缺爬蟲")
    parser.add_argument("--run-now", action="store_true", help="立即執行一次後結束")
    parser.add_argument("--query", action="store_true", help="印出所有活躍職缺")
    args = parser.parse_args()

    config = load_config()

    if args.query:
        query_jobs(config)
        return

    if args.run_now:
        logger.info("手動觸發：立即執行")
        run_crawl(config)
        return

    # ── 排程模式 ──
    hour = config.get("schedule", {}).get("hour", 9)
    minute = config.get("schedule", {}).get("minute", 0)

    scheduler = BlockingScheduler(timezone="Asia/Taipei")
    scheduler.add_job(
        run_crawl,
        trigger=CronTrigger(hour=hour, minute=minute, timezone="Asia/Taipei"),
        args=[config],
        id="daily_crawl",
        name="每日職缺爬蟲",
        misfire_grace_time=3600,
    )

    logger.info("排程器啟動，每天 %02d:%02d 執行（Ctrl+C 停止）", hour, minute)
    try:
        # 排程模式下先立即跑一次，方便確認
        logger.info("首次執行...")
        run_crawl(config)
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("排程器已停止")


if __name__ == "__main__":
    main()
