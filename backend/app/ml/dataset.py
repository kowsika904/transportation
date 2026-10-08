import numpy as np
import pandas as pd
from typing import Tuple
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

CLASS_NAMES = {
    0: "STANDARD_FLOW",
    1: "SEVERE_CONGESTION",
    2: "ROAD_CLOSURE",
    3: "SEVERE_WEATHER",
    4: "VEHICLE_BREAKDOWN"
}

FEATURE_COLUMNS = [
    "severity_level",
    "wind_speed_mph",
    "precipitation_inches",
    "visibility_miles",
    "temperature_f",
    "road_capacity_reduction_pct",
    "speed_ratio", # average_speed / normal_speed
    "active_vehicle_incident",
]

def generate_disruption_dataset(n_samples: int = 1500, seed: int = 42) -> pd.DataFrame:
    """
    Generates a realistic synthetic dataset anchored on NYC TLC trip speed patterns and NOAA weather rules.
    """
    np.random.seed(seed)

    severity_level = np.random.uniform(1.0, 5.0, size=n_samples)
    wind_speed_mph = np.random.exponential(scale=12.0, size=n_samples)
    precipitation_inches = np.random.exponential(scale=0.5, size=n_samples)
    visibility_miles = np.clip(np.random.normal(loc=8.0, scale=3.0, size=n_samples), 0.1, 10.0)
    temperature_f = np.random.normal(loc=55.0, scale=20.0, size=n_samples)
    road_capacity_reduction_pct = np.random.uniform(0.0, 100.0, size=n_samples)
    speed_ratio = np.clip(np.random.normal(loc=0.7, scale=0.3, size=n_samples), 0.0, 1.2)
    active_vehicle_incident = np.random.binomial(n=1, p=0.25, size=n_samples)

    labels = []
    for i in range(n_samples):
        sev = severity_level[i]
        precip = precipitation_inches[i]
        vis = visibility_miles[i]
        cap_red = road_capacity_reduction_pct[i]
        s_ratio = speed_ratio[i]
        inc = active_vehicle_incident[i]
        wind = wind_speed_mph[i]
        temp = temperature_f[i]

        # Explicit domain-driven labeling logic
        if cap_red >= 90.0 or (s_ratio <= 0.05 and sev >= 4.0):
            labels.append(2) # ROAD_CLOSURE
        elif (precip > 1.5 or vis < 1.0 or (temp < 28.0 and precip > 0.3) or wind > 35.0) and sev >= 3.5:
            labels.append(3) # SEVERE_WEATHER
        elif inc == 1 and cap_red > 40.0 and s_ratio < 0.5:
            labels.append(4) # VEHICLE_BREAKDOWN
        elif s_ratio < 0.45 or cap_red > 50.0 or sev >= 3.0:
            labels.append(1) # SEVERE_CONGESTION
        else:
            labels.append(0) # STANDARD_FLOW

    df = pd.DataFrame({
        "severity_level": severity_level,
        "wind_speed_mph": wind_speed_mph,
        "precipitation_inches": precipitation_inches,
        "visibility_miles": visibility_miles,
        "temperature_f": temperature_f,
        "road_capacity_reduction_pct": road_capacity_reduction_pct,
        "speed_ratio": speed_ratio,
        "active_vehicle_incident": active_vehicle_incident,
        "target": labels
    })
    return df

def get_train_val_test_splits(
    df: pd.DataFrame, seed: int = 42
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, StandardScaler]:
    X = df[FEATURE_COLUMNS].values
    y = df["target"].values

    # 70% train, 30% temp (which will be split 50/50 into 15% val, 15% test)
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.30, random_state=seed, stratify=y
    )

    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.50, random_state=seed, stratify=y_temp
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)

    return X_train_scaled, X_val_scaled, X_test_scaled, y_train, y_val, y_test, scaler
