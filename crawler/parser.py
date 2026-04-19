import re
import json
import hashlib


# --------------------------------------------------------------------------- #
# 技能正規化
# --------------------------------------------------------------------------- #

# 別名 → 標準名稱（key 統一小寫）
_SKILL_ALIAS: dict[str, str] = {
    # Python
    "python3": "Python", "python2": "Python", "python 3": "Python", "python 2": "Python",
    # JavaScript
    "javascript": "JavaScript", "js": "JavaScript", "es6": "JavaScript", "es2015": "JavaScript",
    "typescript": "TypeScript", "ts": "TypeScript",
    # Java
    "java": "Java",
    # C/C++
    "c++": "C++", "cpp": "C++", "c/c++": "C/C++",
    # C#
    "c#": "C#", "csharp": "C#",
    # Databases
    "mysql": "MySQL", "postgresql": "PostgreSQL", "postgres": "PostgreSQL",
    "mssql": "MS SQL", "sql server": "MS SQL", "microsoft sql server": "MS SQL",
    "mongodb": "MongoDB", "mongo": "MongoDB",
    "redis": "Redis",
    "sqlite": "SQLite",
    # Cloud
    "aws": "AWS", "amazon web services": "AWS",
    "gcp": "GCP", "google cloud": "GCP", "google cloud platform": "GCP",
    "azure": "Azure", "microsoft azure": "Azure",
    # Frameworks
    "react": "React", "react.js": "React", "reactjs": "React",
    "vue": "Vue.js", "vue.js": "Vue.js", "vuejs": "Vue.js",
    "angular": "Angular", "angularjs": "Angular",
    "node": "Node.js", "node.js": "Node.js", "nodejs": "Node.js",
    "django": "Django", "flask": "Flask", "fastapi": "FastAPI",
    "spring": "Spring", "spring boot": "Spring Boot", "springboot": "Spring Boot",
    # DevOps
    "docker": "Docker", "kubernetes": "Kubernetes", "k8s": "Kubernetes",
    "git": "Git", "github": "Git", "gitlab": "Git",
    "ci/cd": "CI/CD", "cicd": "CI/CD",
    "linux": "Linux", "ubuntu": "Linux",
    # Data / ML
    "machine learning": "Machine Learning", "ml": "Machine Learning",
    "deep learning": "Deep Learning", "dl": "Deep Learning",
    "tensorflow": "TensorFlow", "pytorch": "PyTorch",
    "pandas": "pandas", "numpy": "NumPy", "scikit-learn": "scikit-learn",
    "excel": "Excel", "microsoft excel": "Excel",
    "power bi": "Power BI", "powerbi": "Power BI",
    "tableau": "Tableau",
    "sql": "SQL",
}


def normalize_skill(name: str) -> str:
    """將技能名稱正規化：查別名表，否則做 title-case 修正。"""
    stripped = name.strip()
    lower = stripped.lower()
    if lower in _SKILL_ALIAS:
        return _SKILL_ALIAS[lower]
    return stripped


# --------------------------------------------------------------------------- #
# 列表解析
# --------------------------------------------------------------------------- #

def extract_job_id(link: str) -> str:
    """從 //www.104.com.tw/job/XXXXX 取出 XXXXX"""
    return link.rstrip("/").split("/")[-1]


def normalize_salary_to_monthly(sal_value: int, sal_type: int) -> int:
    """
    將各種薪資類型轉換成月薪（新台幣）。

    List API s5：  0=月薪(直接值), 1=時薪, 2=日薪, 3=月薪, 4=論件計酬, 6=年薪
    Detail API salaryType：10=面議, 20=時薪, 30=日薪, 40=論件計酬, 50=月薪, 60=年薪
    """
    if not sal_value or sal_value <= 0:
        return 0
    if sal_type in (1, 20):    # 時薪 → 月薪
        return int(sal_value * 8 * 22)
    elif sal_type in (2, 30):  # 日薪 → 月薪
        return int(sal_value * 22)
    elif sal_type in (0, 3, 50):  # 月薪（含 list API s5=0 直接就是月薪值）
        return sal_value
    elif sal_type in (6, 60):  # 年薪 → 月薪
        return int(sal_value / 12)
    else:  # 10=面議, 40=論件計酬, 其他無法標準化
        return 0


def parse_salary(text: str) -> tuple:
    """
    解析薪資字串，回傳 (min, max)。
    '月薪 40,000～60,000元' -> (40000, 60000)
    '面議'                  -> (0, 0)
    """
    nums = [int(n.replace(",", "")) for n in re.findall(r"[\d,]+", text)]
    if len(nums) >= 2:
        return nums[0], nums[1]
    if len(nums) == 1:
        return nums[0], nums[0]
    return 0, 0


