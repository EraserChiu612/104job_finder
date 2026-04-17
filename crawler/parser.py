import re
import json
import hashlib


# --------------------------------------------------------------------------- #
# 列表解析
# --------------------------------------------------------------------------- #

def extract_job_id(link: str) -> str:
    """從 //www.104.com.tw/job/XXXXX 取出 XXXXX"""
    return link.rstrip("/").split("/")[-1]


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
    sal_min = item.get("salaryLow", 0) or 0
    sal_max = item.get("salaryHigh", 0) or 0
    # s5: 薪資類型 (1=時薪, 2=日薪, 3=月薪, 4=論件計酬, 6=年薪)
    sal_type = item.get("s5", 0)
    if sal_min and sal_max:
        salary_desc = f"月薪 {sal_min:,}～{sal_max:,} 元" if sal_type == 3 else f"{sal_min:,}～{sal_max:,}"
    elif sal_min:
        salary_desc = f"月薪 {sal_min:,} 元以上" if sal_type == 3 else f"{sal_min:,} 元以上"
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
    skills = []
    for tag in condition.get("specialty", []):
        # 可能是 {"description": "..."} 或直接字串
        if isinstance(tag, dict):
            name = tag.get("description", tag.get("code", "")).strip()
        else:
            name = str(tag).strip()
        if name:
            skills.append(name)
    for tag in condition.get("skill", []):
        if isinstance(tag, dict):
            name = tag.get("description", tag.get("code", "")).strip()
        else:
            name = str(tag).strip()
        if name:
            skills.append(name)
    for lang in condition.get("language", []):
        lang_name = lang.get("language", "").strip()
        if lang_name:
            skills.append(f"{lang_name}（外語）")

    # ── 工作條件 ──
    experience = condition.get("workExp", "")
    education = condition.get("edu", "")
    other = condition.get("other", "").strip()

    # ── 薪資（從 jobDetail 取，比列表準確）──
    salary_desc = job_detail.get("salary", "")
    sal_min = job_detail.get("salaryMin", 0) or 0
    sal_max = job_detail.get("salaryMax", 0) or 0

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
        "description": job_detail.get("jobDescription", ""),
        "welfare": welfare.get("welfare", ""),
        "salary_min": sal_min or None,
        "salary_max": sal_max or None,
        "salary_desc": salary_desc or None,
        "area": area or None,
    }



# --------------------------------------------------------------------------- #
# 內容 hash（用於判斷是否有更新）
# --------------------------------------------------------------------------- #

HASH_FIELDS = ["title", "salary_desc", "description", "skills", "experience", "education", "welfare"]


def compute_hash(job: dict) -> str:
    content = "|".join(str(job.get(f) or "") for f in HASH_FIELDS)
    return hashlib.md5(content.encode("utf-8")).hexdigest()
