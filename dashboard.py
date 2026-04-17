"""
dashboard.py - 本地職缺儀表板 Server

用法: python dashboard.py
瀏覽器開啟: http://localhost:5000
"""

import json
import sqlite3
from pathlib import Path

import yaml
from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)

DB_PATH = "data/jobs.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ─────────────────────────────────────────────
# API Routes
# ─────────────────────────────────────────────

@app.route("/api/jobs")
def api_jobs():
    conn = get_db()
    conditions = []
    params = []

    keyword = request.args.get("keyword", "")
    area = request.args.get("area", "")
    skill = request.args.get("skill", "")
    salary_min = request.args.get("salary_min", "")
    show_inactive = request.args.get("inactive", "0") == "1"
    sort = request.args.get("sort", "last_updated_at")
    search = request.args.get("search", "")

    if not show_inactive:
        conditions.append("is_active = 1")

    if keyword:
        conditions.append("keyword = ?")
        params.append(keyword)

    if area:
        conditions.append("area LIKE ?")
        params.append(f"%{area}%")

    if skill:
        conditions.append("skills LIKE ?")
        params.append(f"%{skill}%")

    if salary_min:
        try:
            val = int(salary_min)
            conditions.append("(salary_min >= ? OR salary_min = 0)")
            params.append(val)
        except ValueError:
            pass

    if search:
        conditions.append("(title LIKE ? OR company_name LIKE ? OR description LIKE ?)")
        params += [f"%{search}%", f"%{search}%", f"%{search}%"]

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    valid_sorts = {"last_updated_at", "first_seen_at", "salary_min", "salary_max", "company_name", "title"}
    if sort not in valid_sorts:
        sort = "last_updated_at"

    sql = f"SELECT * FROM jobs {where} ORDER BY {sort} DESC LIMIT 500"
    rows = conn.execute(sql, params).fetchall()
    conn.close()

    result = []
    for r in rows:
        j = dict(r)
        try:
            j["skills_list"] = json.loads(j.get("skills") or "[]")
        except Exception:
            j["skills_list"] = []
        result.append(j)

    return jsonify(result)


@app.route("/api/job/<job_id>")
def api_job_detail(job_id):
    conn = get_db()
    job = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
    if not job:
        return jsonify({"error": "not found"}), 404

    history = conn.execute(
        "SELECT * FROM job_history WHERE job_id = ? ORDER BY snapshot_at DESC",
        (job_id,)
    ).fetchall()
    conn.close()

    j = dict(job)
    try:
        j["skills_list"] = json.loads(j.get("skills") or "[]")
    except Exception:
        j["skills_list"] = []

    h = []
    for r in history:
        item = dict(r)
        try:
            item["skills_list"] = json.loads(item.get("skills") or "[]")
        except Exception:
            item["skills_list"] = []
        h.append(item)

    return jsonify({"job": j, "history": h})


@app.route("/api/stats")
def api_stats():
    conn = get_db()

    total = conn.execute("SELECT COUNT(*) FROM jobs WHERE is_active=1").fetchone()[0]
    inactive = conn.execute("SELECT COUNT(*) FROM jobs WHERE is_active=0").fetchone()[0]
    today = conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE date(first_seen_at) = date('now')"
    ).fetchone()[0]
    keywords = conn.execute(
        "SELECT keyword, COUNT(*) as cnt FROM jobs WHERE is_active=1 GROUP BY keyword"
    ).fetchall()
    areas = conn.execute(
        "SELECT area, COUNT(*) as cnt FROM jobs WHERE is_active=1 GROUP BY area ORDER BY cnt DESC LIMIT 8"
    ).fetchall()
    salary_known = conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE is_active=1 AND salary_min > 0"
    ).fetchone()[0]
    logs = conn.execute(
        "SELECT * FROM crawl_logs ORDER BY started_at DESC LIMIT 5"
    ).fetchall()
    conn.close()

    return jsonify({
        "total": total,
        "inactive": inactive,
        "new_today": today,
        "keywords": [dict(r) for r in keywords],
        "areas": [dict(r) for r in areas],
        "salary_known": salary_known,
        "recent_logs": [dict(r) for r in logs],
    })


@app.route("/api/keywords")
def api_keywords():
    try:
        with open("config.yaml", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        return jsonify(cfg.get("keywords", []))
    except Exception:
        return jsonify([])


# ─────────────────────────────────────────────
# Serve Dashboard HTML
# ─────────────────────────────────────────────

@app.route("/")
def index():
    html_path = Path(__file__).parent / "dashboard" / "index.html"
    return html_path.read_text(encoding="utf-8")


if __name__ == "__main__":
    print("\n  ╔══════════════════════════════════════╗")
    print("  ║  CYBERPUNK JOB DASHBOARD  v1.0       ║")
    print("  ║  http://localhost:5000               ║")
    print("  ╚══════════════════════════════════════╝\n")
    app.run(debug=False, port=5000)