def parse_list_item(item: dict) -> dict:
    # 新 API: link.job 已是完整 URL
    job_url = item.get("link", {}).get("job", "")
    job_id = extract_job_id(job_url)

    # 新 API: 薪資為 salaryLow / salaryHigh（整數），無 salaryDesc
    sal_min_raw = item.get("salaryLow", 0) or 0
    sal_max_raw = item.get("salaryHigh", 0) or 0
    # s5: 薪資類型 (1=時薪, 2=日薪, 3=月薪, 4=論件計酬, 6=年薪)
    sal_type = item.get("s5", 3)  # 預設為月薪

    # 正規化到月薪
    sal_min = normalize_salary_to_monthly(sal_min_raw, sal_type)
    sal_max = normalize_salary_to_monthly(sal_max_raw, sal_type)

    # 薪資描述：統一以月薪格式呈現
    if sal_min and sal_max:
        salary_desc = f"月薪 {sal_min:,}～{sal_max:,} 元"
    elif sal_min:
        salary_desc = f"月薪 {sal_min:,} 元以上"
    else:
        salary_desc = "面議"

    return {
        "job_id": job_id,
        "title": item.get("jobName", ""),
        "company_name": item.get("custName", ""),
        "company_id": item.get("custNo", ""),
        "area": item.get("jobAddrNoDesc", ""),
        "salary_min": sal_min,
        "salary_max": sal_max,
        "salary_desc": salary_desc,
        "job_url": job_url or f"https://www.104.com.tw/job/{job_id}",
    }


# --------------------------------------------------------------------------- #
# 詳情解析
# --------------------------------------------------------------------------- #

def parse_detail(raw: dict) -> dict:
    data = raw.get("data", {})
    condition = data.get("condition", {})
    job_detail = data.get("jobDetail", {})
    welfare = data.get("welfare", {})

    # ── 技能：specialty + skill + language ──
    seen_skills: set = set()
    skills = []

    def _add_skill(raw: str):
        normed = normalize_skill(raw)
        if normed and normed not in seen_skills:
            seen_skills.add(normed)
            skills.append(normed)

    for tag in condition.get("specialty", []):
        if isinstance(tag, dict):
            name = tag.get("description", tag.get("code", "")).strip()
        else:
            name = str(tag).strip()
        if name:
            _add_skill(name)
    for tag in condition.get("skill", []):
        if isinstance(tag, dict):
            name = tag.get("description", tag.get("code", "")).strip()
        else:
            name = str(tag).strip()
        if name:
            _add_skill(name)
    for lang in condition.get("language", []):
        lang_name = lang.get("language", "").strip()
        if lang_name:
            _add_skill(f"{lang_name}（外語）")

    # ── 工作條件 ──
    experience = condition.get("workExp", "")
    education = condition.get("edu", "")
    other = condition.get("other", "").strip()

    # ── 薪資（從 jobDetail 取，比列表準確）──
    salary_desc = job_detail.get("salary", "")
    sal_min_raw = job_detail.get("salaryMin", 0) or 0
    sal_max_raw = job_detail.get("salaryMax", 0) or 0

    # 推測薪資類型（從 salary_desc 或直接欄位）
    # detail API: 10=面議, 20=時薪, 30=日薪, 40=論件計酬, 50=月薪, 60=年薪
    sal_type = job_detail.get("salaryType", 50)  # 預設月薪

    # 正規化到月薪
    sal_min = normalize_salary_to_monthly(sal_min_raw, sal_type)
    sal_max = normalize_salary_to_monthly(sal_max_raw, sal_type)

    # ── 工作地址 ──
    area = job_detail.get("addressRegion", "")
    area_detail = job_detail.get("addressDetail", "")

    # ── 其他 ──
    manage_resp = job_detail.get("manageResp", "")
    need_emp = job_detail.get("needEmp", "")

    return {
        "experience": experience,
        "education": education,
        "job_type": job_detail.get("jobType", ""),
        "skills": json.dumps(skills, ensure_ascii=False),
        "other": other or None,
        "description": job_detail.get("jobDescription", ""),
        "welfare": welfare.get("welfare", ""),
        "salary_min": sal_min or None,
        "salary_max": sal_max or None,
        "salary_desc": salary_desc or None,
        "area": area or None,
        "area_detail": area_detail or None,
    }



# --------------------------------------------------------------------------- #
# 內容 hash（用於判斷是否有更新）
# --------------------------------------------------------------------------- #

HASH_FIELDS = ["title", "salary_desc", "description", "skills", "experience", "education", "welfare"]


def compute_hash(job: dict) -> str:
    content = "|".join(str(job.get(f) or "") for f in HASH_FIELDS)
    return hashlib.md5(content.encode("utf-8")).hexdigest()
