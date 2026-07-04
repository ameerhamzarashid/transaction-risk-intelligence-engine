from pathlib import Path
import json
import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd


SEED = 42
random.seed(SEED)
np.random.seed(SEED)

OUTPUT_DIR = Path("data/synthetic")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


FIRST_NAMES = [
    "Aisha", "James", "Maya", "Daniel", "Fatima", "Oliver", "Sophia", "Noah",
    "Amelia", "Muhammad", "Isabella", "Ethan", "Zara", "Lucas", "Hannah",
    "Ali", "Grace", "Leo", "Mia", "Adam"
]

LAST_NAMES = [
    "Khan", "Smith", "Patel", "Brown", "Ahmed", "Jones", "Wilson", "Taylor",
    "Hussain", "Davies", "Miller", "Thomas", "Walker", "Ali", "Robinson",
    "Clarke", "Wright", "Green", "Hall", "Young"
]

COUNTRIES = [
    "United Kingdom", "Germany", "France", "United Arab Emirates", "Pakistan",
    "India", "United States", "Canada", "Netherlands", "Nigeria", "Turkey",
    "Singapore", "Spain", "Italy"
]

HIGH_RISK_COUNTRIES = {"Nigeria", "Turkey"}
MEDIUM_RISK_COUNTRIES = {"Pakistan", "United Arab Emirates", "India"}

MERCHANT_CATEGORIES = [
    "Groceries", "Electronics", "Travel", "Gambling", "Crypto Exchange",
    "Luxury Goods", "Restaurants", "Fuel", "Online Marketplace", "Cash Withdrawal",
    "Money Transfer", "Subscription", "Pharmacy", "Hotels"
]

HIGH_RISK_CATEGORIES = {
    "Gambling",
    "Crypto Exchange",
    "Luxury Goods",
    "Money Transfer",
    "Cash Withdrawal",
}

CHANNELS = ["Card Present", "E-Commerce", "Mobile Banking", "Branch", "ATM", "API"]
CURRENCIES = ["GBP", "EUR", "USD"]
ACCOUNT_TYPES = ["Current", "Savings", "Business"]
CUSTOMER_SEGMENTS = ["Retail", "SME", "Corporate", "Private Banking"]


def country_risk(country: str) -> str:
    if country in HIGH_RISK_COUNTRIES:
        return "High"
    if country in MEDIUM_RISK_COUNTRIES:
        return "Medium"
    return "Low"


def random_date_within(days_back: int) -> datetime:
    return datetime.now() - timedelta(
        days=random.randint(0, days_back),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
        seconds=random.randint(0, 59),
    )


def generate_customers(n_customers: int = 1000) -> pd.DataFrame:
    rows = []

    for i in range(1, n_customers + 1):
        country = random.choice(COUNTRIES)
        age = random.randint(18, 82)
        dob = datetime.now() - timedelta(days=age * 365 + random.randint(0, 364))

        rows.append(
            {
                "customer_id": f"CUST{i:06d}",
                "full_name": f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
                "date_of_birth": dob.date().isoformat(),
                "country": country,
                "country_risk_level": country_risk(country),
                "customer_segment": random.choices(
                    CUSTOMER_SEGMENTS,
                    weights=[0.72, 0.18, 0.07, 0.03],
                    k=1,
                )[0],
                "kyc_status": random.choices(
                    ["Verified", "Pending Review", "Failed"],
                    weights=[0.90, 0.08, 0.02],
                    k=1,
                )[0],
                "pep_flag": random.choices([0, 1], weights=[0.98, 0.02], k=1)[0],
                "customer_since": random_date_within(2000).date().isoformat(),
            }
        )

    return pd.DataFrame(rows)


