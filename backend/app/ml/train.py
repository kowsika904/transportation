import os
import json
import joblib
import numpy as np
import pandas as pd

from xgboost import XGBClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, precision_recall_fscore_support
from app.ml.dataset import generate_disruption_dataset, get_train_val_test_splits, FEATURE_COLUMNS, CLASS_NAMES

def train_and_evaluate_xgboost(save_dir: str = None) -> dict:
    if save_dir is None:
        save_dir = os.path.join(os.path.dirname(__file__), "..", "saved_models")
    os.makedirs(save_dir, exist_ok=True)

    print("Generating dataset...")
    df = generate_disruption_dataset(n_samples=2000, seed=42)

    X_train, X_val, X_test, y_train, y_val, y_test, scaler = get_train_val_test_splits(df, seed=42)

    print(f"Dataset split sizes: Train={len(y_train)}, Val={len(y_val)}, Test={len(y_test)}")

    model = XGBClassifier(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.08,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="multi:softprob",
        num_class=5,
        random_state=42,
        eval_metric="mlogloss"
    )

    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=False
    )

    # Predictions on test set
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)

    acc = float(accuracy_score(y_test, y_pred))
    p_macro, r_macro, f1_macro, _ = precision_recall_fscore_support(y_test, y_pred, average="macro")

    cm = confusion_matrix(y_test, y_pred).tolist()

    report_dict = classification_report(y_test, y_pred, target_names=[CLASS_NAMES[i] for i in range(5)], output_dict=True)

    class_wise = {}
    for i in range(5):
        c_name = CLASS_NAMES[i]
        if c_name in report_dict:
            class_wise[c_name] = {
                "precision": float(report_dict[c_name]["precision"]),
                "recall": float(report_dict[c_name]["recall"]),
                "f1_score": float(report_dict[c_name]["f1-score"]),
                "support": int(report_dict[c_name]["support"])
            }

    importances = model.feature_importances_
    feat_imp = {feat: float(imp) for feat, imp in zip(FEATURE_COLUMNS, importances)}

    metrics = {
        "model_name": "XGBoost Disruption Classifier",
        "num_samples": len(df),
        "num_train": len(y_train),
        "num_val": len(y_val),
        "num_test": len(y_test),
        "accuracy": float(acc),
        "macro_precision": float(p_macro),
        "macro_recall": float(r_macro),
        "macro_f1": float(f1_macro),
        "class_wise_metrics": class_wise,
        "confusion_matrix": cm,
        "feature_importances": feat_imp,
    }

    # Save artifacts
    model_path = os.path.join(save_dir, "xgboost_model.json")
    scaler_path = os.path.join(save_dir, "scaler.joblib")
    metrics_path = os.path.join(save_dir, "ml_metrics.json")

    model.save_model(model_path)
    joblib.dump(scaler, scaler_path)

    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"Model saved to {model_path}")
    print(f"Scaler saved to {scaler_path}")
    print(f"Metrics saved to {metrics_path}")
    print(f"Actual Test Accuracy: {acc * 100:.2f}%")
    print(f"Macro F1-Score: {f1_macro:.4f}")

    return metrics

if __name__ == "__main__":
    train_and_evaluate_xgboost()
