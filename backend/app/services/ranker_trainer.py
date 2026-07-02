"""
Ranker Trainer
==============
Trains a LightGBM Ranker (Learning-to-Rank) using pseudo-labeled data.
Performs cross-validation, saves the model, feature importances, and SHAP values.
"""
import os
import pickle
from pathlib import Path
from typing import Any, Dict, List, Tuple

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

try:
    import shap
except ImportError:
    pass  # Handle gracefully if pip install shap hasn't finished yet

from app.utils.logger import get_logger

logger = get_logger(__name__)


class RankerTrainer:
    """
    Service for training a LightGBM Ranker model.
    """
    def __init__(self):
        # We save models to root-level models directory
        self.models_dir = Path("models")
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self.model_path = self.models_dir / "ranker.pkl"
        self.importance_path = self.models_dir / "feature_importance.csv"

    def train_model(
        self, 
        features_df: pd.DataFrame, 
        labels: np.ndarray, 
        group_ids: np.ndarray,
        n_splits: int = 5
    ) -> lgb.LGBMRanker:
        """
        Trains the LGBMRanker using GroupKFold cross-validation.
        `group_ids` are usually the query IDs (e.g. Job ID), because LTR models rank candidates within a query group.
        If this is for a single JD, we can just treat the whole dataset as a single group or chunk it.
        """
        logger.info(f"Training LightGBM Ranker on {len(features_df)} rows with {features_df.shape[1]} features.")
        
        # If there's only 1 group (1 JD), LGBMRanker requires multiple groups for cross-validation splitting.
        # As a fallback for a single JD, we'll arbitrarily split groups into chunks to allow CV.
        unique_groups = np.unique(group_ids)
        if len(unique_groups) < n_splits:
            logger.warning("Not enough query groups for CV. Creating artificial chunks for LTR training.")
            # Create synthetic groups of ~100 candidates each
            group_ids = np.arange(len(features_df)) // 100
        
        gkf = GroupKFold(n_splits=n_splits)
        
        models = []
        cv_scores = []
        
        # We use a single final model trained on everything for the actual persistence,
        # but we do CV to log the NDCG performance.
        
        for fold, (train_idx, val_idx) in enumerate(gkf.split(features_df, labels, groups=group_ids)):
            X_train, y_train = features_df.iloc[train_idx], labels[train_idx]
            X_val, y_val = features_df.iloc[val_idx], labels[val_idx]
            
            group_train = group_ids[train_idx]
            group_val = group_ids[val_idx]
            
            # LGBM requires group sizes, not group IDs
            # Sort by group ID to correctly calculate group sizes
            train_sort_idx = np.argsort(group_train)
            X_train = X_train.iloc[train_sort_idx]
            y_train = y_train[train_sort_idx]
            group_train = group_train[train_sort_idx]
            _, train_group_sizes = np.unique(group_train, return_counts=True)
            
            val_sort_idx = np.argsort(group_val)
            X_val = X_val.iloc[val_sort_idx]
            y_val = y_val[val_sort_idx]
            group_val = group_val[val_sort_idx]
            _, val_group_sizes = np.unique(group_val, return_counts=True)
            
            ranker = lgb.LGBMRanker(
                objective="lambdarank",
                metric="ndcg",
                n_estimators=100,
                learning_rate=0.05,
                random_state=42
            )
            
            # Using callbacks instead of early_stopping_rounds in newer lightgbm
            callbacks = [lgb.early_stopping(stopping_rounds=10, verbose=False)]
            
            ranker.fit(
                X=X_train,
                y=y_train,
                group=train_group_sizes,
                eval_set=[(X_val, y_val)],
                eval_group=[val_group_sizes],
                eval_at=[10, 50],
                callbacks=callbacks
            )
            
            best_score = ranker.best_score_['valid_0']['ndcg@10']
            cv_scores.append(best_score)
            models.append(ranker)
            logger.info(f"Fold {fold+1} NDCG@10: {best_score:.4f}")
            
        logger.info(f"Mean CV NDCG@10: {np.mean(cv_scores):.4f}")
        
        # ── Train Final Model on All Data ──
        logger.info("Training final model on all data...")
        sort_idx = np.argsort(group_ids)
        X_all = features_df.iloc[sort_idx]
        y_all = labels[sort_idx]
        g_all = group_ids[sort_idx]
        _, final_group_sizes = np.unique(g_all, return_counts=True)
        
        final_ranker = lgb.LGBMRanker(
            objective="lambdarank",
            metric="ndcg",
            n_estimators=100,
            learning_rate=0.05,
            random_state=42
        )
        
        final_ranker.fit(
            X=X_all,
            y=y_all,
            group=final_group_sizes
        )
        
        # 3. Save Model
        self._save_model(final_ranker)
        
        # 4. Save Feature Importance
        self._save_feature_importance(final_ranker, features_df.columns.tolist())
        
        # 5. Generate SHAP Values
        self._generate_shap(final_ranker, X_all)
        
        return final_ranker

    def _save_model(self, model: lgb.LGBMRanker) -> None:
        with open(self.model_path, "wb") as f:
            pickle.dump(model, f)
        logger.info(f"Saved Ranker model to {self.model_path}")

    def _save_feature_importance(self, model: lgb.LGBMRanker, feature_names: List[str]) -> None:
        importance = model.feature_importances_
        df = pd.DataFrame({
            "feature": feature_names,
            "importance": importance
        })
        df = df.sort_values(by="importance", ascending=False)
        df.to_csv(self.importance_path, index=False)
        logger.info(f"Saved feature importance to {self.importance_path}")
        
    def _generate_shap(self, model: lgb.LGBMRanker, X: pd.DataFrame) -> None:
        """
        Generates and logs SHAP values for interpretability.
        """
        try:
            import shap
        except ImportError:
            logger.warning("SHAP is not installed. Skipping SHAP value generation.")
            return
            
        logger.info("Calculating SHAP values...")
        # TreeExplainer is extremely fast for LightGBM
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(X)
        
        # We can just save the mean absolute SHAP values as a CSV for reporting
        mean_shap = np.abs(shap_values).mean(axis=0)
        shap_df = pd.DataFrame({
            "feature": X.columns,
            "mean_abs_shap": mean_shap
        })
        shap_df = shap_df.sort_values(by="mean_abs_shap", ascending=False)
        
        shap_path = self.models_dir / "shap_importance.csv"
        shap_df.to_csv(shap_path, index=False)
        logger.info(f"Saved mean SHAP values to {shap_path}")