def generate_merchants(n_merchants: int = 250) -> pd.DataFrame:
    rows = []

    for i in range(1, n_merchants + 1):
        country = random.choice(COUNTRIES)
        category = random.choice(MERCHANT_CATEGORIES)

        rows.append(
            {
                "merchant_id": f"MER{i:06d}",
                "merchant_name": f"{category} Merchant {i:03d}",
                "merchant_category": category,
                "merchant_country": country,
                "merchant_country_risk_level": country_risk(country),
                "high_risk_category_flag": int(category in HIGH_RISK_CATEGORIES),
            }
        )

    return pd.DataFrame(rows)


def generate_accounts(customers: pd.DataFrame, n_accounts: int = 1300) -> pd.DataFrame:
    rows = []
    customer_ids = customers["customer_id"].tolist()

    for i in range(1, n_accounts + 1):
        rows.append(
            {
                "account_id": f"ACC{i:06d}",
                "customer_id": random.choice(customer_ids),
                "account_type": random.choices(
                    ACCOUNT_TYPES,
                    weights=[0.70, 0.20, 0.10],
                    k=1,
                )[0],
                "account_status": random.choices(
                    ["Active", "Dormant", "Closed"],
                    weights=[0.92, 0.06, 0.02],
                    k=1,
                )[0],
                "opened_date": random_date_within(2500).date().isoformat(),
            }
        )

    return pd.DataFrame(rows)


def generate_transactions(
    customers: pd.DataFrame,
    merchants: pd.DataFrame,
    accounts: pd.DataFrame,
    n_transactions: int = 10000,
) -> pd.DataFrame:
    rows = []

    customer_lookup = customers.set_index("customer_id").to_dict("index")
    merchant_lookup = merchants.set_index("merchant_id").to_dict("index")
    customer_accounts = accounts.groupby("customer_id")["account_id"].apply(list).to_dict()

    customer_ids = customers["customer_id"].tolist()
    merchant_ids = merchants["merchant_id"].tolist()
    all_account_ids = accounts["account_id"].tolist()

    for i in range(1, n_transactions + 1):
        customer_id = random.choice(customer_ids)
        account_id = random.choice(customer_accounts.get(customer_id, all_account_ids))
        merchant_id = random.choice(merchant_ids)

        customer = customer_lookup[customer_id]
        merchant = merchant_lookup[merchant_id]

        amount = round(float(np.random.lognormal(mean=3.6, sigma=1.0)), 2)

        # Inject some deliberately suspicious high-value transactions.
        if random.random() < 0.035:
            amount = round(float(np.random.lognormal(mean=8.0, sigma=0.6)), 2)

        timestamp = random_date_within(180)
        hour = timestamp.hour

        cross_border = int(customer["country"] != merchant["merchant_country"])
        high_amount = int(amount > 1500)
        unusual_hour = int(hour < 5)
        high_risk_category = int(merchant["high_risk_category_flag"] == 1)
        high_risk_country = int(
            customer["country_risk_level"] == "High"
            or merchant["merchant_country_risk_level"] == "High"
        )
        kyc_issue = int(customer["kyc_status"] != "Verified")
        pep_flag = int(customer["pep_flag"] == 1)

        risk_signal_count = (
            cross_border
            + high_amount
            + unusual_hour
            + high_risk_category
            + high_risk_country
            + kyc_issue
            + pep_flag
        )

        suspicious_label = int(
            risk_signal_count >= 3
            or (high_amount and high_risk_category)
            or (pep_flag and cross_border)
        )

        rows.append(
            {
                "transaction_id": f"TXN{i:08d}",
                "transaction_timestamp": timestamp.isoformat(timespec="seconds"),
                "customer_id": customer_id,
                "account_id": account_id,
                "merchant_id": merchant_id,
                "merchant_category": merchant["merchant_category"],
                "customer_country": customer["country"],
                "merchant_country": merchant["merchant_country"],
                "amount": amount,
                "currency": random.choices(CURRENCIES, weights=[0.82, 0.10, 0.08], k=1)[0],
                "channel": random.choice(CHANNELS),
                "transaction_type": random.choices(
                    ["Purchase", "Cash Withdrawal", "Transfer", "Refund"],
                    weights=[0.72, 0.10, 0.15, 0.03],
                    k=1,
                )[0],
                "status": random.choices(
                    ["Completed", "Pending", "Failed", "Reversed"],
                    weights=[0.91, 0.04, 0.03, 0.02],
                    k=1,
                )[0],
                "cross_border_flag": cross_border,
                "high_amount_flag": high_amount,
                "unusual_hour_flag": unusual_hour,
                "high_risk_category_flag": high_risk_category,
                "high_risk_country_flag": high_risk_country,
                "kyc_issue_flag": kyc_issue,
                "pep_flag": pep_flag,
                "suspicious_label": suspicious_label,
            }
        )

    return pd.DataFrame(rows)


