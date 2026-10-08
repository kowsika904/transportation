import os
import json
from typing import Dict, Any

def get_saved_metrics(model_dir: str = None) -> Dict[str, Any]:
    if model_dir is None:
        model_dir = os.path.join(os.path.dirname(__file__), "..", "saved_models")
    metrics_path = os.path.join(model_dir, "ml_metrics.json")
    if not os.path.exists(metrics_path):
        from app.ml.train import train_and_evaluate_xgboost
        return train_and_evaluate_xgboost(model_dir)
    with open(metrics_path, "r") as f:
        return json.load(f)
