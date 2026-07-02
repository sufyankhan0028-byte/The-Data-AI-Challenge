"""
Unit tests for the Ranker Trainer.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
from app.services.ranker_trainer import RankerTrainer

class TestRankerTrainer:
    def setup_method(self):
        self.trainer = RankerTrainer()
        # Redirect outputs to test folder
        test_dir = Path(__file__).parent / "test_models"
        self.trainer.models_dir = test_dir
        self.trainer.model_path = test_dir / "ranker.pkl"
        self.trainer.importance_path = test_dir / "feature_importance.csv"

    def teardown_method(self):
        # Cleanup
        if self.trainer.models_dir.exists():
            import shutil
            shutil.rmtree(self.trainer.models_dir)

    def test_train_model(self):
        # Generate dummy data
        np.random.seed(42)
        n_samples = 150
        
        # 5 features
        X = pd.DataFrame(np.random.rand(n_samples, 5), columns=[f"feat_{i}" for i in range(5)])
        
        # Labels 0-3
        y = np.random.randint(0, 4, size=n_samples)
        
        # All belong to the same query group (e.g. 1 JD). 
        # The trainer will artificially chunk it if < n_splits
        group_ids = np.zeros(n_samples)
        
        # Train
        model = self.trainer.train_model(X, y, group_ids, n_splits=3)
        
        assert model is not None
        assert self.trainer.model_path.exists()
        assert self.trainer.importance_path.exists()
        
        # Check importance file
        imp_df = pd.read_csv(self.trainer.importance_path)
        assert len(imp_df) == 5
        assert "feature" in imp_df.columns
        assert "importance" in imp_df.columns


if __name__ == "__main__":
    test_classes = [TestRankerTrainer]
    passed = failed = 0
    print("\n" + "═" * 60)
    print("  RankerTrainer — Unit Tests")
    print("═" * 60)

    for cls in test_classes:
        instance = cls()
        methods = [m for m in dir(instance) if m.startswith("test_")]
        for method_name in methods:
            instance.setup_method()
            try:
                getattr(instance, method_name)()
                print(f"    ✅ {method_name}")
                passed += 1
            except Exception as exc:
                print(f"    ❌ {method_name}")
                import traceback
                traceback.print_exc()
                failed += 1
            finally:
                instance.teardown_method()

    print("\n" + "─" * 60)
    print(f"  Results: {passed} passed, {failed} failed")
    print("─" * 60)
    if failed:
        sys.exit(1)
