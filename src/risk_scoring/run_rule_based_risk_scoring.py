from pathlib import Path
import json
from datetime import datetime

import duckdb
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]

DB_PATH = BASE_DIR / "data" / "processed" / "transaction_risk.duckdb"
REPORTS_DIR = BASE_DIR / "reports"

REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def check_database_exists() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"DuckDB database not found at {DB_PATH}. "
            "Run Stage 2 first: python src\\database\\build_duckdb_database.py"
        )


def load_enriched_transactions(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    df = con.execute(
        """
        SELECT *
        FROM vw_transaction_enriched;
        """
    ).df()

    print(f"Loaded enriched transactions: {len(df):,} rows")

    return df


def yes(value) -> bool:
    return int(value) == 1 if pd.notna(value) else False


def add_reason(reasons: list[str], reason_code: str) -> None:
    if reason_code not in reasons:
        reasons.append(reason_code)


def calculate_transaction_score(row: pd.Series) -> pd.Series:
    score = 0
    reasons = []

    amount = float(row["amount"]) if pd.notna(row["amount"]) else 0
    merchant_category = str(row["merchant_category"])
    channel = str(row["channel"])
    status = str(row["status"])

    if yes(row["watchlist_match_flag"]):
        score += 35
        add_reason(reasons, "WATCHLIST_MATCH")

    if yes(row["pep_flag"]) or yes(row["customer_master_pep_flag"]):
        score += 25
        add_reason(reasons, "PEP_CUSTOMER")

    if yes(row["kyc_issue_flag"]):
        score += 20
        add_reason(reasons, "KYC_ISSUE")

    if yes(row["high_risk_country_flag"]):
        score += 18
        add_reason(reasons, "HIGH_RISK_COUNTRY")

    if yes(row["high_risk_category_flag"]):
        score += 18
        add_reason(reasons, "HIGH_RISK_MERCHANT_CATEGORY")

    if yes(row["high_amount_flag"]):
        score += 15
        add_reason(reasons, "HIGH_AMOUNT_TRANSACTION")

    if amount >= 5000:
        score += 15
        add_reason(reasons, "VERY_HIGH_AMOUNT")

    if amount >= 10000:
        score += 10
        add_reason(reasons, "EXTREME_AMOUNT")

    if yes(row["cross_border_flag"]):
        score += 10
        add_reason(reasons, "CROSS_BORDER_TRANSACTION")

    if yes(row["unusual_hour_flag"]):
        score += 10
        add_reason(reasons, "UNUSUAL_HOUR_ACTIVITY")

    if merchant_category in ["Crypto Exchange", "Gambling", "Money Transfer"]:
        score += 10
        add_reason(reasons, "SENSITIVE_MERCHANT_CATEGORY")

    if merchant_category in ["Cash Withdrawal", "Luxury Goods"]:
        score += 6
        add_reason(reasons, "ELEVATED_MERCHANT_CATEGORY")

    if channel in ["ATM", "API"]:
        score += 5
        add_reason(reasons, "CHANNEL_MONITORING_FLAG")

    if status in ["Failed", "Reversed"]:
        score += 5
        add_reason(reasons, "NON_STANDARD_TRANSACTION_STATUS")

    if yes(row["cross_border_flag"]) and yes(row["high_amount_flag"]):
        score += 8
        add_reason(reasons, "HIGH_AMOUNT_CROSS_BORDER_COMBINATION")

    if yes(row["watchlist_match_flag"]) and yes(row["cross_border_flag"]):
        score += 10
        add_reason(reasons, "WATCHLIST_CROSS_BORDER_COMBINATION")

    if yes(row["pep_flag"]) and yes(row["high_amount_flag"]):
        score += 10
        add_reason(reasons, "PEP_HIGH_AMOUNT_COMBINATION")

    score = min(score, 100)

    if score >= 75:
        risk_band = "Critical"
    elif score >= 55:
        risk_band = "High"
    elif score >= 30:
        risk_band = "Medium"
    else:
        risk_band = "Low"

    if score >= 75:
        alert_priority = "P1"
    elif score >= 55:
        alert_priority = "P2"
    elif score >= 30:
        alert_priority = "P3"
    else:
        alert_priority = "No Alert"

    should_create_alert = int(score >= 30)

    if len(reasons) == 0:
        reasons.append("NO_MAJOR_RULE_TRIGGERED")

    return pd.Series(
        {
            "rule_based_risk_score": score,
            "risk_band": risk_band,
            "alert_priority": alert_priority,
            "should_create_alert": should_create_alert,
            "reason_codes": "; ".join(reasons),
            "reason_count": len(reasons),
        }
    )


def score_transactions(transactions: pd.DataFrame) -> pd.DataFrame:
    score_columns = transactions.apply(calculate_transaction_score, axis=1)

    scored = pd.concat([transactions, score_columns], axis=1)

    scored["scored_at"] = datetime.now().isoformat(timespec="seconds")

    scored = scored.sort_values(
        by=["rule_based_risk_score", "amount"],
        ascending=[False, False],
    ).reset_index(drop=True)

    return scored


def create_customer_risk_scores(scored_transactions: pd.DataFrame) -> pd.DataFrame:
    customer_scores = (
        scored_transactions.groupby("customer_id")
        .agg(
            full_name=("full_name", "first"),
            customer_segment=("customer_segment", "first"),
            customer_country=("customer_master_country", "first"),
            country_risk_level=("country_risk_level", "first"),
            kyc_status=("kyc_status", "first"),
            pep_flag=("customer_master_pep_flag", "max"),
            transaction_count=("transaction_id", "count"),
            total_transaction_amount=("amount", "sum"),
            average_transaction_amount=("amount", "mean"),
            max_transaction_amount=("amount", "max"),
            average_transaction_risk_score=("rule_based_risk_score", "mean"),
            max_transaction_risk_score=("rule_based_risk_score", "max"),
            alert_count=("should_create_alert", "sum"),
            critical_transaction_count=(
                "risk_band",
                lambda x: int((x == "Critical").sum()),
            ),
            high_transaction_count=(
                "risk_band",
                lambda x: int((x == "High").sum()),
            ),
            medium_transaction_count=(
                "risk_band",
                lambda x: int((x == "Medium").sum()),
            ),
            watchlist_match_count=("watchlist_match_flag", "sum"),
            suspicious_label_count=("suspicious_label", "sum"),
        )
        .reset_index()
    )

    customer_scores["total_transaction_amount"] = customer_scores[
        "total_transaction_amount"
    ].round(2)

    customer_scores["average_transaction_amount"] = customer_scores[
        "average_transaction_amount"
    ].round(2)

    customer_scores["average_transaction_risk_score"] = customer_scores[
        "average_transaction_risk_score"
    ].round(2)

    customer_scores["customer_rule_based_risk_score"] = (
        customer_scores["max_transaction_risk_score"] * 0.45
        + customer_scores["average_transaction_risk_score"] * 0.25
        + customer_scores["alert_count"].clip(upper=10) * 2.0
        + customer_scores["watchlist_match_count"].clip(upper=5) * 4.0
        + customer_scores["critical_transaction_count"].clip(upper=5) * 3.0
        + customer_scores["high_transaction_count"].clip(upper=5) * 2.0
    )

    customer_scores["customer_rule_based_risk_score"] = customer_scores[
        "customer_rule_based_risk_score"
    ].clip(upper=100).round(2)

    def customer_band(score: float) -> str:
        if score >= 75:
            return "Critical"
        if score >= 55:
            return "High"
        if score >= 30:
            return "Medium"
        return "Low"

    customer_scores["customer_risk_band"] = customer_scores[
        "customer_rule_based_risk_score"
    ].apply(customer_band)

    customer_scores["customer_review_priority"] = customer_scores[
        "customer_risk_band"
    ].map(
        {
            "Critical": "P1",
            "High": "P2",
            "Medium": "P3",
            "Low": "No Review",
        }
    )

    customer_scores = customer_scores.sort_values(
        by=[
            "customer_rule_based_risk_score",
            "alert_count",
            "total_transaction_amount",
        ],
        ascending=[False, False, False],
    ).reset_index(drop=True)

    return customer_scores


def create_transaction_alerts(scored_transactions: pd.DataFrame) -> pd.DataFrame:
    alerts = scored_transactions[scored_transactions["should_create_alert"] == 1].copy()

    alerts = alerts.reset_index(drop=True)

    alerts.insert(
        0,
        "alert_id",
        [f"RISK-ALERT-{i + 1:06d}" for i in range(len(alerts))],
    )

    alerts["alert_status"] = "Open"

    alerts["alert_type"] = "Rule-Based Transaction Risk"

    alerts["alert_owner"] = alerts["risk_band"].map(
        {
            "Critical": "Financial Crime Senior Analyst",
            "High": "Financial Crime Analyst",
            "Medium": "Operations Risk Analyst",
            "Low": "Operations Analyst",
        }
    )

    alerts["recommended_action"] = alerts["risk_band"].map(
        {
            "Critical": "Immediate review required. Check customer profile, watchlist status, transaction context and supporting evidence.",
            "High": "Prioritised review required. Investigate triggered risk rules and customer transaction history.",
            "Medium": "Review when capacity allows. Validate reason codes and monitor for repeat behaviour.",
            "Low": "No immediate action required.",
        }
    )

    selected_columns = [
        "alert_id",
        "alert_status",
        "alert_type",
        "alert_priority",
        "alert_owner",
        "recommended_action",
        "transaction_id",
        "transaction_timestamp",
        "customer_id",
        "full_name",
        "account_id",
        "merchant_id",
        "merchant_name",
        "merchant_category",
        "amount",
        "currency",
        "channel",
        "status",
        "rule_based_risk_score",
        "risk_band",
        "reason_codes",
        "watchlist_match_flag",
        "kyc_issue_flag",
        "pep_flag",
        "cross_border_flag",
        "high_amount_flag",
        "unusual_hour_flag",
        "high_risk_category_flag",
        "high_risk_country_flag",
        "suspicious_label",
        "scored_at",
    ]

    return alerts[selected_columns]


def save_to_duckdb(
    con: duckdb.DuckDBPyConnection,
    scored_transactions: pd.DataFrame,
    customer_scores: pd.DataFrame,
    alerts: pd.DataFrame,
) -> None:
    con.register("transaction_risk_scores_df", scored_transactions)
    con.register("customer_risk_scores_df", customer_scores)
    con.register("transaction_risk_alerts_df", alerts)

    con.execute(
        """
        CREATE OR REPLACE TABLE transaction_risk_scores AS
        SELECT *
        FROM transaction_risk_scores_df;
        """
    )

    con.execute(
        """
        CREATE OR REPLACE TABLE customer_risk_scores AS
        SELECT *
        FROM customer_risk_scores_df;
        """
    )

    con.execute(
        """
        CREATE OR REPLACE TABLE transaction_risk_alerts AS
        SELECT *
        FROM transaction_risk_alerts_df;
        """
    )

    con.execute(
        """
        CREATE OR REPLACE VIEW vw_transaction_risk_summary AS
        SELECT
            risk_band,
            alert_priority,
            COUNT(*) AS transaction_count,
            ROUND(SUM(amount), 2) AS total_amount,
            ROUND(AVG(rule_based_risk_score), 2) AS average_risk_score
        FROM transaction_risk_scores
        GROUP BY risk_band, alert_priority
        ORDER BY average_risk_score DESC;
        """
    )

    con.execute(
        """
        CREATE OR REPLACE VIEW vw_customer_risk_summary AS
        SELECT
            customer_risk_band,
            customer_review_priority,
            COUNT(*) AS customer_count,
            ROUND(AVG(customer_rule_based_risk_score), 2) AS average_customer_score,
            SUM(alert_count) AS total_alerts
        FROM customer_risk_scores
        GROUP BY customer_risk_band, customer_review_priority
        ORDER BY average_customer_score DESC;
        """
    )

    print("Saved risk scoring tables and summary views to DuckDB")


def save_reports(
    scored_transactions: pd.DataFrame,
    customer_scores: pd.DataFrame,
    alerts: pd.DataFrame,
) -> None:
    transaction_scores_path = REPORTS_DIR / "stage5_transaction_risk_scores.csv"
    customer_scores_path = REPORTS_DIR / "stage5_customer_risk_scores.csv"
    alerts_path = REPORTS_DIR / "stage5_transaction_risk_alerts.csv"
    summary_path = REPORTS_DIR / "stage5_risk_scoring_summary.json"

    scored_transactions.to_csv(transaction_scores_path, index=False)
    customer_scores.to_csv(customer_scores_path, index=False)
    alerts.to_csv(alerts_path, index=False)

    summary = {
        "run_timestamp": datetime.now().isoformat(timespec="seconds"),
        "transaction_rows_scored": int(len(scored_transactions)),
        "customer_rows_scored": int(len(customer_scores)),
        "transaction_alerts_created": int(len(alerts)),
        "critical_transactions": int((scored_transactions["risk_band"] == "Critical").sum()),
        "high_risk_transactions": int((scored_transactions["risk_band"] == "High").sum()),
        "medium_risk_transactions": int((scored_transactions["risk_band"] == "Medium").sum()),
        "low_risk_transactions": int((scored_transactions["risk_band"] == "Low").sum()),
        "critical_customers": int((customer_scores["customer_risk_band"] == "Critical").sum()),
        "high_risk_customers": int((customer_scores["customer_risk_band"] == "High").sum()),
        "medium_risk_customers": int((customer_scores["customer_risk_band"] == "Medium").sum()),
        "low_risk_customers": int((customer_scores["customer_risk_band"] == "Low").sum()),
        "average_transaction_risk_score": round(
            float(scored_transactions["rule_based_risk_score"].mean()),
            2,
        ),
        "max_transaction_risk_score": int(
            scored_transactions["rule_based_risk_score"].max()
        ),
    }

    summary_path.write_text(json.dumps(summary, indent=4))

    print(f"Saved {transaction_scores_path}")
    print(f"Saved {customer_scores_path}")
    print(f"Saved {alerts_path}")
    print(f"Saved {summary_path}")


def print_console_summary(
    scored_transactions: pd.DataFrame,
    customer_scores: pd.DataFrame,
    alerts: pd.DataFrame,
) -> None:
    print("\nTransaction Risk Band Summary")
    print("-----------------------------")
    print(scored_transactions["risk_band"].value_counts().to_string())

    print("\nCustomer Risk Band Summary")
    print("--------------------------")
    print(customer_scores["customer_risk_band"].value_counts().to_string())

    print("\nTop 10 Transaction Alerts")
    print("-------------------------")
    print(
        alerts[
            [
                "alert_id",
                "transaction_id",
                "customer_id",
                "amount",
                "risk_band",
                "rule_based_risk_score",
                "reason_codes",
            ]
        ]
        .head(10)
        .to_string(index=False)
    )


def main() -> None:
    check_database_exists()

    print(f"Running Stage 5 rule-based risk scoring against: {DB_PATH}")

    with duckdb.connect(str(DB_PATH)) as con:
        transactions = load_enriched_transactions(con)

        scored_transactions = score_transactions(transactions)
        customer_scores = create_customer_risk_scores(scored_transactions)
        alerts = create_transaction_alerts(scored_transactions)

        save_to_duckdb(con, scored_transactions, customer_scores, alerts)
        save_reports(scored_transactions, customer_scores, alerts)
        print_console_summary(scored_transactions, customer_scores, alerts)

    print("\nStage 5 rule-based risk scoring completed successfully")


if __name__ == "__main__":
    main()