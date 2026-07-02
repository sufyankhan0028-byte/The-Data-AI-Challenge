"""
Final Ranking Service
=====================
Orchestrates the complete retrieval, feature engineering, fraud detection,
and Learning-to-Rank pipeline to return the absolute Top 100 candidates.
"""
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from app.services.hybrid_retrieval_service import HybridRetrievalService
from app.services.feature_engineering import FeatureEngineeringService
from app.services.contradiction_detector import CandidateContradictionDetector
from app.services.honeypot_detector import HoneypotDetector
from app.utils.logger import get_logger

logger = get_logger(__name__)


class FinalRankingService:
    """
    Master orchestrator for candidate ranking.
    """
    def __init__(
        self, 
        hybrid_retrieval_service: HybridRetrievalService,
        ranker_model_path: Optional[str] = None
    ):
        self.retrieval = hybrid_retrieval_service
        self.contradiction = CandidateContradictionDetector()
        self.honeypot = HoneypotDetector()
        
        # Load LTR Model
        if ranker_model_path is None:
            # Resolve relative to project root
            project_root = Path(__file__).parent.parent.parent.parent
            self.model_path = project_root / "models" / "ranker.pkl"
        else:
            self.model_path = Path(ranker_model_path)
            
        self.ranker = None
        self._load_model()

    def _load_model(self):
        if self.model_path.exists():
            with open(self.model_path, "rb") as f:
                self.ranker = pickle.load(f)
            logger.info("Successfully loaded LightGBM Ranker model.")
        else:
            logger.warning(f"Ranker model not found at {self.model_path}. Will fallback to Hybrid scoring.")

    def rank_candidates(
        self, 
        jd_parsed: Dict[str, Any], 
        candidates_db: Dict[str, Dict[str, Any]], 
        top_k: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Executes the full pipeline:
        JD -> Retrieval -> Featurization -> Fraud Check -> LTR -> Top 100
        """
        from app.config.ranking_config import load_ranking_weights
        weights = load_ranking_weights()
        print("Loaded Ranking Weights:")
        print(f"Semantic Match: {weights.semantic_match}")
        print(f"Experience: {weights.experience}")
        print(f"Behavioral Signals: {weights.behavioral_signals}")
        print(f"Production Experience: {weights.production_experience}")
        print(f"Startup Experience: {weights.startup_experience}")
        print(f"Career Stability: {weights.career_stability}")
        logger.info("Loaded Ranking Weights:\nSemantic Match: %s\nExperience: %s\nBehavioral Signals: %s\nProduction Experience: %s\nStartup Experience: %s\nCareer Stability: %s",
                    weights.semantic_match, weights.experience, weights.behavioral_signals, weights.production_experience, weights.startup_experience, weights.career_stability)
        # 1. Hybrid Retrieval (Initial coarse pass to get Top 1000)
        logger.info("Executing Hybrid Retrieval pass...")
        retrieved = self.retrieval.retrieve(jd_parsed, top_k=1000)
        
        valid_candidates = []
        feature_matrices = []
        
        logger.info(f"Retrieved {len(retrieved)} candidates. Extracting features and checking fraud...")
        
        # 2. Feature Engineering & Fraud Detection
        for r_cand in retrieved:
            cand_id = r_cand.get("candidate_id")
            if cand_id not in candidates_db:
                continue
                
            raw_json = candidates_db[cand_id]
            
            # Fraud checks
            contra_res = self.contradiction.detect(raw_json)
            honey_res = self.honeypot.detect(raw_json)
            
            # If high fraud probability, drop them immediately from ranking
            if contra_res.get("contradiction_score", 0.0) >= 0.3 or honey_res.get("honeypot_probability", 0.0) >= 0.3:
                continue
                
            # Extract deep semantic/production features
            features = FeatureEngineeringService.generate_features(
                candidate=raw_json,
                jd_requirements=jd_parsed,
                bm25_score=r_cand.get("bm25_norm", 0.0),
                embedding_score=r_cand.get("semantic_score", 0.0)
            )
            
            # Convert Pydantic feature vector to dict
            f_dict = features.model_dump()
            
            valid_candidates.append(cand_id)
            feature_matrices.append(f_dict)
            
        if not valid_candidates:
            logger.warning("All retrieved candidates failed fraud checks or were not found in DB.")
            return []
            
        # 3. Learning to Rank (LightGBM)
        logger.info(f"Scoring {len(valid_candidates)} candidates using LTR...")
        X = pd.DataFrame(feature_matrices)
        
        final_scores = []
        if self.ranker is not None:
            # Predict using LightGBM
            try:
                scores = self.ranker.predict(X)
                final_scores = scores.tolist()
            except Exception as e:
                logger.error(f"Error during LTR prediction: {e}")
                final_scores = [
                    (weights.semantic_match / 100.0) * float(row.get("embedding_similarity", 0.0)) +
                    (weights.experience / 100.0) * float(row.get("years_experience_score", 0.0)) +
                    (weights.behavioral_signals / 100.0) * float(row.get("recruiter_response_rate", 0.0)) +
                    (weights.production_experience / 100.0) * float(row.get("production_ml_score", 0.0)) +
                    (weights.startup_experience / 100.0) * float(row.get("startup_score", 0.0)) +
                    (weights.career_stability / 100.0) * float(row.get("career_growth_score", 0.0))
                    for _, row in X.iterrows()
                ]
        else:
            # Fallback to dynamic weighted score if no LTR model is trained yet
            final_scores = [
                (weights.semantic_match / 100.0) * float(row.get("embedding_similarity", 0.0)) +
                (weights.experience / 100.0) * float(row.get("years_experience_score", 0.0)) +
                (weights.behavioral_signals / 100.0) * float(row.get("recruiter_response_rate", 0.0)) +
                (weights.production_experience / 100.0) * float(row.get("production_ml_score", 0.0)) +
                (weights.startup_experience / 100.0) * float(row.get("startup_score", 0.0)) +
                (weights.career_stability / 100.0) * float(row.get("career_growth_score", 0.0))
                for _, row in X.iterrows()
            ]
            
        # 4. Format and sort results
        results = []
        for i in range(len(valid_candidates)):
            results.append({
                "candidate_id": valid_candidates[i],
                "score": round(float(final_scores[i]), 4),
                "feature_breakdown": feature_matrices[i]
            })
            
        # Sort by LTR score descending
        results = sorted(results, key=lambda x: x["score"], reverse=True)
        
        # Return exact Top 100
        top_results = results[:top_k]
        logger.info(f"Final ranking complete. Returning Top {len(top_results)} candidates.")
        
        return top_results
