"""
Negative Signals Detector
Penalizes candidates who exhibit suspicious patterns (keyword stuffing, data inconsistencies).
"""
from __future__ import annotations

import json
from typing import Dict, List, Tuple

import pandas as pd


def detect_negative_signals(row: pd.Series) -> Tuple[float, List[str]]:
    """
    Returns (penalty 0-1, list of flag descriptions).
    0 = no penalty, 1 = completely penalize.
    """
    flags: List[str] = []
    penalty = 0.0

    # --- Keyword stuffing detection ---
    skills_json = row.get("skills_json", "[]")
    skills = json.loads(skills_json) if isinstance(skills_json, str) else []
    skill_count = len(skills)
    avg_endorse = (
        sum(s.get("endorsements", 0) for s in skills) / skill_count
        if skill_count > 0 else 0
    )
    assessments_json = row.get("skill_assessment_scores_json", "{}")
    assessments = json.loads(assessments_json) if isinstance(assessments_json, str) else {}

    # Many skills but very low endorsements and no assessments
    if skill_count > 15 and avg_endorse < 2 and len(assessments) == 0:
        flags.append(f"Possible keyword stuffing: {skill_count} skills, avg endorsements={avg_endorse:.1f}")
        penalty += 0.10

    # Skills listed as "expert" but zero endorsements and zero assessment
    expert_unverified = [
        s["name"] for s in skills
        if s.get("proficiency") == "expert"
        and s.get("endorsements", 0) == 0
        and s["name"] not in assessments
    ]
    if len(expert_unverified) > 3:
        flags.append(f"{len(expert_unverified)} unverified 'expert' skills")
        penalty += 0.08

    # --- Profile completeness ---
    completeness = float(row.get("profile_completeness_score", 100))
    if completeness < 30:
        flags.append(f"Very low profile completeness: {completeness:.0f}%")
        penalty += 0.05

    # --- Not open to work (no hard penalty, just flag) ---
    if not row.get("open_to_work_flag", True):
        flags.append("Not marked as open to work")
        # Minor signal — recruiter must message first
        penalty += 0.02

    # --- Very long notice period ---
    notice = int(row.get("notice_period_days", 60))
    if notice > 120:
        flags.append(f"Long notice period: {notice} days")
        penalty += 0.03

    # --- Implausibly fast career (many jobs in short time) ---
    career_json = row.get("career_json", "[]")
    career = json.loads(career_json) if isinstance(career_json, str) else []
    if len(career) >= 5:
        total_months = sum(e.get("duration_months", 0) for e in career)
        avg_tenure = total_months / len(career)
        if avg_tenure < 6:
            flags.append(f"High job hopping: avg tenure {avg_tenure:.0f} months")
            penalty += 0.05

    return min(penalty, 0.35), flags  # cap at 35% penalty
