import sqlite3
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# DDL
# --------------------------------------------------------------------------- #
SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS jobs (
    job_id          TEXT PRIMARY KEY,
    keyword         TEXT NOT NULL,
    title           TEXT,
    company_name    TEXT,
    company_id      TEXT,
    area            TEXT,
    salary_min      INTEGER DEFAULT 0,
    salary_max      INTEGER DEFAULT 0,
    salary_desc     TEXT,
    job_type        TEXT,
    experience      TEXT,
    education       TEXT,
    skills          TEXT,       -- JSON array string
    other           TEXT,
    description     TEXT,
    welfare         TEXT,
    job_url         TEXT,
    first_seen_at   TEXT NOT NULL,
    last_seen_at    TEXT NOT NULL,
    last_updated_at TEXT NOT NULL,
    is_active       INTEGER DEFAULT 1,
    content_hash    TEXT
);

CREATE TABLE IF NOT EXISTS job_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id          TEXT NOT NULL,
    snapshot_at     TEXT NOT NULL,
    title           TEXT,
    company_name    TEXT,
    salary_desc     TEXT,
    job_type        TEXT,
    experience      TEXT,
    education       TEXT,
    skills          TEXT,
    other           TEXT,
    description     TEXT,
    welfare         TEXT,
    content_hash    TEXT,
    change_reason   TEXT,       -- 'new' | 'updated'
    FOREIGN KEY(job_id) REFERENCES jobs(job_id)
);

CREATE TABLE IF NOT EXISTS crawl_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at      TEXT NOT NULL,
    finished_at     TEXT,
    keyword         TEXT,
    total_found     INTEGER DEFAULT 0,
    new_jobs        INTEGER DEFAULT 0,
    updated_jobs    INTEGER DEFAULT 0,
    inactive_jobs   INTEGER DEFAULT 0,
    status          TEXT DEFAULT 'running',  -- 'ok' | 'error' | 'running'
    error_msg       TEXT
);

