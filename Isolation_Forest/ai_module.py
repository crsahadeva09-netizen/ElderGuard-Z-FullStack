
from pathlib import Path

import joblib
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "transactions.csv"
MODEL_PATH = BASE_DIR / "isolation_forest.pkl"

FEATURE_COLUMNS = ["amount", "recent_transfers"]


def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model not found: {MODEL_PATH}. "
            "Run train_model.py first."
        )

    return joblib.load(MODEL_PATH)


def load_training_data():
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Training data not found: {DATA_PATH}. "
            "Run generate_data.py first."
        )

    return pd.read_csv(DATA_PATH)


def analyze_transaction(
    user_id,
    amount,
    recipient_type,
    recent_transfers,
    current_transaction_number=None,
    previous_transactions=None,
):
    if amount < 0 or recent_transfers < 0:
        raise ValueError("Amount and recent transfers cannot be negative.")

    if recipient_type not in {"known", "new"}:
        raise ValueError("recipient_type must be 'known' or 'new'.")

    # Prefer actual transaction history provided by the backend.
    if previous_transactions is not None:
        history = [
            float(item["amount"] if isinstance(item, dict) else item)
            for item in previous_transactions
        ]
    elif current_transaction_number is not None:
        df = load_training_data()
        history = df.loc[
            (df["user_id"] == user_id)
            & (df["transaction_number"] < current_transaction_number),
            "amount",
        ].astype(float).tolist()
    else:
        history = []

    previous_average = (
        sum(history) / len(history) if history else 0.0
    )

    model = load_model()
    transaction = pd.DataFrame(
        [[amount, recent_transfers]],
        columns=FEATURE_COLUMNS,
    )

    prediction = int(model.predict(transaction)[0])

    behaviour_anomaly = (
        previous_average > 0
        and amount > 2 * previous_average
    )
    new_recipient = recipient_type == "new"
    multiple_transfers = recent_transfers >= 4
    model_anomaly = prediction == -1

    reasons = []

    if behaviour_anomaly:
        reasons.append(
            "Amount is much higher than the customer's historical average"
        )
    if new_recipient:
        reasons.append("Payment is made to a new recipient")
    if multiple_transfers:
        reasons.append("Multiple recent transfers detected")
    if model_anomaly:
        reasons.append("Isolation Forest detected an unusual pattern")

    warning_count = sum([
        behaviour_anomaly,
        new_recipient,
        multiple_transfers,
        model_anomaly,
    ])

    if warning_count >= 3:
        risk_level = "High"
        action = "Flag for urgent review"
    elif warning_count >= 1:
        risk_level = "Medium"
        action = "Request additional verification"
    else:
        risk_level = "Low"
        action = "Allow transaction; continue monitoring"

    return {
        "user_id": user_id,
        "amount": amount,
        "risk_level": risk_level,
        "unusual": warning_count > 0,
        "previous_average": round(previous_average, 2),
        "explanation": (
            "; ".join(reasons)
            if reasons
            else "No unusual pattern detected"
        ),
        "suggested_action": action,
        "model_anomaly": model_anomaly,
        "behaviour_anomaly": behaviour_anomaly,
    }


if __name__ == "__main__":
    result = analyze_transaction(
        user_id=101,
        amount=15000,
        recipient_type="new",
        recent_transfers=5,
        previous_transactions=[1000, 1200, 900],
    )
    print(result)
