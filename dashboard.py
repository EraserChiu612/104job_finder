"""
dashboard.py - 本地職缺儀表板 Server

用法: python dashboard.py
瀏覽器開啟: http://localhost:5000
"""

import json
import re
import sqlite3
from collections import Counter
from itertools import combinations
from pathlib import Path

import yaml
from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)

DB_PATH = "data/jobs.db"


def _init_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    from storage.db import JobDB
    db = JobDB(DB_PATH)
    db.close()


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
        conditions.append("(area LIKE ? OR area_detail LIKE ?)")
        params += [f"%{area}%", f"%{area}%"]

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
# Analytics Routes
# ─────────────────────────────────────────────

@app.route("/api/analytics/skills")
def api_analytics_skills():
    conn = get_db()
    kw = request.args.get("keyword", "")
    sql = "SELECT skills FROM jobs WHERE is_active=1 AND skills IS NOT NULL"
    params = []
    if kw:
        sql += " AND keyword=?"
        params.append(kw)
    rows = conn.execute(sql, params).fetchall()
    conn.close()

    counter = Counter()
    for row in rows:
        try:
            for s in json.loads(row["skills"]):
                s = s.strip()
                if s:
                    counter[s] += 1
        except Exception:
            pass

    return jsonify([{"name": k, "count": v} for k, v in counter.most_common(50)])


@app.route("/api/analytics/other")
def api_analytics_other():
    conn = get_db()
    kw = request.args.get("keyword", "")
    sql = "SELECT title, company_name, other FROM jobs WHERE is_active=1 AND other IS NOT NULL AND other != ''"
    params = []
    if kw:
        sql += " AND keyword=?"
        params.append(kw)
    rows = conn.execute(sql, params).fetchall()
    conn.close()

    stop_words = {
        # 單字語助詞 / 介詞
        '的', '了', '及', '與', '或', '在', '有', '能', '是', '並', '且', '等',
        '可', '以', '為', '將', '對', '於', '不', '需', '要', '具', '熟', '年',
        '之', '其', '此', '由', '至', '從', '使', '但', '若', '即', '則', '才',
        '亦', '已', '每', '各', '無', '另', '含', '依', '按', '均',
        # 連接詞 / 副詞
        '以及', '並且', '而且', '不但', '不僅', '雖然', '然而', '因此', '所以',
        '因而', '以便', '同時', '此外', '另外', '除此', '否則', '進而', '其次',
        '再者', '甚至', '例如', '諸如', '等等', '其中', '其他', '如下', '如上',
        '以下', '上述', '下列', '包含', '包括', '涵蓋',
        # 職缺常見贅詞
        '工作', '相關', '優先', '佳', '者', '如', '歡迎', '請', '需要', '具有',
        '具備', '良好', '以上', '擔任', '負責', '參與', '了解', '熟悉', '使用',
        '不限', '不拘', '尤佳', '為佳', '加分', '必須', '基本', '有效',
        '有意者', '有意願', '有興趣', '有相關', '具相關', '優先考慮',
        '相關經驗', '工作經驗', '以上經驗',
    }

    keyword_counter = Counter()
    job_list = []

    for row in rows:
        text = row["other"] or ""
        job_list.append({
            "title": row["title"],
            "company": row["company_name"],
            "other": text,
        })
        tokens = re.split(r'[、，,\s。！？；：\n\r\t＊*•·\-－]+', text)
        for token in tokens:
            token = re.sub(r'^[\d\.\、\s]+', '', token).strip('「」【】()（）[]〔〕《》')
            if len(token) >= 2 and token not in stop_words and not token.isdigit():
                keyword_counter[token] += 1

    return jsonify({
        "keywords": [{"name": k, "count": v} for k, v in keyword_counter.most_common(30)],
        "jobs": job_list,
    })


