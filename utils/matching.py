"""مطابقة محلية قابلة للتفسير بين ملف الباحث وإعلان الوظيفة."""

import re
from typing import Dict, List, Tuple


def _norm(value) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _contains(a, b) -> bool:
    a, b = _norm(a), _norm(b)
    return bool(a and b and (a in b or b in a))


def score_match(user: Dict, job: Dict) -> Tuple[int, List[str]]:
    score = 0
    reasons = []

    user_region, job_region = user.get("region"), job.get("region")
    if not job_region or job_region in ("أي منطقة", "عن بُعد (Remote)") or \
            user_region in ("أي منطقة", job_region, "عن بُعد (Remote)"):
        score += 20
        reasons.append("الموقع مناسب")

    if _contains(user.get("category"), job.get("category")):
        score += 25
        reasons.append("المجال الوظيفي مناسب")
    elif _contains(user.get("specialization"), job.get("title")) or \
            _contains(user.get("specialization"), job.get("specialization")):
        score += 20
        reasons.append("التخصص الدقيق قريب")

    if _contains(user.get("specialization"), job.get("title")) or \
            _contains(user.get("specialization"), job.get("specialization")):
        score += 20
        if "التخصص الدقيق قريب" not in reasons:
            reasons.append("التخصص الدقيق مناسب")

    if _contains(user.get("work_type"), job.get("work_type")) or \
            not job.get("work_type"):
        score += 10
        reasons.append("نوع الدوام مناسب")

    if _contains(user.get("experience_level"), job.get("requirements")) or \
            not job.get("requirements"):
        score += 10
        reasons.append("الخبرة تبدو مناسبة")

    if _contains(user.get("salary_range"), job.get("salary")) or not job.get("salary"):
        score += 5
        reasons.append("الراتب متوافق أو قابل للتفاوض")

    return min(score, 100), reasons[:4]


def matching_users(users: List[Dict], job: Dict, threshold: int = 55):
    result = []
    for user in users:
        score, reasons = score_match(user, job)
        if score >= threshold:
            enriched = dict(user)
            enriched["match_score"] = score
            enriched["match_reasons"] = reasons
            result.append(enriched)
    return sorted(result, key=lambda item: item["match_score"], reverse=True)