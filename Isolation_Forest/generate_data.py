
from pathlib import Path
import random

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = BASE_DIR / "transactions.csv"


def generate_data():
    random.seed(42)
    data = []

    # Generate 100 synthetic customers.
    for user_id in range(101, 201):
        normal_amount = random.randint(500, 5000)

        # Generate 20 transactions per customer.
        for transaction in range(20):
            transaction_number = transaction + 1

            amount = random.randint(
                int(normal_amount * 0.5),
                int(normal_amount * 1.5),
            )

            recipient_type = random.choice(["known", "known", "new"])
            recent_transfers = random.randint(1, 3)

            # Generate occasional unusual transactions.
            if random.random() < 0.10:
                amount = normal_amount * random.randint(5, 10)
                recipient_type = "new"
                recent_transfers = random.randint(4, 7)

            data.append({
                "user_id": user_id,
                "transaction_number": transaction_number,
                "amount": amount,
                "recipient_type": recipient_type,
                "recent_transfers": recent_transfers,
            })

    df = pd.DataFrame(data)
    df = df.sort_values(
        ["user_id", "transaction_number"]
    ).reset_index(drop=True)

    # Calculate averages using only earlier transactions.
    df["previous_average"] = (
        df.groupby("user_id")["amount"]
        .transform(lambda amounts: amounts.shift(1).expanding().mean())
        .fillna(0)
    )

    df.to_csv(OUTPUT_PATH, index=False)

    print("Synthetic transaction data generated successfully!")
    print(f"Customers: {df['user_id'].nunique()}")
    print(f"Transactions: {len(df)}")
    print(f"CSV saved to: {OUTPUT_PATH}")

    return df


if __name__ == "__main__":
    generate_data()