@app.route("/api/analytics/distribution")
def api_analytics_distribution():
    conn = get_db()
    kw = request.args.get("keyword", "")
    base = "WHERE is_active=1"
    params = []
    if kw:
        base += " AND keyword=?"
        params.append(kw)

    salary_rows = conn.execute(
        f"SELECT salary_min FROM jobs {base} AND salary_min > 0", params
    ).fetchall()
    no_salary = conn.execute(
        f"SELECT COUNT(*) FROM jobs {base} AND (salary_min = 0 OR salary_min IS NULL)", params
    ).fetchone()[0]

    buckets = {"<40K": 0, "40-60K": 0, "60-80K": 0, "80-100K": 0, ">100K": 0}
    total_sal = 0
    for row in salary_rows:
        s = row[0]
        total_sal += s
        if s < 40000: buckets["<40K"] += 1
        elif s < 60000: buckets["40-60K"] += 1
        elif s < 80000: buckets["60-80K"] += 1
        elif s < 100000: buckets["80-100K"] += 1
        else: buckets[">100K"] += 1

    avg_salary = int(total_sal / len(salary_rows)) if salary_rows else 0

    exp_rows = conn.execute(
        f"SELECT experience, COUNT(*) as cnt FROM jobs {base} AND experience IS NOT NULL AND experience != '' GROUP BY experience ORDER BY cnt DESC", params
    ).fetchall()
    edu_raw = conn.execute(
        f"SELECT education, COUNT(*) as cnt FROM jobs {base} AND education IS NOT NULL AND education != '' GROUP BY education ORDER BY cnt DESC", params
    ).fetchall()
    # 取最低學歷：依序定義，分割多選值後取最低層級
    _EDU_ORDER = ['不拘', '高中職', '高中', '專科', '大學', '碩士', '博士']
    def _min_edu(raw):
        parts = re.split(r'[、,，]', (raw or '').replace('以上', '').replace('（職）', ''))
        parts = [p.strip() for p in parts if p.strip()]
        if not parts:
            return '不拘'
        best_idx, best = len(_EDU_ORDER), parts[0]
        for p in parts:
            for i, lvl in enumerate(_EDU_ORDER):
                if lvl in p:
                    if i < best_idx:
                        best_idx, best = i, lvl
                    break
        return best
    edu_map = {}
    for row in edu_raw:
        label = _min_edu(row['education'])
        edu_map[label] = edu_map.get(label, 0) + row['cnt']
    edu_rows = sorted([{'education': k, 'cnt': v} for k, v in edu_map.items()], key=lambda x: -x['cnt'])

    area_rows = conn.execute(
        f"SELECT area, COUNT(*) as cnt FROM jobs {base} AND area IS NOT NULL AND area != '' GROUP BY area ORDER BY cnt DESC LIMIT 10", params
    ).fetchall()
    conn.close()

    salary_dist = [{"range": "面議/未知", "count": no_salary}]
    salary_dist += [{"range": k, "count": v} for k, v in buckets.items()]

    return jsonify({
        "salary_dist": salary_dist,
        "avg_salary": avg_salary,
        "experience_dist": [dict(r) for r in exp_rows],
        "education_dist": edu_rows,
        "area_dist": [dict(r) for r in area_rows],
    })


@app.route("/api/analytics/companies")
def api_analytics_companies():
    conn = get_db()
    kw = request.args.get("keyword", "")
    top_n = int(request.args.get("top_n", 20))

    base = "WHERE is_active=1"
    params: list = []
    if kw:
        base += " AND keyword=?"
        params.append(kw)

    rows = conn.execute(
        f"SELECT company_id, company_name, skills, salary_min, salary_max FROM jobs {base}",
        params,
    ).fetchall()
    conn.close()

    company_data: dict[str, dict] = {}
    for row in rows:
        cid = row["company_id"] or row["company_name"]
        if not cid:
            continue
        if cid not in company_data:
            company_data[cid] = {
                "company_id": row["company_id"],
                "company_name": row["company_name"],
                "job_count": 0,
                "salaries": [],
                "skill_counter": Counter(),
            }
        entry = company_data[cid]
        entry["job_count"] += 1
        if row["salary_min"] and row["salary_min"] > 0:
            avg = (row["salary_min"] + (row["salary_max"] or row["salary_min"])) / 2
            entry["salaries"].append(avg)
        try:
            for s in json.loads(row["skills"] or "[]"):
                if s.strip():
                    entry["skill_counter"][s.strip()] += 1
        except Exception:
            pass

    result = []
    for entry in company_data.values():
        sals = entry["salaries"]
        top_skills = [s for s, _ in entry["skill_counter"].most_common(5)]
        result.append({
            "company_id": entry["company_id"],
            "company_name": entry["company_name"],
            "job_count": entry["job_count"],
            "avg_salary": int(sum(sals) / len(sals)) if sals else 0,
            "top_skills": top_skills,
        })

    result.sort(key=lambda x: x["job_count"], reverse=True)
    return jsonify(result[:top_n])


