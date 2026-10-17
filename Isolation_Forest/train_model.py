
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "transactions.csv"
MODEL_PATH = BASE_DIR / "isolation_forest.pkl"

FEATURE_COLUMNS = ["amount", "recent_transfers"]


def train_model():
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"{DATA_PATH} not found. Run generate_data.py first."
        )

    df = pd.read_csv(DATA_PATH)

    missing = set(FEATURE_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    features = df[FEATURE_COLUMNS]

    if features.empty or features.isna().any().any():
        raise ValueError("Training features are empty or contain missing values.")

    model = make_pipeline(
        StandardScaler(),
        IsolationForest(
            n_estimators=100,
            contamination=0.10,
            random_state=42,
        ),
    )

    model.fit(features)
    joblib.dump(model, MODEL_PATH)

    predictions = model.predict(features)

    print("AI model trained and saved successfully!")
    print(f"Training records: {len(df)}")
    print(f"Records flagged as unusual: {(predictions == -1).sum()}")
    print(f"Model saved to: {MODEL_PATH}")

    return model


if __name__ == "__main__":
    train_model()
