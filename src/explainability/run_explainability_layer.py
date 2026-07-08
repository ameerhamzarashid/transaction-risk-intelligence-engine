from pathlib import Path
import json
from datetime import datetime

import duckdb
import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]

DB_PATH = BASE_DIR / "data" / "processed" / "transaction_risk.duckdb"
REPORTS_DIR = BASE_DIR / "reports"

REPORTS_DIR.mkdir(parents=True, exist_ok=True)


RULE_REASON_TRANSLATIONS = {
    "WATCHLIST_MATCH": "the customer or merchant matched the dummy watchlist",
    "PEP_CUSTOMER": "the customer has a PEP-related risk flag",
    "KYC_ISSUE": "the customer has a KYC issue",
    "HIGH_RISK_COUNTRY": "the transaction involves a high-risk country",
    "HIGH_RISK_MERCHANT_CATEGORY": "the merchant category is considered high risk",
    "HIGH_AMOUNT_TRANSACTION": "the transaction amount is high",
    "VERY_HIGH_AMOUNT": "the transaction amount is very high",
    "EXTREME_AMOUNT": "the transaction amount is extremely high",
    "CROSS_BORDER_TRANSACTION": "the transaction is cross-border",
    "UNUSUAL_HOUR_ACTIVITY": "the transaction occurred during an unusual hour",
    "SENSITIVE_MERCHANT_CATEGORY": "the merchant category is sensitive",
    "ELEVATED_MERCHANT_CATEGORY": "the merchant category has elevated monitoring risk",
    "CHANNEL_MONITORING_FLAG": "the channel requires closer monitoring",
    "NON_STANDARD_TRANSACTION_STATUS": "the transaction status is failed or reversed",
    "HIGH_AMOUNT_CROSS_BORDER_COMBINATION": "the transaction combines high value and cross-border activity",
    "WATCHLIST_CROSS_BORDER_COMBINATION": "the transaction combines watchlist exposure and cross-border activity",
    "PEP_HIGH_AMOUNT_COMBINATION": "the transaction combines PEP exposure and high value",
    "NO_MAJOR_RULE_TRIGGERED": "no major rule-based trigger was identified",
}

ML_REASON_TRANSLATIONS = {
    "UNUSUALLY_HIGH_AMOUNT": "the amount is unusually high compared with the wider transaction population",
    "UNUSUAL_TRANSACTION_HOUR": "the transaction time pattern is unusual",
    "CROSS_BORDER_PATTERN": "the transaction forms part of a cross-border pattern",
    "HIGH_RISK_MERCHANT_CATEGORY_PATTERN": "the merchant category contributes to the anomaly pattern",
    "WATCHLIST_LINKED_PATTERN": "watchlist linkage contributes to the anomaly pattern",
    "KYC_RISK_PATTERN": "KYC risk contributes to the anomaly pattern",
    "TOP_1_PERCENT_ANOMALY_SCORE": "the transaction is in the top 1 percent of anomaly scores",
    "TOP_5_PERCENT_ANOMALY_SCORE": "the transaction is in the top 5 percent of anomaly scores",
    "TOP_10_PERCENT_ANOMALY_SCORE": "the transaction is in the top 10 percent of anomaly scores",
    "STATISTICAL_PATTERN_ANOMALY": "the transaction has an unusual statistical pattern",
}


def check_database_exists() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"DuckDB database not found at {DB_PATH}. "
            "Run Stage 2 first: python src\\database\\build_duckdb_database.py"
        )