@app.route("/api/analytics/timeline")
def api_analytics_timeline():
    conn = get_db()
    kw = request.args.get("keyword", "")
    days = int(request.args.get("days", 30))

    base = "WHERE date(first_seen_at) >= date('now', ?)"
    params: list = [f"-{days} days"]
    if kw:
        base += " AND keyword=?"
        params.append(kw)

    new_jobs = conn.execute(
        f"SELECT date(first_seen_at) as d, COUNT(*) as cnt FROM jobs {base} GROUP BY d ORDER BY d",
        params,
    ).fetchall()

    crawl_params: list = [f"-{days} days"]
    crawl_base = "WHERE date(started_at) >= date('now', ?) AND status='ok'"
    if kw:
        crawl_base += " AND keyword=?"
        crawl_params.append(kw)

    crawl_logs = conn.execute(
        f"SELECT date(started_at) as d, SUM(new_jobs) as new_j, SUM(updated_jobs) as upd_j FROM crawl_logs {crawl_base} GROUP BY d ORDER BY d",
        crawl_params,
    ).fetchall()
    conn.close()

    return jsonify({
        "new_jobs": [{"date": r["d"], "count": r["cnt"]} for r in new_jobs],
        "crawl_activity": [{"date": r["d"], "new": r["new_j"] or 0, "updated": r["upd_j"] or 0} for r in crawl_logs],
    })


@app.route("/api/analytics/salary-by-skill")
def api_analytics_salary_by_skill():
    conn = get_db()
    kw = request.args.get("keyword", "")
    top_n = int(request.args.get("top_n", 20))
    sql = "SELECT skills, salary_min, salary_max FROM jobs WHERE is_active=1 AND skills IS NOT NULL AND salary_min > 0"
    params = []
    if kw:
        sql += " AND keyword=?"
        params.append(kw)
    rows = conn.execute(sql, params).fetchall()
    conn.close()

    skill_salaries: dict[str, list] = {}
    for row in rows:
        try:
            skill_list = [s.strip() for s in json.loads(row["skills"]) if s.strip()]
        except Exception:
            continue
        avg = (row["salary_min"] + (row["salary_max"] or row["salary_min"])) / 2
        for skill in skill_list:
            skill_salaries.setdefault(skill, []).append(avg)

    result = [
        {
            "skill": skill,
            "avg_salary": int(sum(vals) / len(vals)),
            "count": len(vals),
        }
        for skill, vals in skill_salaries.items()
        if len(vals) >= 3  # 樣本數太少不具參考價值
    ]
    result.sort(key=lambda x: x["avg_salary"], reverse=True)
    return jsonify(result[:top_n])


@app.route("/api/analytics/cooccurrence")
def api_analytics_cooccurrence():
    conn = get_db()
    kw = request.args.get("keyword", "")
    top_n = int(request.args.get("top_n", 15))
    sql = "SELECT skills FROM jobs WHERE is_active=1 AND skills IS NOT NULL"
    params = []
    if kw:
        sql += " AND keyword=?"
        params.append(kw)
    rows = conn.execute(sql, params).fetchall()
    conn.close()

    pair_counter: Counter = Counter()
    for row in rows:
        try:
            skill_list = [s.strip() for s in json.loads(row["skills"]) if s.strip()]
        except Exception:
            continue
        # 只取前 20 個技能避免組合爆炸
        for a, b in combinations(sorted(set(skill_list[:20])), 2):
            pair_counter[(a, b)] += 1

    result = [
        {"skill_a": a, "skill_b": b, "count": c}
        for (a, b), c in pair_counter.most_common(top_n)
    ]
    return jsonify(result)


# ─────────────────────────────────────────────
# Serve Dashboard HTML
# ─────────────────────────────────────────────

@app.route("/")
def index():
    html_path = Path(__file__).parent / "dashboard" / "index.html"
    return html_path.read_text(encoding="utf-8")


if __name__ == "__main__":
    _init_db()
    print("\n  ╔══════════════════════════════════════╗")
    print("  ║  CYBERPUNK JOB DASHBOARD  v1.0       ║")
    print("  ║  http://localhost:5000               ║")
    print("  ╚══════════════════════════════════════╝\n")
    app.run(debug=False, port=5000)