def generate_account_transfers(
    accounts: pd.DataFrame,
    n_transfers: int = 2500,
) -> pd.DataFrame:
    rows = []
    account_ids = accounts["account_id"].tolist()

    for i in range(1, n_transfers + 1):
        source_account = random.choice(account_ids)
        destination_account = random.choice(account_ids)

        while destination_account == source_account:
            destination_account = random.choice(account_ids)

        amount = round(float(np.random.lognormal(mean=4.1, sigma=1.1)), 2)

        if random.random() < 0.025:
            amount = round(float(np.random.lognormal(mean=8.2, sigma=0.5)), 2)

        rows.append(
            {
                "transfer_id": f"TRF{i:08d}",
                "transfer_timestamp": random_date_within(180).isoformat(timespec="seconds"),
                "source_account_id": source_account,
                "destination_account_id": destination_account,
                "amount": amount,
                "currency": random.choices(CURRENCIES, weights=[0.84, 0.08, 0.08], k=1)[0],
                "transfer_purpose": random.choice(
                    [
                        "Invoice Payment",
                        "Personal Transfer",
                        "Supplier Payment",
                        "Loan Repayment",
                        "Unknown",
                    ]
                ),
                "channel": random.choice(
                    ["Mobile Banking", "Branch", "API", "Online Banking"]
                ),
            }
        )

    return pd.DataFrame(rows)


def generate_watchlist(customers: pd.DataFrame, merchants: pd.DataFrame) -> pd.DataFrame:
    watchlisted_customers = customers.sample(12, random_state=SEED)
    watchlisted_merchants = merchants.sample(8, random_state=SEED)

    rows = []

    for _, row in watchlisted_customers.iterrows():
        rows.append(
            {
                "watchlist_id": f"WL-C-{row['customer_id']}",
                "entity_id": row["customer_id"],
                "entity_name": row["full_name"],
                "entity_type": "Customer",
                "watchlist_type": random.choice(
                    ["Dummy Sanctions", "Dummy PEP", "Internal High Risk"]
                ),
                "risk_reason": random.choice(
                    [
                        "Name appears on dummy watchlist",
                        "Politically exposed dummy profile",
                        "Internal high-risk dummy case",
                    ]
                ),
            }
        )

    for _, row in watchlisted_merchants.iterrows():
        rows.append(
            {
                "watchlist_id": f"WL-M-{row['merchant_id']}",
                "entity_id": row["merchant_id"],
                "entity_name": row["merchant_name"],
                "entity_type": "Merchant",
                "watchlist_type": random.choice(
                    ["Dummy Sanctions", "Internal High Risk"]
                ),
                "risk_reason": random.choice(
                    [
                        "Merchant appears on dummy watchlist",
                        "Merchant category under dummy review",
                    ]
                ),
            }
        )

    return pd.DataFrame(rows)


