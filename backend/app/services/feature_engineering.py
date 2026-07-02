"""
Feature Engineering Service
===========================
Generates a 28-dimensional dense feature vector for a candidate vs. a Job Description.
Extracts deep semantic, experience, career, behavioral, and location features.
"""
from typing import Any, Dict, Optional

from app.schemas.features import FeatureVector

class FeatureEngineeringService:
    
    @staticmethod
    def generate_features(
        candidate: Dict[str, Any], 
        jd_requirements: Dict[str, Any],
        bm25_score: float = 0.0,
        embedding_score: float = 0.0
    ) -> FeatureVector:
        """
        Parses raw candidate dict and JD requirements to generate the 28D feature vector.
        """
        profile = candidate.get("profile", {})
        signals = candidate.get("redrob_signals", {})
        skills = candidate.get("skills", [])
        career = candidate.get("career_history", [])
        
        # ── Semantic Features ──
        # bm25 and embeddings are usually passed in from the Retrieval Engine
        
        # Skill overlap
        jd_must = set(jd_requirements.get("must_have_skills", []))
        cand_skills = {s.get("name", "").lower() for s in skills}
        jd_must_lower = {s.lower() for s in jd_must}
        
        overlap = len(jd_must_lower.intersection(cand_skills))
        skill_overlap_score = overlap / len(jd_must_lower) if jd_must_lower else 1.0

        # ── Experience Features ──
        yoe = profile.get("years_of_experience", 0.0)
        req_min = jd_requirements.get("required_experience_min") or 0.0
        req_max = jd_requirements.get("required_experience_max") or 99.0
        
        if req_min <= yoe <= req_max:
            yoe_score = 1.0
        elif yoe > req_max:
            yoe_score = 0.8  # slightly overqualified
        else:
            yoe_score = yoe / req_min if req_min > 0 else 0.0
            
        seniority_map = {"intern": 0, "junior": 1, "mid": 2, "senior": 3, "lead": 4, "principal": 5}
        req_seniority = seniority_map.get(str(jd_requirements.get("seniority_level", "unknown")), 2)
        # Approximate cand seniority based on YoE
        if yoe < 2: cand_sen = 1
        elif yoe < 5: cand_sen = 2
        elif yoe < 8: cand_sen = 3
        else: cand_sen = 4
        
        sen_score = 1.0 - (abs(req_seniority - cand_sen) * 0.2)
        sen_score = max(0.0, sen_score)
        
        prod_ml_score = 1.0 if "docker" in cand_skills or "kubernetes" in cand_skills or "mlops" in cand_skills else 0.0
        startup_score = 1.0 if "startup" in profile.get("summary", "").lower() else 0.0
        leadership_score = 1.0 if "lead" in profile.get("current_title", "").lower() or "manager" in profile.get("current_title", "").lower() else 0.0

        # ── Career Features ──
        job_hops = len(career)
        average_tenure = 0.0
        if job_hops > 0:
            total_months = sum([c.get("duration_months", 0) for c in career])
            average_tenure = (total_months / 12.0) / job_hops
            
        career_growth_score = 1.0 if average_tenure > 2.0 else 0.5
        title_progression_score = 1.0 if job_hops > 1 and "senior" in profile.get("current_title", "").lower() else 0.5

        # ── Skill Features (Explicit checks for specific tech) ──
        vector_db_score = 1.0 if any(db in cand_skills for db in ["pinecone", "weaviate", "milvus", "qdrant", "faiss"]) else 0.0
        retrieval_score = 1.0 if any(r in cand_skills for r in ["bm25", "elasticsearch", "solr", "retrieval"]) else 0.0
        ranking_score = 1.0 if any(r in cand_skills for r in ["ranking", "learning to rank", "xgboost", "lightgbm"]) else 0.0
        python_score = 1.0 if "python" in cand_skills else 0.0
        llm_score = 1.0 if any(l in cand_skills for l in ["llm", "gpt", "langchain", "llamaindex", "huggingface"]) else 0.0
        fine_tuning_score = 1.0 if any(f in cand_skills for f in ["lora", "qlora", "fine-tuning", "peft"]) else 0.0
        open_source_score = 1.0 if signals.get("github_activity_score", 0) > 0.5 else 0.0

        # ── Behavioral Features ──
        recruiter_response_rate = signals.get("recruiter_response_rate", 0.0)
        github_activity_score = signals.get("github_activity_score", 0.0)
        interview_completion_rate = signals.get("interview_completion_rate", 0.0)
        profile_views_score = min(1.0, signals.get("profile_views_30d", 0.0) / 100.0)
        saved_by_recruiters_score = min(1.0, signals.get("saved_by_recruiters_30d", 0.0) / 20.0)
        profile_completeness_score = signals.get("profile_completeness_score", 0.8)
        open_to_work_score = 1.0 if signals.get("open_to_work") else 0.0
        recent_activity_score = 1.0 if signals.get("last_active_date") else 0.0
        notice_period_score = 1.0 if signals.get("notice_period_days", 90) <= 30 else 0.5

        # ── Location Features ──
        country = profile.get("country", "").lower()
        india_score = 1.0 if "india" in country else 0.0
        relocation_score = 1.0 if signals.get("willing_to_relocate") else 0.0
        hybrid_score = 1.0 if signals.get("open_to_hybrid") else 0.0

        return FeatureVector(
            embedding_similarity=embedding_score,
            bm25_score=bm25_score,
            skill_overlap_score=skill_overlap_score,
            
            years_experience_score=yoe_score,
            seniority_score=sen_score,
            production_ml_score=prod_ml_score,
            startup_score=startup_score,
            leadership_score=leadership_score,
            
            average_tenure=average_tenure,
            job_hops=job_hops,
            career_growth_score=career_growth_score,
            title_progression_score=title_progression_score,
            
            vector_db_score=vector_db_score,
            retrieval_score=retrieval_score,
            ranking_score=ranking_score,
            python_score=python_score,
            llm_score=llm_score,
            fine_tuning_score=fine_tuning_score,
            open_source_score=open_source_score,
            
            recruiter_response_rate=recruiter_response_rate,
            github_activity_score=github_activity_score,
            interview_completion_rate=interview_completion_rate,
            profile_views_score=profile_views_score,
            saved_by_recruiters_score=saved_by_recruiters_score,
            profile_completeness_score=profile_completeness_score,
            open_to_work_score=open_to_work_score,
            recent_activity_score=recent_activity_score,
            notice_period_score=notice_period_score,
            
            india_score=india_score,
            relocation_score=relocation_score,
            hybrid_score=hybrid_score
        )
