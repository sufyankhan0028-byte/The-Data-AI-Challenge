import os
import pickle
import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import GroupKFold

# Ensure directories exist
os.makedirs("models", exist_ok=True)
os.makedirs("analysis", exist_ok=True)

def train_ranker_pipeline():
    print("Loading datasets...")
    
    # 1. Load Features and Labels
    features_path = "processed/features.parquet"
    labels_path = "data/training/manual_labels.csv" # Fallback to manual if pseudo isn't there, or vice versa
    
    if not os.path.exists(labels_path):
        labels_path = "data/training/pseudo_labels.csv"
        
    df_features = pd.read_parquet(features_path)
    df_labels = pd.read_csv(labels_path)
    
    # 2. Align Data (Merge on candidate_id)
    print("Aligning features with labels...")
    df_merged = pd.merge(df_features, df_labels, on="candidate_id", how="inner")
    
    if len(df_merged) == 0:
        print("ERROR: No matching candidate_ids between features and labels!")
        return
        
    print(f"Ready to train on {len(df_merged)} labeled candidates.")
    
    # Extract X and y
    # Drop non-numeric / label columns for training
    drop_cols = ["candidate_id", "label", "reason", "hybrid_score", "points", "contradiction_score", "honeypot_score"]
    feature_cols = [c for c in df_merged.columns if c not in drop_cols]
    
    X = df_merged[feature_cols]
    y = df_merged["label"].values
    
    # For LTR, we need groups. Since this is a single JD, we create synthetic chunks
    # to allow Cross Validation to run properly.
    group_ids = np.arange(len(df_merged)) // 100
    
    # 3. Cross Validation
    print("Running GroupKFold Cross Validation...")
    gkf = GroupKFold(n_splits=5)
    cv_scores = []
    
    for fold, (train_idx, val_idx) in enumerate(gkf.split(X, y, groups=group_ids)):
        X_train, y_train = X.iloc[train_idx], y[train_idx]
        X_val, y_val = X.iloc[val_idx], y[val_idx]
        
        g_train = group_ids[train_idx]
        g_val = group_ids[val_idx]
        
        # Sort by groups for LightGBM
        t_sort = np.argsort(g_train)
        X_train = X_train.iloc[t_sort]
        y_train = y_train[t_sort]
        _, train_group_sizes = np.unique(g_train[t_sort], return_counts=True)
        
        v_sort = np.argsort(g_val)
        X_val = X_val.iloc[v_sort]
        y_val = y_val[v_sort]
        _, val_group_sizes = np.unique(g_val[v_sort], return_counts=True)
        
        ranker = lgb.LGBMRanker(
            objective="lambdarank",
            metric="ndcg",
            n_estimators=100,
            learning_rate=0.05,
            random_state=42
        )
        
        callbacks = [lgb.early_stopping(stopping_rounds=10, verbose=False)]
        
        ranker.fit(
            X=X_train, y=y_train, group=train_group_sizes,
            eval_set=[(X_val, y_val)], eval_group=[val_group_sizes],
            eval_at=[10, 50], callbacks=callbacks
        )
        
        score = ranker.best_score_['valid_0']['ndcg@10']
        cv_scores.append(score)
        print(f"  Fold {fold+1} NDCG@10: {score:.4f}")
        
    print(f"Mean CV NDCG@10: {np.mean(cv_scores):.4f}")
    
    # 4. Train Final Model
    print("Training final model on all data...")
    g_all_sort = np.argsort(group_ids)
    X_all = X.iloc[g_all_sort]
    y_all = y[g_all_sort]
    _, all_group_sizes = np.unique(group_ids[g_all_sort], return_counts=True)
    
    final_ranker = lgb.LGBMRanker(
        objective="lambdarank",
        metric="ndcg",
        n_estimators=100,
        learning_rate=0.05,
        random_state=42
    )
    final_ranker.fit(X_all, y_all, group=all_group_sizes)
    
    # 5. Save Predictions
    df_merged["prediction_score"] = final_ranker.predict(X)
    df_merged[["candidate_id", "label", "prediction_score"]].to_csv("analysis/prediction_scores.csv", index=False)
    print("Saved prediction scores to analysis/prediction_scores.csv")
    
    # 6. Save Model
    model_path = "models/ranker.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(final_ranker, f)
    print(f"Saved LightGBM Ranker to {model_path}")
    
    # 7. Save Feature Importance
    importance_path = "models/feature_importance.csv"
    imp_df = pd.DataFrame({
        "feature": feature_cols,
        "importance": final_ranker.feature_importances_
    }).sort_values(by="importance", ascending=False)
    imp_df.to_csv(importance_path, index=False)
    print(f"Saved feature importance to {importance_path}")
    
    # 8. Generate and Save SHAP Analysis
    try:
        import shap
        print("Calculating SHAP values...")
        explainer = shap.TreeExplainer(final_ranker)
        shap_values = explainer.shap_values(X_all)
        
        mean_shap = np.abs(shap_values).mean(axis=0)
        shap_df = pd.DataFrame({
            "feature": feature_cols,
            "mean_abs_shap": mean_shap
        }).sort_values(by="mean_abs_shap", ascending=False)
        
        shap_path = "analysis/shap_values.csv"
        shap_df.to_csv(shap_path, index=False)
        print(f"Saved SHAP values to {shap_path}")
        
    except ImportError:
        print("WARNING: SHAP is not installed. Skipping SHAP analysis.")

if __name__ == "__main__":
    train_ranker_pipeline()
