"""
Pseudo Label Generator
======================
Automatically assigns heuristic labels to retrieved candidates to generate
training data for Learning-to-Rank models.

Labels:
3 = Excellent
2 = Good
1 = Average
0 = Poor
"""
import csv
from pathlib import Path
from typing import Any, Dict, List

from app.services.contradiction_detector import CandidateContradictionDetector
from app.services.honeypot_detector import HoneypotDetector
from app.services.feature_engineering import FeatureEngineeringService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PseudoLabelGenerator:
    """
    Generates CSV of pseudo-labels by combining semantic scores with
    production heuristics and fraud detection.
    """
    def __init__(self, output_path: str = "data/training/pseudo_labels.csv"):
        self.contradiction_detector = CandidateContradictionDetector()
        self.honeypot_detector = HoneypotDetector()
        
        # Use absolute path based on project root if relative
        if not Path(output_path).is_absolute():
            project_root = Path(__file__).parent.parent.parent.parent
            self.output_path = project_root / output_path
        else:
            self.output_path = Path(output_path)
            
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def generate_labels(
        self, 
        candidates: List[Dict[str, Any]], 
        jd_requirements: Dict[str, Any]
    ) -> None:
        """
        Processes a list of retrieved candidates (must contain 'candidate' dict and 'hybrid_score').
        Generates 0-3 labels and exports to CSV.
        
        Expected input format:
        [
            {
                "candidate": {... raw candidate json ...},
                "hybrid_score": 0.85
            }
        ]
        """
        logger.info(f"Generating pseudo-labels for {len(candidates)} candidates...")
        
        labeled_data = []
        
        for item in candidates:
            cand = item.get("candidate", {})
            cand_id = cand.get("candidate_id", "UNKNOWN")
            hybrid_score = item.get("hybrid_score", 0.0)
            
            # 1. Run Fraud Detectors
            contra_res = self.contradiction_detector.detect(cand)
            honey_res = self.honeypot_detector.detect(cand)
            
            contra_score = contra_res.get("contradiction_score", 0.0)
            honey_score = honey_res.get("honeypot_probability", 0.0)
            
            # 2. Extract Features
            # We pass 0.0 for bm25/embed since hybrid_score represents the combined semantic power
            features = FeatureEngineeringService.generate_features(
                candidate=cand,
                jd_requirements=jd_requirements,
                bm25_score=0.0,
                embedding_score=0.0 
            )
            
            # 3. Exact Heuristic Scoring Algorithm
            yoe = cand.get("profile", {}).get("years_of_experience", 0)
            
            has_prod_ml = features.production_ml_score > 0
            has_retrieval = features.retrieval_score > 0
            has_embeddings = features.embedding_similarity > 0.5  # Semantic proxy for embeddings
            has_vector_db = features.vector_db_score > 0
            
            strong_behavior = (features.github_activity_score > 0.5) or (features.recruiter_response_rate > 0.5)
            
            # 4. Label Assignment
            # Bad (0): non-technical, contradictory, impossible
            if contra_score >= 0.4 or honey_score >= 0.4 or features.python_score == 0:
                label = 0
                reason = "Bad Fit: Non-technical, contradictory, or impossible profile"
            else:
                # Excellent (3): 5-9 YoE, production ML, retrieval, embeddings, vector databases, strong behavioral
                if (5 <= yoe <= 9) and has_prod_ml and has_retrieval and has_embeddings and has_vector_db and strong_behavior:
                    label = 3
                    reason = "Excellent Fit: Meets all exact required ML/Retrieval criteria"
                # Good (2): some missing skills
                elif (yoe >= 3) and (has_prod_ml or has_retrieval or has_vector_db):
                    label = 2
                    reason = "Good Fit: Missing some core skills but has solid ML foundations"
                # Weak (1): adjacent profile
                elif features.python_score > 0 or hybrid_score > 0.4:
                    label = 1
                    reason = "Weak Fit: Adjacent technical profile lacking specific ML/Retrieval experience"
                else:
                    label = 0
                    reason = "Bad Fit: Lacks technical alignment"
                    
            labeled_data.append({
                "candidate_id": cand_id,
                "label": label,
                "hybrid_score": round(hybrid_score, 4),
                "contradiction_score": round(contra_score, 2),
                "honeypot_score": round(honey_score, 2),
                "reason": reason
            })
            
        # Export to CSV
        with open(self.output_path, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                "candidate_id", "label", "hybrid_score", 
                "contradiction_score", "honeypot_score", "reason"
            ])
            writer.writeheader()
            writer.writerows(labeled_data)
            
        logger.info(f"Successfully exported {len(labeled_data)} labels to {self.output_path}")