CREATE INDEX IF NOT EXISTS idx_jh_job_id   ON job_history(job_id);
CREATE INDEX IF NOT EXISTS idx_jobs_kw     ON jobs(keyword);
CREATE INDEX IF NOT EXISTS idx_jobs_active ON jobs(is_active);
"""


# --------------------------------------------------------------------------- #
# DB class
# --------------------------------------------------------------------------- #
class JobDB:
    def __init__(self, db_path: str):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()
        self._migrate()
        logger.info("DB 已就緒：%s", db_path)

    def _migrate(self):
        for table in ("jobs", "job_history"):
            try:
                self.conn.execute(f"ALTER TABLE {table} ADD COLUMN other TEXT")
                self.conn.commit()
            except Exception:
                pass

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _save_history(self, job: dict, snapshot_at: str, reason: str):
        self.conn.execute(
            """
            INSERT INTO job_history
                (job_id, snapshot_at, title, company_name, salary_desc,
                 job_type, experience, education, skills, other,
                 description, welfare, content_hash, change_reason)
            VALUES
                (:job_id, :snapshot_at, :title, :company_name, :salary_desc,
                 :job_type, :experience, :education, :skills, :other,
                 :description, :welfare, :content_hash, :change_reason)
            """,
            {
                **job,
                "snapshot_at": snapshot_at,
                "content_hash": job.get("content_hash", ""),
                "change_reason": reason,
            },
        )

    # ------------------------------------------------------------------ upsert
    def upsert_job(self, job: dict) -> str:
        """
        插入或更新職缺。
        回傳: 'new' | 'updated' | 'unchanged'
        """
        now = self._now()
        job_id = job["job_id"]
        new_hash = job.get("content_hash", "")

        row = self.conn.execute(
            "SELECT content_hash FROM jobs WHERE job_id = ?", (job_id,)
        ).fetchone()

        if row is None:
            # 全新職缺
            self.conn.execute(
                """
                INSERT INTO jobs
                    (job_id, keyword, title, company_name, company_id, area,
                     salary_min, salary_max, salary_desc, job_type,
                     experience, education, skills, other, description, welfare,
                     job_url, first_seen_at, last_seen_at, last_updated_at,
                     is_active, content_hash)
                VALUES
                    (:job_id, :keyword, :title, :company_name, :company_id, :area,
                     :salary_min, :salary_max, :salary_desc, :job_type,
                     :experience, :education, :skills, :other, :description, :welfare,
                     :job_url, :now, :now, :now,
                     1, :content_hash)
                """,
                {**job, "now": now, "content_hash": new_hash},
            )
            self._save_history(job, now, "new")
            self.conn.commit()
            return "new"

        # 更新 last_seen，同時補上 other（若之前是 NULL）
        self.conn.execute(
            "UPDATE jobs SET last_seen_at = ?, is_active = 1, other = COALESCE(other, ?) WHERE job_id = ?",
            (now, job.get("other"), job_id),
        )

        if row["content_hash"] != new_hash:
            # 內容有變
            self.conn.execute(
                """
                UPDATE jobs SET
                    title           = :title,
                    company_name    = :company_name,
                    salary_min      = :salary_min,
                    salary_max      = :salary_max,
                    salary_desc     = :salary_desc,
                    job_type        = :job_type,
                    experience      = :experience,
                    education       = :education,
                    skills          = :skills,
                    other           = :other,
                    description     = :description,
                    welfare         = :welfare,
                    last_updated_at = :now,
                    content_hash    = :content_hash
                WHERE job_id = :job_id
                """,
                {**job, "now": now, "content_hash": new_hash},
            )
            self._save_history(job, now, "updated")
            self.conn.commit()
            return "updated"

        self.conn.commit()
        return "unchanged"

    # ------------------------------------------------------------------ inactive
    def mark_inactive(self, seen_ids: set, keyword: str) -> int:
        """本次沒出現的職缺標記 inactive，回傳筆數"""
        rows = self.conn.execute(
            "SELECT job_id FROM jobs WHERE is_active = 1 AND keyword = ?", (keyword,)
        ).fetchall()

        count = 0
        for r in rows:
            if r["job_id"] not in seen_ids:
                self.conn.execute(
                    "UPDATE jobs SET is_active = 0 WHERE job_id = ?", (r["job_id"],)
                )
                count += 1
        self.conn.commit()
        return count

    # ------------------------------------------------------------------ crawl log
    def log_crawl_start(self, keyword: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO crawl_logs (started_at, keyword, status) VALUES (?, ?, 'running')",
            (self._now(), keyword),
        )
        self.conn.commit()
        return cur.lastrowid

    def log_crawl_finish(
        self,
        log_id: int,
        total: int = 0,
        new: int = 0,
        updated: int = 0,
        inactive: int = 0,
        status: str = "ok",
        error: str = None,
    ):
        self.conn.execute(
            """
            UPDATE crawl_logs SET
                finished_at   = ?,
                total_found   = ?,
                new_jobs      = ?,
                updated_jobs  = ?,
                inactive_jobs = ?,
                status        = ?,
                error_msg     = ?
            WHERE id = ?
            """,
            (self._now(), total, new, updated, inactive, status, error, log_id),
        )
        self.conn.commit()

    # ------------------------------------------------------------------ query
    def get_active_jobs(self, keyword: str = None) -> list:
        sql = "SELECT * FROM jobs WHERE is_active = 1"
        params: tuple = ()
        if keyword:
            sql += " AND keyword = ?"
            params = (keyword,)
        sql += " ORDER BY last_updated_at DESC"
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def get_job_history(self, job_id: str) -> list:
        rows = self.conn.execute(
            "SELECT * FROM job_history WHERE job_id = ? ORDER BY snapshot_at DESC",
            (job_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self):
        self.conn.close()
