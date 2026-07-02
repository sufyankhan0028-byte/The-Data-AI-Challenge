"""
Honeypot Detector Service
=========================
Identifies low-quality, AI-generated, or fraudulent candidate profiles.
Returns a probability score (0.0 to 1.0) and human-readable reasons.
"""
from typing import Any, Dict, List
import datetime

class HoneypotDetector:
    """
    Detects impossible or highly suspicious claims in raw candidate JSON.
    """

    # Technology release years for timeline validation
    TECH_RELEASE_YEARS: Dict[str, int] = {
        "pytorch": 2016,
        "tensorflow": 2015,
        "kubernetes": 2014,
        "docker": 2013,
        "react": 2013,
        "langchain": 2022,
        "llamaindex": 2022,
        "chatgpt": 2022,
        "genai": 2021,
        "transformers": 2017,
    }

    @staticmethod
    def detect(candidate: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates a honeypot probability score (0.0 to 1.0) and generates reasoning.
        """
        profile = candidate.get("profile", {})
        skills = candidate.get("skills", [])
        career = candidate.get("career_history", [])
        signals = candidate.get("redrob_signals", {})
        
        reasons = []
        probability = 0.0
        
        yoe = profile.get("years_of_experience", 0.0)
        current_title = profile.get("current_title", "").lower()
        
        # Helper: Extract skill names and lowercase them
        skill_names = {s.get("name", "").lower() for s in skills}

        # 1. Impossible profiles (e.g., claims of 10+ years in frameworks that didn't exist)
        current_year = datetime.datetime.now().year
        for skill in skills:
            name = skill.get("name", "").lower()
            claimed_years = skill.get("duration_months", 0) / 12.0
            
            for tech, release_year in HoneypotDetector.TECH_RELEASE_YEARS.items():
                if tech in name:
                    max_possible_years = current_year - release_year
                    if claimed_years > (max_possible_years + 1):  # 1 yr leeway for betas
                        probability += 0.4
                        reasons.append(f"Impossible profile: Claimed {claimed_years:.1f} years in {name}, which only released in {release_year}.")

        # 2. Synthetic inconsistencies (e.g., backend title with ONLY frontend skills)
        frontend_kws = {"react", "angular", "vue", "css", "html", "javascript"}
        backend_kws = {"java", "spring", "golang", "c#", "kubernetes", "docker", "backend"}
        has_fe_title = "frontend" in current_title or "ui " in current_title
        has_be_title = "backend" in current_title or "back-end" in current_title
        
        if has_fe_title and not any(k in skill_names for k in frontend_kws):
            probability += 0.3
            reasons.append("Synthetic inconsistency: Frontend title with zero frontend skills.")
        if has_be_title and not any(k in skill_names for k in backend_kws):
            probability += 0.3
            reasons.append("Synthetic inconsistency: Backend title with zero backend skills.")

        # 3. Keyword stuffing (Skills per YoE ratio or sheer volume)
        if len(skills) > 75:
            probability += 0.2
            reasons.append(f"Keyword stuffing: {len(skills)} discrete skills is statistically improbable.")
        if yoe > 0:
            skills_per_year = len(skills) / yoe
            if skills_per_year > 20 and yoe >= 3:
                probability += 0.3
                reasons.append("Keyword stuffing: Claiming to master 20+ entirely new technologies every single year.")

        # 4. Behavioral twins (e.g., identical response rates and views to known bots)
        # We heuristic this via perfectly clean round numbers that bots often emit
        rr = signals.get("recruiter_response_rate", -1.0)
        views = signals.get("profile_views_30d", -1.0)
        if rr == 1.0 and views > 1000 and len(skills) > 50:
            probability += 0.2
            reasons.append("Behavioral anomaly: Perfect response rate with hyper-inflated views and skills (bot signature).")

        # 5. Unrealistically perfect candidates
        # E.g. claims 5 YoE, knows every single DB, every single Cloud, every single AI framework
        tech_clusters = [
            {"aws", "gcp", "azure"},
            {"pytorch", "tensorflow", "keras"},
            {"react", "angular", "vue"},
            {"postgres", "mongodb", "cassandra", "redis"}
        ]
        mastered_clusters = sum(1 for cluster in tech_clusters if len(cluster.intersection(skill_names)) >= 2)
        if mastered_clusters >= 4 and yoe < 7:
            probability += 0.3
            reasons.append("Unrealistically perfect: Claims mastery of multiple opposing framework clusters across full stack and AI with low YoE.")

        # 6. Contradictory employment history
        total_career_months = sum([job.get("duration_months", 0) for job in career])
        if total_career_months > 0 and yoe > 0:
            claimed_months = yoe * 12
            if claimed_months > (total_career_months + 60):
                probability += 0.3
                reasons.append(f"Contradictory employment: Profile claims {yoe} YoE, but career history only contains {total_career_months/12.0:.1f} years.")

        # 7. AI buzzword stuffing (GenAI without foundations)
        ai_buzz = {"langchain", "llamaindex", "chatgpt", "generative ai", "genai", "prompt engineering"}
        found_buzz = ai_buzz.intersection(skill_names)
        if len(found_buzz) >= 3:
            foundations = {"python", "pytorch", "tensorflow", "scikit-learn", "machine learning"}
            if len(foundations.intersection(skill_names)) == 0:
                probability += 0.5
                reasons.append(f"AI buzzword stuffing: Claimed {len(found_buzz)} GenAI frameworks but zero foundational ML or Python skills.")

        return {
            "honeypot_probability": min(1.0, probability),
            "reasons": reasons
        }
