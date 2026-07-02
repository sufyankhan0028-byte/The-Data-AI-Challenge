"""
Candidate Contradiction Detector
================================
Identifies anomalous, contradictory, or fraudulent signals in a candidate profile.
Calculates a contradiction_score and returns discrete reasoning.
"""
from typing import Any, Dict, List, Tuple

class CandidateContradictionDetector:
    
    @staticmethod
    def detect(candidate: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs heuristic rules to detect anomalies in a candidate profile.
        Returns a dictionary containing the final score (0.0 to 1.0) and a list of reasons.
        """
        profile = candidate.get("profile", {})
        skills = candidate.get("skills", [])
        career = candidate.get("career_history", [])
        education = candidate.get("education", [])
        
        reasons = []
        score = 0.0
        
        current_title = profile.get("current_title", "").lower()
        summary = profile.get("summary", "").lower()
        yoe = profile.get("years_of_experience", 0.0)
        
        skill_names = [s.get("name", "").lower() for s in skills]
        ai_skills = {"pytorch", "tensorflow", "llm", "transformers", "langchain", "machine learning", "deep learning"}
        has_ai_skills = any(skill in ai_skills for skill in skill_names)

        # 1. Marketing manager with advanced AI profile
        if "marketing" in current_title and has_ai_skills:
            # Check if proficiency is marked as advanced
            advanced_ai = any(
                s.get("name", "").lower() in ai_skills and s.get("proficiency", "") == "advanced" 
                for s in skills
            )
            if advanced_ai:
                reasons.append("Anomalous skillset: Marketing title with advanced AI framework skills.")
                score += 0.3

        # 2. AI engineer with no technical career history
        if "ai" in current_title or "machine learning" in current_title:
            is_technical_history = False
            for job in career:
                job_title = job.get("title", "").lower()
                if any(t in job_title for t in ["engineer", "developer", "data", "science", "ml", "ai", "scientist"]):
                    is_technical_history = True
                    break
            if career and not is_technical_history:
                reasons.append("Contradictory career: AI title but previous roles are non-technical.")
                score += 0.4

        # 3. Unrealistic experience claims
        # Compare profile YoE vs sum of duration_months
        total_career_months = sum([job.get("duration_months", 0) for job in career])
        calculated_yoe = total_career_months / 12.0
        if yoe > 0 and calculated_yoe > 0:
            if abs(yoe - calculated_yoe) > 5.0:  # 5 years discrepancy
                reasons.append(f"Unrealistic experience claim: Stated {yoe} YoE but career history adds up to {calculated_yoe:.1f} YoE.")
                score += 0.3

        # Also check for impossible skill duration (e.g. 10 years in LangChain)
        for s in skills:
            name = s.get("name", "").lower()
            dur = s.get("duration_months", 0)
            if name == "langchain" and dur > 36:
                reasons.append(f"Unrealistic skill duration: Claimed {dur} months in LangChain (framework is newer than this).")
                score += 0.5
            if name == "chatgpt" and dur > 48:
                reasons.append(f"Unrealistic skill duration: Claimed {dur} months in ChatGPT.")
                score += 0.5

        # 4. Contradictory summaries
        if "software engineer" in summary and "recruiter" in current_title:
            reasons.append("Contradictory summary: Summary implies software engineering while current title is recruiter.")
            score += 0.2

        # 5. Skill stuffing
        if len(skills) > 60:
            reasons.append(f"Skill stuffing: Profile lists {len(skills)} discrete skills, which is abnormally high.")
            score += 0.3

        # 6. Education timeline anomalies
        if education:
            for edu in education:
                start = edu.get("start_year", 0)
                end = edu.get("end_year", 0)
                if start > 0 and end > 0 and start > end:
                    reasons.append(f"Education anomaly: Start year {start} is after end year {end}.")
                    score += 0.3
                    break

        # 7. Career timeline anomalies
        import datetime
        for job in career:
            try:
                start_str = job.get("start_date")
                end_str = job.get("end_date")
                if start_str and end_str:
                    start_date = datetime.datetime.strptime(start_str[:10], "%Y-%m-%d")
                    end_date = datetime.datetime.strptime(end_str[:10], "%Y-%m-%d")
                    if start_date > end_date:
                        reasons.append(f"Career anomaly: Job start date {start_str} is after end date {end_str}.")
                        score += 0.3
                        break
            except Exception:
                pass  # Ignore parse errors

        # 8. Too many unrelated skills
        # E.g., someone with React, AWS, Nursing, Dentistry, and PyTorch
        unrelated_categories = {"nursing", "plumbing", "dentistry", "hr", "payroll", "salesforce admin"}
        if len(unrelated_categories.intersection(skill_names)) > 0 and has_ai_skills:
            reasons.append("Unrelated skill clusters: Profile combines highly technical AI skills with completely unrelated manual/administrative skills.")
            score += 0.2

        # 9. Senior title with beginner skills
        is_senior = any(t in current_title for t in ["senior", "principal", "staff", "lead", "director"])
        if is_senior and skills:
            # Check if all skills have less than 24 months duration or beginner proficiency
            all_beginner = all(
                s.get("proficiency", "beginner") == "beginner" or s.get("duration_months", 0) < 24 
                for s in skills
            )
            if all_beginner:
                reasons.append("Contradictory seniority: Title implies Senior/Lead, but all listed skills are beginner proficiency or < 2 years duration.")
                score += 0.4

        # Bound score between 0.0 and 1.0
        final_score = min(1.0, score)

        return {
            "contradiction_score": final_score,
            "reasons": reasons
        }
