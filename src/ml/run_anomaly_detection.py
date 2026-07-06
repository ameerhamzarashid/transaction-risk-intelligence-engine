from pathlib import Path
import json
from datetime import datetime

import duckdb
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


BASE_DIR = Path(__file__).resolve().parents[2]

DB_PATH = BASE_DIR / "data" / "processed" / "transaction_risk.duckdb"
REPORTS_DIR = BASE_DIR / "reports"

REPORTS_DIR.mkdir(parents=True, exist_ok=True)


NUMERIC_FEATURES = [
    "amount",
    "transaction_hour",
    "transaction_day_of_week",
    "cross_border_flag",
    "high_amount_flag",
    "unusual_hour_flag",
    "high_risk_category_flag",
    "high_risk_country_flag",
    "kyc_issue_flag",
    "pep_flag",
    "watchlist_match_flag",
    "rule_based_risk_score",
    "reason_count",
]

CATEGORICAL_FEATURES = [
    "merchant_category",
    "currency",
    "channel",
    "transaction_type",
    "status",
    "customer_segment",
    "country_risk_level",
    "merchant_country_risk_level",
]


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


def load_transactions(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    if table_exists(con, "transaction_risk_scores"):
        query = """
            SELECT *
            FROM transaction_risk_scores;
        """
        print("Loading transactions from transaction_risk_scores table")
    else:
        query = """
            SELECT *
            FROM vw_transaction_enriched;
        """
        print("Loading transactions from vw_transaction_enriched view")

    df = con.execute(query).df()

    print(f"Loaded transactions for ML anomaly detection: {len(df):,} rows")

    return df


def prepare_ml_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["transaction_timestamp"] = pd.to_datetime(
        df["transaction_timestamp"],
        errors="coerce",
    )

    df["transaction_hour"] = df["transaction_timestamp"].dt.hour
    df["transaction_day_of_week"] = df["transaction_timestamp"].dt.dayofweek

    if "rule_based_risk_score" not in df.columns:
        df["rule_based_risk_score"] = 0

    if "reason_count" not in df.columns:
        df["reason_count"] = 0

    for column in NUMERIC_FEATURES:
        if column not in df.columns:
            df[column] = 0

    for column in CATEGORICAL_FEATURES:
        if column not in df.columns:
            df[column] = "Unknown"

    df[NUMERIC_FEATURES] = df[NUMERIC_FEATURES].apply(
        pd.to_numeric,
        errors="coerce",
    )

    df[CATEGORICAL_FEATURES] = df[CATEGORICAL_FEATURES].fillna("Unknown").astype(str)

    return df


def build_preprocessing_pipeline() -> ColumnTransformer:
    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )

    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, NUMERIC_FEATURES),
            ("categorical", categorical_pipeline, CATEGORICAL_FEATURES),
        ]
    )

    return preprocessor


def assign_anomaly_band(score_percentile: float) -> str:
    if score_percentile >= 99:
        return "Critical"
    if score_percentile >= 95:
        return "High"
    if score_percentile >= 90:
        return "Medium"
    return "Low"


def assign_ml_alert_priority(anomaly_band: str) -> str:
    if anomaly_band == "Critical":
        return "P1"
    if anomaly_band == "High":
        return "P2"
    if anomaly_band == "Medium":
        return "P3"
    return "No Alert"


def create_reason_from_anomaly(row: pd.Series) -> str:
    reasons = []

    if row["amount"] >= 5000:
        reasons.append("UNUSUALLY_HIGH_AMOUNT")

    if int(row["unusual_hour_flag"]) == 1:
        reasons.append("UNUSUAL_TRANSACTION_HOUR")

    if int(row["cross_border_flag"]) == 1:
        reasons.append("CROSS_BORDER_PATTERN")

    if int(row["high_risk_category_flag"]) == 1:
        reasons.append("HIGH_RISK_MERCHANT_CATEGORY_PATTERN")

    if int(row["watchlist_match_flag"]) == 1:
        reasons.append("WATCHLIST_LINKED_PATTERN")

    if int(row["kyc_issue_flag"]) == 1:
        reasons.append("KYC_RISK_PATTERN")

    if row["anomaly_score_percentile"] >= 99:
        reasons.append("TOP_1_PERCENT_ANOMALY_SCORE")
    elif row["anomaly_score_percentile"] >= 95:
        reasons.append("TOP_5_PERCENT_ANOMALY_SCORE")
    elif row["anomaly_score_percentile"] >= 90:
        reasons.append("TOP_10_PERCENT_ANOMALY_SCORE")

    if len(reasons) == 0:
        reasons.append("STATISTICAL_PATTERN_ANOMALY")

    return "; ".join(reasons)