def table_exists(con: duckdb.DuckDBPyConnection, table_name: str) -> bool:
    result = con.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_name = ?
        """,
        [table_name],
    ).fetchone()[0]

    return result > 0


def load_scored_transactions(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    if table_exists(con, "ml_transaction_anomaly_scores"):
        base_table = "ml_transaction_anomaly_scores"
        print("Loading scored transactions from ml_transaction_anomaly_scores")
    elif table_exists(con, "transaction_risk_scores"):
        base_table = "transaction_risk_scores"
        print("Loading scored transactions from transaction_risk_scores")
    else:
        raise RuntimeError(
            "No scored transaction table found. Run Stage 5 and Stage 6 first."
        )

    if table_exists(con, "reconciliation_breaks"):
        query = f"""
            SELECT
                s.*,
                rb.case_id AS reconciliation_case_id,
                rb.break_type AS reconciliation_break_type,
                rb.severity AS reconciliation_severity,
                rb.case_age_days AS reconciliation_case_age_days,
                rb.recommended_action AS reconciliation_recommended_action
            FROM {base_table} s
            LEFT JOIN reconciliation_breaks rb
                ON s.transaction_id = rb.transaction_id;
        """
    else:
        query = f"""
            SELECT *
            FROM {base_table};
        """

    df = con.execute(query).df()

    print(f"Loaded scored transactions for explainability: {len(df):,} rows")

    return df


def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    defaults = {
        "rule_based_risk_score": 0,
        "risk_band": "Low",
        "alert_priority": "No Alert",
        "should_create_alert": 0,
        "reason_codes": "NO_MAJOR_RULE_TRIGGERED",
        "reason_count": 0,
        "ml_anomaly_score": 0.0,
        "anomaly_score_percentile": 0.0,
        "ml_anomaly_flag": 0,
        "ml_anomaly_band": "Low",
        "ml_alert_priority": "No Alert",
        "should_create_ml_alert": 0,
        "ml_reason_codes": "STATISTICAL_PATTERN_ANOMALY",
        "combined_risk_signal": "No Alert",
        "reconciliation_case_id": "",
        "reconciliation_break_type": "",
        "reconciliation_severity": "",
        "reconciliation_case_age_days": 0,
        "reconciliation_recommended_action": "",
        "amount": 0,
        "currency": "Unknown",
        "channel": "Unknown",
        "merchant_category": "Unknown",
        "merchant_name": "Unknown",
        "full_name": "Unknown",
        "customer_id": "Unknown",
        "transaction_id": "Unknown",
        "transaction_timestamp": "",
        "watchlist_match_flag": 0,
        "kyc_issue_flag": 0,
        "pep_flag": 0,
        "cross_border_flag": 0,
        "high_amount_flag": 0,
        "unusual_hour_flag": 0,
        "high_risk_category_flag": 0,
        "high_risk_country_flag": 0,
        "suspicious_label": 0,
    }

    for column, default_value in defaults.items():
        if column not in df.columns:
            df[column] = default_value

    numeric_columns = [
        "rule_based_risk_score",
        "should_create_alert",
        "ml_anomaly_score",
        "anomaly_score_percentile",
        "ml_anomaly_flag",
        "should_create_ml_alert",
        "reconciliation_case_age_days",
        "amount",
        "watchlist_match_flag",
        "kyc_issue_flag",
        "pep_flag",
        "cross_border_flag",
        "high_amount_flag",
        "unusual_hour_flag",
        "high_risk_category_flag",
        "high_risk_country_flag",
        "suspicious_label",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)

    text_columns = [
        "risk_band",
        "alert_priority",
        "reason_codes",
        "ml_anomaly_band",
        "ml_alert_priority",
        "ml_reason_codes",
        "combined_risk_signal",
        "reconciliation_case_id",
        "reconciliation_break_type",
        "reconciliation_severity",
        "reconciliation_recommended_action",
        "currency",
        "channel",
        "merchant_category",
        "merchant_name",
        "full_name",
        "customer_id",
        "transaction_id",
        "transaction_timestamp",
    ]

    for column in text_columns:
        df[column] = df[column].fillna("").astype(str)

    return df


def split_reason_codes(reason_string: str) -> list[str]:
    if not reason_string:
        return []

    return [
        reason.strip()
        for reason in str(reason_string).split(";")
        if reason.strip()
    ]


def translate_reasons(reason_codes: list[str], mapping: dict[str, str]) -> list[str]:
    translated = []

    for reason in reason_codes:
        translated.append(mapping.get(reason, reason.lower().replace("_", " ")))

    return translated


def join_human_reasons(reasons: list[str], max_reasons: int = 5) -> str:
    if not reasons:
        return "no major explainability driver was identified"

    selected = reasons[:max_reasons]

    if len(selected) == 1:
        return selected[0]

    return ", ".join(selected[:-1]) + " and " + selected[-1]


def assign_combined_explanation_score(row: pd.Series) -> float:
    rule_score = float(row["rule_based_risk_score"])
    anomaly_percentile = float(row["anomaly_score_percentile"])

    reconciliation_boost = 0

    if row["reconciliation_severity"] == "High":
        reconciliation_boost = 12
    elif row["reconciliation_severity"] == "Medium":
        reconciliation_boost = 7
    elif row["reconciliation_severity"] == "Low":
        reconciliation_boost = 3

    watchlist_boost = 8 if int(row["watchlist_match_flag"]) == 1 else 0
    suspicious_label_boost = 5 if int(row["suspicious_label"]) == 1 else 0

    combined_score = (
        rule_score * 0.45
        + anomaly_percentile * 0.40
        + reconciliation_boost
        + watchlist_boost
        + suspicious_label_boost
    )

    return round(float(min(combined_score, 100)), 2)


def assign_explanation_priority(combined_score: float) -> str:
    if combined_score >= 80:
        return "P1"
    if combined_score >= 60:
        return "P2"
    if combined_score >= 35:
        return "P3"
    return "No Alert"


def assign_review_queue(priority: str) -> str:
    if priority == "P1":
        return "Enhanced Financial Crime Review"
    if priority == "P2":
        return "Financial Crime Analyst Review"
    if priority == "P3":
        return "Operations Risk Review"
    return "No Immediate Review"


def identify_main_trigger(row: pd.Series) -> str:
    rule_alert = int(row["should_create_alert"]) == 1
    ml_alert = int(row["should_create_ml_alert"]) == 1
    reconciliation_alert = bool(row["reconciliation_case_id"])

    if rule_alert and ml_alert and reconciliation_alert:
        return "Rule + ML + Reconciliation"
    if rule_alert and ml_alert:
        return "Rule + ML"
    if rule_alert and reconciliation_alert:
        return "Rule + Reconciliation"
    if ml_alert and reconciliation_alert:
        return "ML + Reconciliation"
    if rule_alert:
        return "Rule Only"
    if ml_alert:
        return "ML Only"
    if reconciliation_alert:
        return "Reconciliation Only"

    return "No Alert"


def build_evidence_summary(row: pd.Series) -> str:
    evidence = [
        f"amount {row['amount']:.2f} {row['currency']}",
        f"merchant category {row['merchant_category']}",
        f"channel {row['channel']}",
        f"rule score {row['rule_based_risk_score']}",
        f"ML anomaly percentile {row['anomaly_score_percentile']}",
    ]

    if row["reconciliation_case_id"]:
        evidence.append(
            f"reconciliation break {row['reconciliation_break_type']} with {row['reconciliation_severity']} severity"
        )

    return "; ".join(evidence)


def build_recommended_action(row: pd.Series, priority: str, main_trigger: str) -> str:
    if priority == "P1":
        action = (
            "Immediate investigation required. Review customer profile, transaction context, "
            "watchlist/KYC indicators, anomaly pattern and reconciliation evidence."
        )
    elif priority == "P2":
        action = (
            "Prioritised analyst review required. Validate rule triggers, compare against ML anomaly pattern "
            "and check source-system consistency."
        )
    elif priority == "P3":
        action = (
            "Operational review recommended. Check reason codes, monitor repeat behaviour and close if evidence is benign."
        )
    else:
        action = "No immediate action required. Retain for monitoring and reporting."

    if "Reconciliation" in main_trigger and row["reconciliation_recommended_action"]:
        action = action + " Reconciliation action: " + row["reconciliation_recommended_action"]

    return action


def build_explanation_text(row: pd.Series, priority: str, main_trigger: str) -> str:
    rule_codes = split_reason_codes(row["reason_codes"])
    ml_codes = split_reason_codes(row["ml_reason_codes"])

    rule_reasons = translate_reasons(rule_codes, RULE_REASON_TRANSLATIONS)
    ml_reasons = translate_reasons(ml_codes, ML_REASON_TRANSLATIONS)

    rule_text = join_human_reasons(rule_reasons)
    ml_text = join_human_reasons(ml_reasons)

    reconciliation_text = ""

    if row["reconciliation_case_id"]:
        reconciliation_text = (
            f" It also has a reconciliation break classified as "
            f"{row['reconciliation_break_type']} with {row['reconciliation_severity']} severity."
        )

    explanation = (
        f"Transaction {row['transaction_id']} was assigned priority {priority}. "
        f"The main trigger is {main_trigger}. "
        f"The rule-based explanation is that {rule_text}. "
        f"The ML explanation is that {ml_text}."
        f"{reconciliation_text}"
    )

    return explanation


def create_alert_explanations(df: pd.DataFrame) -> pd.DataFrame:
    df = ensure_columns(df)

    df["combined_explanation_score"] = df.apply(
        assign_combined_explanation_score,
        axis=1,
    )

    df["explanation_priority"] = df["combined_explanation_score"].apply(
        assign_explanation_priority
    )

    df["main_trigger"] = df.apply(identify_main_trigger, axis=1)

    explainable_alerts = df[
        (df["explanation_priority"] != "No Alert")
        | (df["main_trigger"] != "No Alert")
        | (df["suspicious_label"] == 1)
    ].copy()

    explainable_alerts = explainable_alerts.sort_values(
        by=["combined_explanation_score", "anomaly_score_percentile", "rule_based_risk_score", "amount"],
        ascending=[False, False, False, False],
    ).reset_index(drop=True)

    explainable_alerts.insert(
        0,
        "explanation_id",
        [f"EXP-{i + 1:06d}" for i in range(len(explainable_alerts))],
    )

    explainable_alerts["review_queue"] = explainable_alerts["explanation_priority"].apply(
        assign_review_queue
    )

    explainable_alerts["evidence_summary"] = explainable_alerts.apply(
        build_evidence_summary,
        axis=1,
    )

    explainable_alerts["recommended_investigation_action"] = explainable_alerts.apply(
        lambda row: build_recommended_action(
            row,
            row["explanation_priority"],
            row["main_trigger"],
        ),
        axis=1,
    )

    explainable_alerts["plain_english_explanation"] = explainable_alerts.apply(
        lambda row: build_explanation_text(
            row,
            row["explanation_priority"],
            row["main_trigger"],
        ),
        axis=1,
    )

    explainable_alerts["generated_at"] = datetime.now().isoformat(timespec="seconds")

    selected_columns = [
        "explanation_id",
        "explanation_priority",
        "review_queue",
        "main_trigger",
        "combined_explanation_score",
        "transaction_id",
        "transaction_timestamp",
        "customer_id",
        "full_name",
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
        "ml_anomaly_score",
        "anomaly_score_percentile",
        "ml_anomaly_band",
        "ml_reason_codes",
        "combined_risk_signal",
        "reconciliation_case_id",
        "reconciliation_break_type",
        "reconciliation_severity",
        "reconciliation_case_age_days",
        "evidence_summary",
        "plain_english_explanation",
        "recommended_investigation_action",
        "suspicious_label",
        "generated_at",
    ]

    existing_columns = [
        column for column in selected_columns if column in explainable_alerts.columns
    ]

    return explainable_alerts[existing_columns]


def create_reason_summary(alert_explanations: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for _, row in alert_explanations.iterrows():
        for reason_code in split_reason_codes(row.get("reason_codes", "")):
            rows.append(
                {
                    "reason_source": "Rule",
                    "reason_code": reason_code,
                    "human_reason": RULE_REASON_TRANSLATIONS.get(
                        reason_code,
                        reason_code.lower().replace("_", " "),
                    ),
                    "transaction_id": row["transaction_id"],
                    "explanation_priority": row["explanation_priority"],
                    "combined_explanation_score": row["combined_explanation_score"],
                }
            )

        for reason_code in split_reason_codes(row.get("ml_reason_codes", "")):
            rows.append(
                {
                    "reason_source": "ML",
                    "reason_code": reason_code,
                    "human_reason": ML_REASON_TRANSLATIONS.get(
                        reason_code,
                        reason_code.lower().replace("_", " "),
                    ),
                    "transaction_id": row["transaction_id"],
                    "explanation_priority": row["explanation_priority"],
                    "combined_explanation_score": row["combined_explanation_score"],
                }
            )

        if row.get("reconciliation_break_type", ""):
            rows.append(
                {
                    "reason_source": "Reconciliation",
                    "reason_code": row["reconciliation_break_type"],
                    "human_reason": "the transaction has a reconciliation break requiring operational review",
                    "transaction_id": row["transaction_id"],
                    "explanation_priority": row["explanation_priority"],
                    "combined_explanation_score": row["combined_explanation_score"],
                }
            )

    if not rows:
        return pd.DataFrame(
            columns=[
                "reason_source",
                "reason_code",
                "human_reason",
                "transaction_count",
                "average_combined_explanation_score",
                "p1_count",
                "p2_count",
                "p3_count",
            ]
        )

    reason_events = pd.DataFrame(rows)

    reason_summary = (
        reason_events.groupby(["reason_source", "reason_code", "human_reason"])
        .agg(
            transaction_count=("transaction_id", "nunique"),
            average_combined_explanation_score=("combined_explanation_score", "mean"),
            p1_count=("explanation_priority", lambda x: int((x == "P1").sum())),
            p2_count=("explanation_priority", lambda x: int((x == "P2").sum())),
            p3_count=("explanation_priority", lambda x: int((x == "P3").sum())),
        )
        .reset_index()
    )

    reason_summary["average_combined_explanation_score"] = reason_summary[
        "average_combined_explanation_score"
    ].round(2)

    reason_summary = reason_summary.sort_values(
        by=["transaction_count", "average_combined_explanation_score"],
        ascending=[False, False],
    ).reset_index(drop=True)

    return reason_summary


def create_customer_explanation_summary(alert_explanations: pd.DataFrame) -> pd.DataFrame:
    if alert_explanations.empty:
        return pd.DataFrame()

    customer_summary = (
        alert_explanations.groupby("customer_id")
        .agg(
            full_name=("full_name", "first"),
            alert_explanation_count=("explanation_id", "count"),
            p1_alerts=("explanation_priority", lambda x: int((x == "P1").sum())),
            p2_alerts=("explanation_priority", lambda x: int((x == "P2").sum())),
            p3_alerts=("explanation_priority", lambda x: int((x == "P3").sum())),
            max_combined_explanation_score=("combined_explanation_score", "max"),
            average_combined_explanation_score=("combined_explanation_score", "mean"),
            max_rule_based_risk_score=("rule_based_risk_score", "max"),
            max_anomaly_score_percentile=("anomaly_score_percentile", "max"),
            total_alert_amount=("amount", "sum"),
            suspicious_label_count=("suspicious_label", "sum"),
        )
        .reset_index()
    )

    customer_summary["average_combined_explanation_score"] = customer_summary[
        "average_combined_explanation_score"
    ].round(2)

    customer_summary["total_alert_amount"] = customer_summary[
        "total_alert_amount"
    ].round(2)

    customer_summary["customer_explanation_priority"] = np.where(
        customer_summary["p1_alerts"] > 0,
        "P1",
        np.where(
            customer_summary["p2_alerts"] > 0,
            "P2",
            np.where(customer_summary["p3_alerts"] > 0, "P3", "No Review"),
        ),
    )

    customer_summary = customer_summary.sort_values(
        by=[
            "customer_explanation_priority",
            "max_combined_explanation_score",
            "alert_explanation_count",
        ],
        ascending=[True, False, False],
    ).reset_index(drop=True)

    return customer_summary


def save_to_duckdb(
    con: duckdb.DuckDBPyConnection,
    alert_explanations: pd.DataFrame,
    reason_summary: pd.DataFrame,
    customer_summary: pd.DataFrame,
) -> None:
    con.register("alert_explanations_df", alert_explanations)
    con.register("explanation_reason_summary_df", reason_summary)
    con.register("customer_explanation_summary_df", customer_summary)

    con.execute(
        """
        CREATE OR REPLACE TABLE alert_explanations AS
        SELECT *
        FROM alert_explanations_df;
        """
    )

    con.execute(
        """
        CREATE OR REPLACE TABLE explanation_reason_summary AS
        SELECT *
        FROM explanation_reason_summary_df;
        """
    )

    con.execute(
        """
        CREATE OR REPLACE TABLE customer_explanation_summary AS
        SELECT *
        FROM customer_explanation_summary_df;
        """
    )

    con.execute(
        """
        CREATE OR REPLACE VIEW vw_explainability_priority_summary AS
        SELECT
            explanation_priority,
            review_queue,
            main_trigger,
            COUNT(*) AS alert_count,
            ROUND(AVG(combined_explanation_score), 2) AS average_combined_score,
            ROUND(SUM(amount), 2) AS total_amount
        FROM alert_explanations
        GROUP BY explanation_priority, review_queue, main_trigger
        ORDER BY average_combined_score DESC;
        """
    )

    con.execute(
        """
        CREATE OR REPLACE VIEW vw_top_explanation_reasons AS
        SELECT
            reason_source,
            reason_code,
            human_reason,
            transaction_count,
            average_combined_explanation_score,
            p1_count,
            p2_count,
            p3_count
        FROM explanation_reason_summary
        ORDER BY transaction_count DESC, average_combined_explanation_score DESC;
        """
    )

    print("Saved explainability tables and views to DuckDB")


def save_reports(
    alert_explanations: pd.DataFrame,
    reason_summary: pd.DataFrame,
    customer_summary: pd.DataFrame,
) -> None:
    alert_path = REPORTS_DIR / "stage7_alert_explanations.csv"
    reason_path = REPORTS_DIR / "stage7_explanation_reason_summary.csv"
    customer_path = REPORTS_DIR / "stage7_customer_explanation_summary.csv"
    summary_path = REPORTS_DIR / "stage7_explainability_summary.json"

    alert_explanations.to_csv(alert_path, index=False)
    reason_summary.to_csv(reason_path, index=False)
    customer_summary.to_csv(customer_path, index=False)

    summary = {
        "run_timestamp": datetime.now().isoformat(timespec="seconds"),
        "alert_explanations_created": int(len(alert_explanations)),
        "unique_customers_with_explanations": int(
            alert_explanations["customer_id"].nunique()
            if not alert_explanations.empty
            else 0
        ),
        "p1_explanations": int(
            (alert_explanations["explanation_priority"] == "P1").sum()
            if not alert_explanations.empty
            else 0
        ),
        "p2_explanations": int(
            (alert_explanations["explanation_priority"] == "P2").sum()
            if not alert_explanations.empty
            else 0
        ),
        "p3_explanations": int(
            (alert_explanations["explanation_priority"] == "P3").sum()
            if not alert_explanations.empty
            else 0
        ),
        "rule_ml_reconciliation_alerts": int(
            (alert_explanations["main_trigger"] == "Rule + ML + Reconciliation").sum()
            if not alert_explanations.empty
            else 0
        ),
        "rule_ml_alerts": int(
            (alert_explanations["main_trigger"] == "Rule + ML").sum()
            if not alert_explanations.empty
            else 0
        ),
        "ml_only_alerts": int(
            (alert_explanations["main_trigger"] == "ML Only").sum()
            if not alert_explanations.empty
            else 0
        ),
        "rule_only_alerts": int(
            (alert_explanations["main_trigger"] == "Rule Only").sum()
            if not alert_explanations.empty
            else 0
        ),
        "reason_codes_summarised": int(len(reason_summary)),
    }

    summary_path.write_text(json.dumps(summary, indent=4))

    print(f"Saved {alert_path}")
    print(f"Saved {reason_path}")
    print(f"Saved {customer_path}")
    print(f"Saved {summary_path}")


def print_console_summary(
    alert_explanations: pd.DataFrame,
    reason_summary: pd.DataFrame,
    customer_summary: pd.DataFrame,
) -> None:
    print("\nExplainability Priority Summary")
    print("-------------------------------")
    print(alert_explanations["explanation_priority"].value_counts().to_string())

    print("\nMain Trigger Summary")
    print("--------------------")
    print(alert_explanations["main_trigger"].value_counts().to_string())

    print("\nTop 10 Explanation Reasons")
    print("--------------------------")
    print(
        reason_summary[
            [
                "reason_source",
                "reason_code",
                "transaction_count",
                "average_combined_explanation_score",
            ]
        ]
        .head(10)
        .to_string(index=False)
    )

    print("\nTop 5 Plain-English Explanations")
    print("--------------------------------")
    print(
        alert_explanations[
            [
                "explanation_id",
                "transaction_id",
                "explanation_priority",
                "combined_explanation_score",
                "plain_english_explanation",
            ]
        ]
        .head(5)
        .to_string(index=False)
    )

    print("\nTop 10 Customer Explanation Summary")
    print("-----------------------------------")
    print(
        customer_summary[
            [
                "customer_id",
                "full_name",
                "alert_explanation_count",
                "customer_explanation_priority",
                "max_combined_explanation_score",
            ]
        ]
        .head(10)
        .to_string(index=False)
    )


def main() -> None:
    check_database_exists()

    print(f"Running Stage 7 explainability layer against: {DB_PATH}")

    with duckdb.connect(str(DB_PATH)) as con:
        scored_transactions = load_scored_transactions(con)

        alert_explanations = create_alert_explanations(scored_transactions)
        reason_summary = create_reason_summary(alert_explanations)
        customer_summary = create_customer_explanation_summary(alert_explanations)

        save_to_duckdb(con, alert_explanations, reason_summary, customer_summary)
        save_reports(alert_explanations, reason_summary, customer_summary)
        print_console_summary(alert_explanations, reason_summary, customer_summary)

    print("\nStage 7 explainability layer completed successfully")


if __name__ == "__main__":
    main()