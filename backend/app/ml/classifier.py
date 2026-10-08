import os
import json
import joblib
import numpy as np
from typing import Dict, Any, Tuple
from xgboost import XGBClassifier

from app.models.schemas import DisruptionInput, DisruptionClassification
from app.ml.dataset import FEATURE_COLUMNS, CLASS_NAMES

class DisruptionClassifierService:
    def __init__(self, model_dir: str = None):
        if model_dir is None:
            model_dir = os.path.join(os.path.dirname(__file__), "..", "saved_models")
        
        self.model_dir = model_dir
        self.model_path = os.path.join(model_dir, "xgboost_model.json")
        self.scaler_path = os.path.join(model_dir, "scaler.joblib")
        
        self.model = None
        self.scaler = None
        self._load_or_train()

    def _load_or_train(self):
        if not (os.path.exists(self.model_path) and os.path.exists(self.scaler_path)):
            print("Saved model artifacts not found. Training model now...")
            from app.ml.train import train_and_evaluate_xgboost
            train_and_evaluate_xgboost(self.model_dir)

        self.model = XGBClassifier()
        self.model.load_model(self.model_path)
        self.scaler = joblib.load(self.scaler_path)

    def extract_features(self, inp: DisruptionInput) -> np.ndarray:
        speed_ratio = inp.average_speed_mph / max(inp.normal_speed_mph, 1.0)
        speed_ratio = float(np.clip(speed_ratio, 0.0, 1.2))
        incident_val = 1.0 if inp.active_vehicle_incident else 0.0

        raw_vec = np.array([[
            float(inp.severity_level),
            float(inp.wind_speed_mph),
            float(inp.precipitation_inches),
            float(inp.visibility_miles),
            float(inp.temperature_f),
            float(inp.road_capacity_reduction_pct),
            speed_ratio,
            incident_val
        ]])
        return raw_vec

    def predict(self, inp: DisruptionInput) -> DisruptionClassification:
        raw_vec = self.extract_features(inp)
        scaled_vec = self.scaler.transform(raw_vec)

        probas = self.model.predict_proba(scaled_vec)[0]
        class_code = int(np.argmax(probas))
        confidence = float(probas[class_code])
        predicted_class = CLASS_NAMES[class_code]

        prob_dict = {CLASS_NAMES[i]: float(probas[i]) for i in range(len(probas))}

        # Calculate SHAP attributions
        try:
            import shap
            explainer = shap.TreeExplainer(self.model)
            shap_values = explainer.shap_values(scaled_vec)
            
            # For multi-class, shap_values can be shape (1, n_features, n_classes) or list
            if isinstance(shap_values, list):
                class_shap = shap_values[class_code][0]
            elif len(shap_values.shape) == 3:
                class_shap = shap_values[0, :, class_code]
            else:
                class_shap = shap_values[0]

            shap_dict = {feat: float(class_shap[i]) for i, feat in enumerate(FEATURE_COLUMNS)}
        except Exception as e:
            print(f"SHAP calculation fallback: {e}")
            # Fallback to feature importance weighting if SHAP raises version specific issue
            importances = self.model.feature_importances_
            shap_dict = {feat: float(importances[i]) for i, feat in enumerate(FEATURE_COLUMNS)}

        return DisruptionClassification(
            predicted_class=predicted_class,
            class_code=class_code,
            confidence=confidence,
            class_probabilities=prob_dict,
            shap_feature_importance=shap_dict
        )