def run_isolation_forest(df: pd.DataFrame) -> pd.DataFrame:
    prepared_df = prepare_ml_features(df)

    feature_df = prepared_df[NUMERIC_FEATURES + CATEGORICAL_FEATURES].copy()

    preprocessor = build_preprocessing_pipeline()

    model = IsolationForest(
        n_estimators=300,
        contamination=0.05,
        random_state=42,
        n_jobs=-1,
    )

    transformed_features = preprocessor.fit_transform(feature_df)

    model.fit(transformed_features)

    raw_predictions = model.predict(transformed_features)
    decision_scores = model.decision_function(transformed_features)

    # Lower decision_function values are more abnormal.
    # We multiply by -1 so higher anomaly_score means more unusual.
    anomaly_scores = -decision_scores

    scored_df = prepared_df.copy()
    scored_df["isolation_forest_prediction"] = raw_predictions
    scored_df["ml_anomaly_flag"] = (raw_predictions == -1).astype(int)
    scored_df["ml_anomaly_score"] = anomaly_scores

    scored_df["anomaly_score_percentile"] = (
        scored_df["ml_anomaly_score"].rank(pct=True) * 100
    ).round(2)

    scored_df["ml_anomaly_band"] = scored_df["anomaly_score_percentile"].apply(
        assign_anomaly_band
    )

    scored_df["ml_alert_priority"] = scored_df["ml_anomaly_band"].apply(
        assign_ml_alert_priority
    )

    scored_df["should_create_ml_alert"] = (
        scored_df["ml_anomaly_band"].isin(["Medium", "High", "Critical"])
    ).astype(int)

    scored_df["ml_reason_codes"] = scored_df.apply(create_reason_from_anomaly, axis=1)

    scored_df["ml_scored_at"] = datetime.now().isoformat(timespec="seconds")

    scored_df["rule_ml_agreement_flag"] = (
        (scored_df["should_create_alert"] == 1)
        & (scored_df["should_create_ml_alert"] == 1)
    ).astype(int)

    scored_df["combined_risk_signal"] = np.where(
        scored_df["rule_ml_agreement_flag"] == 1,
        "Rule and ML",
        np.where(
            scored_df["should_create_ml_alert"] == 1,
            "ML Only",
            np.where(
                scored_df["should_create_alert"] == 1,
                "Rule Only",
                "No Alert",
            ),
        ),
    )

    scored_df = scored_df.sort_values(
        by=["anomaly_score_percentile", "rule_based_risk_score", "amount"],
        ascending=[False, False, False],
    ).reset_index(drop=True)

    return scored_df


def create_ml_alerts(scored_df: pd.DataFrame) -> pd.DataFrame:
    alerts = scored_df[scored_df["should_create_ml_alert"] == 1].copy()
    alerts = alerts.reset_index(drop=True)

    alerts.insert(
        0,
        "ml_alert_id",
        [f"ML-ANOMALY-{i + 1:06d}" for i in range(len(alerts))],
    )

    alerts["ml_alert_status"] = "Open"

    alerts["ml_alert_type"] = "Isolation Forest Transaction Anomaly"

    alerts["ml_alert_owner"] = alerts["ml_anomaly_band"].map(
        {
            "Critical": "Financial Crime Senior Analyst",
            "High": "Financial Crime Analyst",
            "Medium": "Operations Risk Analyst",
            "Low": "Operations Analyst",
        }
    )

    alerts["ml_recommended_action"] = alerts["ml_anomaly_band"].map(
        {
            "Critical": "Immediate investigation required. Review anomaly score, customer profile, rule score, and transaction context.",
            "High": "Prioritised investigation required. Compare against customer history and triggered rule signals.",
            "Medium": "Review if repeated behaviour appears or if combined with other risk indicators.",
            "Low": "No immediate ML action required.",
        }
    )

    selected_columns = [
        "ml_alert_id",
        "ml_alert_status",
        "ml_alert_type",
        "ml_alert_priority",
        "ml_alert_owner",
        "ml_recommended_action",
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
        "alert_priority",
        "ml_anomaly_score",
        "anomaly_score_percentile",
        "ml_anomaly_flag",
        "ml_anomaly_band",
        "ml_reason_codes",
        "combined_risk_signal",
        "suspicious_label",
        "ml_scored_at",
    ]

    existing_columns = [column for column in selected_columns if column in alerts.columns]

    return alerts[existing_columns]