def generate_reconciliation_files(
    transactions: pd.DataFrame,
    n_recon_records: int = 3000,
):
    recon_base = transactions.sample(n_recon_records, random_state=SEED).copy()

    file_a = pd.DataFrame(
        {
            "source_system": "PaymentProcessorA",
            "recon_reference": "REC-A-" + recon_base["transaction_id"],
            "transaction_id": recon_base["transaction_id"],
            "account_id": recon_base["account_id"],
            "booking_date": pd.to_datetime(
                recon_base["transaction_timestamp"]
            ).dt.date.astype(str),
            "amount": recon_base["amount"],
            "currency": recon_base["currency"],
            "status": recon_base["status"],
        }
    ).reset_index(drop=True)

    file_b = file_a.copy()
    file_b["source_system"] = "CoreBankingB"
    file_b["recon_reference"] = file_b["recon_reference"].str.replace(
        "REC-A-",
        "REC-B-",
        regex=False,
    )

    all_indices = list(file_b.index)
    random.shuffle(all_indices)

    amount_mismatch_idx = all_indices[:90]
    date_mismatch_idx = all_indices[90:150]
    missing_in_b_idx = all_indices[150:220]
    duplicate_idx = all_indices[220:250]

    file_b.loc[amount_mismatch_idx, "amount"] = (
        file_b.loc[amount_mismatch_idx, "amount"]
        + np.random.choice(
            [1.50, 2.75, 5.00, 10.00, 25.00],
            size=len(amount_mismatch_idx),
        )
    )

    file_b.loc[date_mismatch_idx, "booking_date"] = (
        pd.to_datetime(file_b.loc[date_mismatch_idx, "booking_date"])
        + pd.to_timedelta(1, unit="D")
    ).dt.date.astype(str)

    duplicates = file_b.loc[duplicate_idx].copy()
    duplicates["recon_reference"] = duplicates["recon_reference"] + "-DUP"

    file_b = file_b.drop(index=missing_in_b_idx)
    file_b = pd.concat([file_b, duplicates], ignore_index=True)

    extra_unmatched = file_a.sample(30, random_state=SEED + 1).copy()
    extra_unmatched["source_system"] = "CoreBankingB"
    extra_unmatched["recon_reference"] = "REC-B-EXTRA-" + extra_unmatched["transaction_id"]
    extra_unmatched["transaction_id"] = "EXTRA-" + extra_unmatched["transaction_id"]

    file_b = pd.concat([file_b, extra_unmatched], ignore_index=True)

    return file_a, file_b


def save_dataset(df: pd.DataFrame, filename: str) -> None:
    path = OUTPUT_DIR / filename
    df.to_csv(path, index=False)
    print(f"Saved {path} with {len(df):,} rows")


def main() -> None:
    customers = generate_customers()
    merchants = generate_merchants()
    accounts = generate_accounts(customers)
    transactions = generate_transactions(customers, merchants, accounts)
    transfers = generate_account_transfers(accounts)
    watchlist = generate_watchlist(customers, merchants)
    recon_a, recon_b = generate_reconciliation_files(transactions)

    save_dataset(customers, "customers.csv")
    save_dataset(merchants, "merchants.csv")
    save_dataset(accounts, "accounts.csv")
    save_dataset(transactions, "transactions.csv")
    save_dataset(transfers, "account_transfers.csv")
    save_dataset(watchlist, "watchlist.csv")
    save_dataset(recon_a, "reconciliation_file_a.csv")
    save_dataset(recon_b, "reconciliation_file_b.csv")

    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "seed": SEED,
        "customers": len(customers),
        "merchants": len(merchants),
        "accounts": len(accounts),
        "transactions": len(transactions),
        "account_transfers": len(transfers),
        "watchlist_entities": len(watchlist),
        "reconciliation_file_a_rows": len(recon_a),
        "reconciliation_file_b_rows": len(recon_b),
        "suspicious_transactions": int(transactions["suspicious_label"].sum()),
    }

    summary_path = OUTPUT_DIR / "generation_summary.json"
    summary_path.write_text(json.dumps(summary, indent=4))
    print(f"Saved {summary_path}")


if __name__ == "__main__":
    main()