def create_customer_ml_summary(scored_df: pd.DataFrame) -> pd.DataFrame:
    customer_summary = (
        scored_df.groupby("customer_id")
        .agg(
            full_name=("full_name", "first"),
            customer_segment=("customer_segment", "first"),
            customer_country=("customer_master_country", "first"),
            transaction_count=("transaction_id", "count"),
            ml_alert_count=("should_create_ml_alert", "sum"),
            ml_anomaly_count=("ml_anomaly_flag", "sum"),
            average_ml_anomaly_score=("ml_anomaly_score", "mean"),
            max_anomaly_score_percentile=("anomaly_score_percentile", "max"),
            average_rule_based_risk_score=("rule_based_risk_score", "mean"),
            max_rule_based_risk_score=("rule_based_risk_score", "max"),
            total_amount=("amount", "sum"),
            max_amount=("amount", "max"),
            suspicious_label_count=("suspicious_label", "sum"),
        )
        .reset_index()
    )

    customer_summary["average_ml_anomaly_score"] = customer_summary[
        "average_ml_anomaly_score"
    ].round(4)

    customer_summary["average_rule_based_risk_score"] = customer_summary[
        "average_rule_based_risk_score"
    ].round(2)

    customer_summary["total_amount"] = customer_summary["total_amount"].round(2)
    customer_summary["max_amount"] = customer_summary["max_amount"].round(2)

    customer_summary["customer_ml_review_priority"] = np.where(
        customer_summary["max_anomaly_score_percentile"] >= 99,
        "P1",
        np.where(
            customer_summary["max_anomaly_score_percentile"] >= 95,
            "P2",
            np.where(
                customer_summary["max_anomaly_score_percentile"] >= 90,
                "P3",
                "No Review",
            ),
        ),
    )

    customer_summary = customer_summary.sort_values(
        by=["max_anomaly_score_percentile", "ml_alert_count", "total_amount"],
        ascending=[False, False, False],
    ).reset_index(drop=True)

    return customer_summary


def save_to_duckdb(
    con: duckdb.DuckDBPyConnection,
    anomaly_scores: pd.DataFrame,
    ml_alerts: pd.DataFrame,
    customer_ml_summary: pd.DataFrame,
) -> None:
    con.register("ml_transaction_anomaly_scores_df", anomaly_scores)
    con.register("ml_transaction_anomaly_alerts_df", ml_alerts)
    con.register("ml_customer_anomaly_summary_df", customer_ml_summary)

    con.execute(
        """
        CREATE OR REPLACE TABLE ml_transaction_anomaly_scores AS
        SELECT *
        FROM ml_transaction_anomaly_scores_df;
        """
    )

    con.execute(
        """
        CREATE OR REPLACE TABLE ml_transaction_anomaly_alerts AS
        SELECT *
        FROM ml_transaction_anomaly_alerts_df;
        """
    )

    con.execute(
        """
        CREATE OR REPLACE TABLE ml_customer_anomaly_summary AS
        SELECT *
        FROM ml_customer_anomaly_summary_df;
        """
    )

    con.execute(
        """
        CREATE OR REPLACE VIEW vw_ml_anomaly_summary AS
        SELECT
            ml_anomaly_band,
            ml_alert_priority,
            combined_risk_signal,
            COUNT(*) AS transaction_count,
            ROUND(AVG(anomaly_score_percentile), 2) AS average_anomaly_percentile,
            ROUND(AVG(rule_based_risk_score), 2) AS average_rule_score,
            ROUND(SUM(amount), 2) AS total_amount
        FROM ml_transaction_anomaly_scores
        GROUP BY ml_anomaly_band, ml_alert_priority, combined_risk_signal
        ORDER BY average_anomaly_percentile DESC;
        """
    )

    con.execute(
        """
        CREATE OR REPLACE VIEW vw_ml_vs_rule_summary AS
        SELECT
            combined_risk_signal,
            COUNT(*) AS transaction_count,
            ROUND(AVG(rule_based_risk_score), 2) AS average_rule_score,
            ROUND(AVG(anomaly_score_percentile), 2) AS average_anomaly_percentile,
            SUM(suspicious_label) AS known_suspicious_label_count
        FROM ml_transaction_anomaly_scores
        GROUP BY combined_risk_signal
        ORDER BY transaction_count DESC;
        """
    )

    print("Saved ML anomaly tables and views to DuckDB")


def save_reports(
    anomaly_scores: pd.DataFrame,
    ml_alerts: pd.DataFrame,
    customer_ml_summary: pd.DataFrame,
) -> None:
    anomaly_scores_path = REPORTS_DIR / "stage6_ml_transaction_anomaly_scores.csv"
    ml_alerts_path = REPORTS_DIR / "stage6_ml_transaction_anomaly_alerts.csv"
    customer_summary_path = REPORTS_DIR / "stage6_ml_customer_anomaly_summary.csv"
    summary_path = REPORTS_DIR / "stage6_ml_anomaly_summary.json"

    anomaly_scores.to_csv(anomaly_scores_path, index=False)
    ml_alerts.to_csv(ml_alerts_path, index=False)
    customer_ml_summary.to_csv(customer_summary_path, index=False)

    summary = {
        "run_timestamp": datetime.now().isoformat(timespec="seconds"),
        "model_type": "IsolationForest",
        "n_estimators": 300,
        "contamination": 0.05,
        "transactions_scored": int(len(anomaly_scores)),
        "ml_anomaly_flags": int(anomaly_scores["ml_anomaly_flag"].sum()),
        "ml_alerts_created": int(len(ml_alerts)),
        "critical_ml_anomalies": int((anomaly_scores["ml_anomaly_band"] == "Critical").sum()),
        "high_ml_anomalies": int((anomaly_scores["ml_anomaly_band"] == "High").sum()),
        "medium_ml_anomalies": int((anomaly_scores["ml_anomaly_band"] == "Medium").sum()),
        "rule_and_ml_alerts": int((anomaly_scores["combined_risk_signal"] == "Rule and ML").sum()),
        "ml_only_alerts": int((anomaly_scores["combined_risk_signal"] == "ML Only").sum()),
        "rule_only_alerts": int((anomaly_scores["combined_risk_signal"] == "Rule Only").sum()),
        "average_anomaly_score": round(float(anomaly_scores["ml_anomaly_score"].mean()), 6),
        "max_anomaly_score": round(float(anomaly_scores["ml_anomaly_score"].max()), 6),
    }

    summary_path.write_text(json.dumps(summary, indent=4))

    print(f"Saved {anomaly_scores_path}")
    print(f"Saved {ml_alerts_path}")
    print(f"Saved {customer_summary_path}")
    print(f"Saved {summary_path}")


def print_console_summary(
    anomaly_scores: pd.DataFrame,
    ml_alerts: pd.DataFrame,
    customer_ml_summary: pd.DataFrame,
) -> None:
    print("\nML Anomaly Band Summary")
    print("-----------------------")
    print(anomaly_scores["ml_anomaly_band"].value_counts().to_string())

    print("\nCombined Rule vs ML Signal Summary")
    print("----------------------------------")
    print(anomaly_scores["combined_risk_signal"].value_counts().to_string())

    print("\nTop 10 ML Anomaly Alerts")
    print("------------------------")
    print(
        ml_alerts[
            [
                "ml_alert_id",
                "transaction_id",
                "customer_id",
                "amount",
                "ml_anomaly_band",
                "anomaly_score_percentile",
                "rule_based_risk_score",
                "combined_risk_signal",
                "ml_reason_codes",
            ]
        ]
        .head(10)
        .to_string(index=False)
    )

    print("\nTop 10 Customer ML Anomaly Summary")
    print("----------------------------------")
    print(
        customer_ml_summary[
            [
                "customer_id",
                "full_name",
                "transaction_count",
                "ml_alert_count",
                "max_anomaly_score_percentile",
                "customer_ml_review_priority",
            ]
        ]
        .head(10)
        .to_string(index=False)
    )


def main() -> None:
    check_database_exists()

    print(f"Running Stage 6 ML anomaly detection against: {DB_PATH}")

    with duckdb.connect(str(DB_PATH)) as con:
        transactions = load_transactions(con)

        anomaly_scores = run_isolation_forest(transactions)
        ml_alerts = create_ml_alerts(anomaly_scores)
        customer_ml_summary = create_customer_ml_summary(anomaly_scores)

        save_to_duckdb(con, anomaly_scores, ml_alerts, customer_ml_summary)
        save_reports(anomaly_scores, ml_alerts, customer_ml_summary)
        print_console_summary(anomaly_scores, ml_alerts, customer_ml_summary)

    print("\nStage 6 ML anomaly detection completed successfully")


if __name__ == "__main__":
    main()