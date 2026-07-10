from pathlib import Path
import json
from datetime import datetime, timedelta

import duckdb
import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]

DB_PATH = BASE_DIR / "data" / "processed" / "transaction_risk.duckdb"
REPORTS_DIR = BASE_DIR / "reports"

REPORTS_DIR.mkdir(parents=True, exist_ok=True)


PRIORITY_SLA_HOURS = {
    "P1": 4,
    "P2": 24,
    "P3": 72,
    "P4": 120,
    "No Alert": 9999,
}


PRIORITY_RANK = {
    "P1": 1,
    "P2": 2,
    "P3": 3,
    "P4": 4,
    "No Alert": 9,
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


def load_table_if_exists(con: duckdb.DuckDBPyConnection, table_name: str) -> pd.DataFrame:
    if table_exists(con, table_name):
        df = con.execute(f"SELECT * FROM {table_name};").df()
        print(f"Loaded {table_name}: {len(df):,} rows")
        return df

    print(f"Table not found, skipping: {table_name}")
    return pd.DataFrame()


def safe_text(value, default: str = "") -> str:
    if pd.isna(value):
        return default

    return str(value)


def safe_number(value, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def parse_datetime(value) -> datetime:
    if pd.isna(value) or value == "":
        return datetime.now()

    parsed = pd.to_datetime(value, errors="coerce")

    if pd.isna(parsed):
        return datetime.now()

    return parsed.to_pydatetime()


def priority_from_severity(severity: str) -> str:
    severity = safe_text(severity)

    if severity in ["Critical", "High"]:
        return "P1" if severity == "Critical" else "P2"

    if severity == "Medium":
        return "P3"

    if severity == "Low":
        return "P4"

    return "P3"


def priority_from_score(score: float) -> str:
    score = safe_number(score)

    if score >= 80:
        return "P1"

    if score >= 60:
        return "P2"

    if score >= 35:
        return "P3"

    return "P4"


def calculate_due_datetime(created_at: datetime, priority: str) -> datetime:
    sla_hours = PRIORITY_SLA_HOURS.get(priority, 72)
    return created_at + timedelta(hours=sla_hours)


def case_age_bucket(age_days: int) -> str:
    if age_days <= 0:
        return "Today"

    if age_days <= 3:
        return "1-3 days"

    if age_days <= 7:
        return "4-7 days"

    if age_days <= 14:
        return "8-14 days"

    return "15+ days"


def sla_status(due_at: datetime, case_status: str) -> str:
    if case_status in ["Closed", "Resolved"]:
        return "Closed"

    now = datetime.now()

    if due_at < now:
        return "Breached"

    hours_remaining = (due_at - now).total_seconds() / 3600

    if hours_remaining <= 8:
        return "At Risk"

    return "Within SLA"


def owner_from_priority_and_source(priority: str, source_type: str) -> str:
    if source_type == "Reconciliation Break":
        if priority in ["P1", "P2"]:
            return "Senior Reconciliation Analyst"
        return "Reconciliation Analyst"

    if source_type in ["Rule-Based Transaction Risk", "ML Anomaly", "Explainability Alert"]:
        if priority == "P1":
            return "Financial Crime Senior Analyst"
        if priority == "P2":
            return "Financial Crime Analyst"
        return "Operations Risk Analyst"

    if source_type in ["Graph Entity Risk", "Suspicious Transfer Pattern", "Graph Risk Cluster"]:
        if priority in ["P1", "P2"]:
            return "AML Network Analyst"
        return "Operations Risk Analyst"

    return "Operations Analyst"


def create_case_record(
    source_type: str,
    source_record_id: str,
    priority: str,
    title: str,
    description: str,
    recommended_action: str,
    created_at,
    customer_id: str = "",
    customer_name: str = "",
    transaction_id: str = "",
    account_id: str = "",
    merchant_id: str = "",
    amount: float = 0.0,
    risk_score: float = 0.0,
    risk_band: str = "",
    main_trigger: str = "",
) -> dict:
    created_datetime = parse_datetime(created_at)
    due_datetime = calculate_due_datetime(created_datetime, priority)

    age_days = max((datetime.now() - created_datetime).days, 0)

    case_status = "Open"

    return {
        "case_source_type": source_type,
        "source_record_id": source_record_id,
        "case_priority": priority,
        "priority_rank": PRIORITY_RANK.get(priority, 9),
        "case_status": case_status,
        "case_owner": owner_from_priority_and_source(priority, source_type),
        "case_title": title,
        "case_description": description,
        "recommended_action": recommended_action,
        "created_at": created_datetime.isoformat(timespec="seconds"),
        "sla_due_at": due_datetime.isoformat(timespec="seconds"),
        "sla_status": sla_status(due_datetime, case_status),
        "case_age_days": age_days,
        "case_age_bucket": case_age_bucket(age_days),
        "customer_id": customer_id,
        "customer_name": customer_name,
        "transaction_id": transaction_id,
        "account_id": account_id,
        "merchant_id": merchant_id,
        "amount": round(safe_number(amount), 2),
        "risk_score": round(safe_number(risk_score), 2),
        "risk_band": risk_band,
        "main_trigger": main_trigger,
    }


def cases_from_reconciliation_breaks(df: pd.DataFrame) -> list[dict]:
    cases = []

    if df.empty:
        return cases

    for _, row in df.iterrows():
        severity = safe_text(row.get("severity", "Medium"))
        priority = priority_from_severity(severity)

        created_at = datetime.now() - timedelta(
            days=int(safe_number(row.get("case_age_days", 0)))
        )

        case = create_case_record(
            source_type="Reconciliation Break",
            source_record_id=safe_text(row.get("case_id", "")),
            priority=priority,
            title=f"Reconciliation break: {safe_text(row.get('break_type', 'Unknown'))}",
            description=(
                f"Transaction {safe_text(row.get('transaction_id', ''))} has a reconciliation break "
                f"classified as {safe_text(row.get('break_type', 'Unknown'))}."
            ),
            recommended_action=safe_text(
                row.get(
                    "recommended_action",
                    "Investigate reconciliation break and compare source-system records.",
                )
            ),
            created_at=created_at,
            transaction_id=safe_text(row.get("transaction_id", "")),
            account_id=safe_text(row.get("a_account_id", row.get("b_account_id", ""))),
            amount=safe_number(row.get("absolute_amount_difference", 0)),
            risk_score=75 if priority == "P1" else 60 if priority == "P2" else 40,
            risk_band=severity,
            main_trigger="Reconciliation Break",
        )

        cases.append(case)

    return cases


def cases_from_rule_alerts(df: pd.DataFrame) -> list[dict]:
    cases = []

    if df.empty:
        return cases

    for _, row in df.iterrows():
        priority = safe_text(row.get("alert_priority", "P3"))

        if priority == "No Alert":
            continue

        case = create_case_record(
            source_type="Rule-Based Transaction Risk",
            source_record_id=safe_text(row.get("alert_id", "")),
            priority=priority,
            title=f"Rule-based risk alert: {safe_text(row.get('risk_band', 'Unknown'))}",
            description=(
                f"Transaction {safe_text(row.get('transaction_id', ''))} triggered rule-based risk scoring "
                f"with reason codes: {safe_text(row.get('reason_codes', ''))}."
            ),
            recommended_action=safe_text(
                row.get(
                    "recommended_action",
                    "Review rule-based risk indicators and supporting customer context.",
                )
            ),
            created_at=row.get("scored_at", datetime.now()),
            customer_id=safe_text(row.get("customer_id", "")),
            customer_name=safe_text(row.get("full_name", "")),
            transaction_id=safe_text(row.get("transaction_id", "")),
            account_id=safe_text(row.get("account_id", "")),
            merchant_id=safe_text(row.get("merchant_id", "")),
            amount=safe_number(row.get("amount", 0)),
            risk_score=safe_number(row.get("rule_based_risk_score", 0)),
            risk_band=safe_text(row.get("risk_band", "")),
            main_trigger="Rule-Based Risk",
        )

        cases.append(case)

    return cases


def cases_from_ml_alerts(df: pd.DataFrame) -> list[dict]:
    cases = []

    if df.empty:
        return cases

    for _, row in df.iterrows():
        priority = safe_text(row.get("ml_alert_priority", "P3"))

        if priority == "No Alert":
            continue

        case = create_case_record(
            source_type="ML Anomaly",
            source_record_id=safe_text(row.get("ml_alert_id", "")),
            priority=priority,
            title=f"ML anomaly alert: {safe_text(row.get('ml_anomaly_band', 'Unknown'))}",
            description=(
                f"Transaction {safe_text(row.get('transaction_id', ''))} was flagged by Isolation Forest "
                f"with anomaly percentile {safe_number(row.get('anomaly_score_percentile', 0)):.2f}. "
                f"Reason codes: {safe_text(row.get('ml_reason_codes', ''))}."
            ),
            recommended_action=safe_text(
                row.get(
                    "ml_recommended_action",
                    "Review ML anomaly behaviour and compare with rule-based risk indicators.",
                )
            ),
            created_at=row.get("ml_scored_at", datetime.now()),
            customer_id=safe_text(row.get("customer_id", "")),
            customer_name=safe_text(row.get("full_name", "")),
            transaction_id=safe_text(row.get("transaction_id", "")),
            account_id=safe_text(row.get("account_id", "")),
            merchant_id=safe_text(row.get("merchant_id", "")),
            amount=safe_number(row.get("amount", 0)),
            risk_score=safe_number(row.get("anomaly_score_percentile", 0)),
            risk_band=safe_text(row.get("ml_anomaly_band", "")),
            main_trigger=safe_text(row.get("combined_risk_signal", "ML Anomaly")),
        )

        cases.append(case)

    return cases


def cases_from_explainability_alerts(df: pd.DataFrame) -> list[dict]:
    cases = []

    if df.empty:
        return cases

    for _, row in df.iterrows():
        priority = safe_text(row.get("explanation_priority", "P3"))

        if priority == "No Alert":
            continue

        case = create_case_record(
            source_type="Explainability Alert",
            source_record_id=safe_text(row.get("explanation_id", "")),
            priority=priority,
            title=f"Explainable alert: {safe_text(row.get('main_trigger', 'Unknown'))}",
            description=safe_text(
                row.get(
                    "plain_english_explanation",
                    "Explainability layer generated an alert requiring review.",
                )
            ),
            recommended_action=safe_text(
                row.get(
                    "recommended_investigation_action",
                    "Review explanation, evidence summary and supporting alert sources.",
                )
            ),
            created_at=row.get("generated_at", datetime.now()),
            customer_id=safe_text(row.get("customer_id", "")),
            customer_name=safe_text(row.get("full_name", "")),
            transaction_id=safe_text(row.get("transaction_id", "")),
            account_id=safe_text(row.get("account_id", "")),
            merchant_id=safe_text(row.get("merchant_id", "")),
            amount=safe_number(row.get("amount", 0)),
            risk_score=safe_number(row.get("combined_explanation_score", 0)),
            risk_band=safe_text(row.get("explanation_priority", "")),
            main_trigger=safe_text(row.get("main_trigger", "")),
        )

        cases.append(case)

    return cases


def cases_from_graph_entities(df: pd.DataFrame) -> list[dict]:
    cases = []

    if df.empty:
        return cases

    for _, row in df.iterrows():
        priority = priority_from_score(safe_number(row.get("graph_priority_score", 0)))

        if priority == "P4":
            continue

        node_id = safe_text(row.get("node_id", ""))
        node_type = safe_text(row.get("node_type", ""))

        customer_id = node_id if node_type == "Customer" else ""
        account_id = node_id if node_type == "Account" else ""
        merchant_id = node_id if node_type == "Merchant" else ""

        case = create_case_record(
            source_type="Graph Entity Risk",
            source_record_id=safe_text(row.get("centrality_case_id", "")),
            priority=priority,
            title=f"High-centrality graph entity: {node_type}",
            description=(
                f"Graph entity {node_id} has graph priority score "
                f"{safe_number(row.get('graph_priority_score', 0)):.2f}, "
                f"risk band {safe_text(row.get('node_risk_band', ''))}, and total degree "
                f"{int(safe_number(row.get('total_degree', 0)))}."
            ),
            recommended_action=safe_text(
                row.get(
                    "recommended_action",
                    "Review high-risk graph entity and connected network.",
                )
            ),
            created_at=datetime.now(),
            customer_id=customer_id,
            customer_name=safe_text(row.get("node_label", "")) if node_type == "Customer" else "",
            account_id=account_id,
            merchant_id=merchant_id,
            amount=safe_number(row.get("total_transaction_amount", 0)),
            risk_score=safe_number(row.get("graph_priority_score", 0)),
            risk_band=safe_text(row.get("node_risk_band", "")),
            main_trigger="Graph Centrality",
        )

        cases.append(case)

    return cases


def cases_from_transfer_patterns(df: pd.DataFrame) -> list[dict]:
    cases = []

    if df.empty:
        return cases

    for _, row in df.iterrows():
        priority = priority_from_score(safe_number(row.get("pattern_risk_score", 0)))

        if priority == "P4":
            continue

        case = create_case_record(
            source_type="Suspicious Transfer Pattern",
            source_record_id=safe_text(row.get("pattern_id", "")),
            priority=priority,
            title=f"Suspicious transfer pattern: {safe_text(row.get('pattern_type', 'Unknown'))}",
            description=safe_text(
                row.get(
                    "pattern_explanation",
                    "Suspicious transfer pattern detected in account network.",
                )
            ),
            recommended_action=safe_text(
                row.get(
                    "recommended_action",
                    "Review transfer pattern and account relationships.",
                )
            ),
            created_at=datetime.now(),
            customer_id=safe_text(row.get("source_customer_id", "")),
            account_id=safe_text(row.get("source_account_id", row.get("destination_account_id", ""))),
            amount=safe_number(row.get("total_amount", 0)),
            risk_score=safe_number(row.get("pattern_risk_score", 0)),
            risk_band=priority,
            main_trigger=safe_text(row.get("pattern_type", "")),
        )

        cases.append(case)

    return cases


def cases_from_graph_clusters(df: pd.DataFrame) -> list[dict]:
    cases = []

    if df.empty:
        return cases

    for _, row in df.iterrows():
        priority = priority_from_score(safe_number(row.get("cluster_risk_score", 0)))

        if priority == "P4":
            continue

        case = create_case_record(
            source_type="Graph Risk Cluster",
            source_record_id=safe_text(row.get("cluster_id", "")),
            priority=priority,
            title=f"Graph risk cluster: {safe_text(row.get('cluster_risk_band', 'Unknown'))}",
            description=(
                f"Graph cluster {safe_text(row.get('cluster_id', ''))} contains "
                f"{int(safe_number(row.get('node_count', 0)))} nodes, "
                f"{int(safe_number(row.get('edge_count', 0)))} edges, "
                f"{int(safe_number(row.get('watchlist_node_count', 0)))} watchlist nodes, "
                f"and cluster risk score {safe_number(row.get('cluster_risk_score', 0)):.2f}."
            ),
            recommended_action="Review graph cluster, top priority nodes and connected relationships.",
            created_at=datetime.now(),
            amount=safe_number(row.get("total_edge_amount", 0)),
            risk_score=safe_number(row.get("cluster_risk_score", 0)),
            risk_band=safe_text(row.get("cluster_risk_band", "")),
            main_trigger="Graph Cluster Risk",
        )

        cases.append(case)

    return cases


def build_unified_cases(
    reconciliation_breaks: pd.DataFrame,
    rule_alerts: pd.DataFrame,
    ml_alerts: pd.DataFrame,
    explainability_alerts: pd.DataFrame,
    graph_entities: pd.DataFrame,
    transfer_patterns: pd.DataFrame,
    graph_clusters: pd.DataFrame,
) -> pd.DataFrame:
    cases = []

    cases.extend(cases_from_reconciliation_breaks(reconciliation_breaks))
    cases.extend(cases_from_rule_alerts(rule_alerts))
    cases.extend(cases_from_ml_alerts(ml_alerts))
    cases.extend(cases_from_explainability_alerts(explainability_alerts))
    cases.extend(cases_from_graph_entities(graph_entities))
    cases.extend(cases_from_transfer_patterns(transfer_patterns))
    cases.extend(cases_from_graph_clusters(graph_clusters))

    if not cases:
        return pd.DataFrame()

    cases_df = pd.DataFrame(cases)

    cases_df = cases_df.sort_values(
        by=["priority_rank", "risk_score", "amount"],
        ascending=[True, False, False],
    ).reset_index(drop=True)

    cases_df.insert(
        0,
        "case_id",
        [f"CASE-{i + 1:07d}" for i in range(len(cases_df))],
    )

    cases_df["last_updated_at"] = datetime.now().isoformat(timespec="seconds")

    return cases_df


def create_case_summary(cases_df: pd.DataFrame) -> pd.DataFrame:
    if cases_df.empty:
        return pd.DataFrame()

    summary = (
        cases_df.groupby(
            [
                "case_source_type",
                "case_priority",
                "case_status",
                "sla_status",
                "case_age_bucket",
            ]
        )
        .agg(
            case_count=("case_id", "count"),
            average_risk_score=("risk_score", "mean"),
            total_amount=("amount", "sum"),
            oldest_case_age_days=("case_age_days", "max"),
        )
        .reset_index()
    )

    summary["average_risk_score"] = summary["average_risk_score"].round(2)
    summary["total_amount"] = summary["total_amount"].round(2)

    summary = summary.sort_values(
        by=["case_source_type", "case_priority", "case_count"],
        ascending=[True, True, False],
    ).reset_index(drop=True)

    return summary


def create_case_work_queue(cases_df: pd.DataFrame) -> pd.DataFrame:
    if cases_df.empty:
        return pd.DataFrame()

    work_queue = cases_df[cases_df["case_status"] == "Open"].copy()

    work_queue = work_queue.sort_values(
        by=["priority_rank", "sla_status", "risk_score", "case_age_days"],
        ascending=[True, True, False, False],
    ).reset_index(drop=True)

    work_queue["queue_rank"] = range(1, len(work_queue) + 1)

    selected_columns = [
        "queue_rank",
        "case_id",
        "case_source_type",
        "case_priority",
        "case_status",
        "sla_status",
        "case_owner",
        "case_title",
        "customer_id",
        "transaction_id",
        "account_id",
        "merchant_id",
        "amount",
        "risk_score",
        "risk_band",
        "case_age_days",
        "case_age_bucket",
        "created_at",
        "sla_due_at",
        "main_trigger",
        "recommended_action",
    ]

    return work_queue[selected_columns]


def save_to_duckdb(
    con: duckdb.DuckDBPyConnection,
    cases_df: pd.DataFrame,
    case_summary: pd.DataFrame,
    work_queue: pd.DataFrame,
) -> None:
    con.register("case_management_cases_df", cases_df)
    con.register("case_management_summary_df", case_summary)
    con.register("case_management_work_queue_df", work_queue)

    con.execute(
        """
        CREATE OR REPLACE TABLE case_management_cases AS
        SELECT *
        FROM case_management_cases_df;
        """
    )

    con.execute(
        """
        CREATE OR REPLACE TABLE case_management_summary AS
        SELECT *
        FROM case_management_summary_df;
        """
    )

    con.execute(
        """
        CREATE OR REPLACE TABLE case_management_work_queue AS
        SELECT *
        FROM case_management_work_queue_df;
        """
    )

    con.execute(
        """
        CREATE OR REPLACE VIEW vw_case_management_priority_summary AS
        SELECT
            case_priority,
            case_status,
            sla_status,
            COUNT(*) AS case_count,
            ROUND(AVG(risk_score), 2) AS average_risk_score,
            ROUND(SUM(amount), 2) AS total_amount,
            MAX(case_age_days) AS oldest_case_age_days
        FROM case_management_cases
        GROUP BY case_priority, case_status, sla_status
        ORDER BY
            CASE case_priority
                WHEN 'P1' THEN 1
                WHEN 'P2' THEN 2
                WHEN 'P3' THEN 3
                WHEN 'P4' THEN 4
                ELSE 9
            END,
            case_count DESC;
        """
    )

    con.execute(
        """
        CREATE OR REPLACE VIEW vw_case_management_source_summary AS
        SELECT
            case_source_type,
            case_priority,
            COUNT(*) AS case_count,
            ROUND(AVG(risk_score), 2) AS average_risk_score,
            ROUND(SUM(amount), 2) AS total_amount,
            SUM(CASE WHEN sla_status = 'Breached' THEN 1 ELSE 0 END) AS breached_cases,
            SUM(CASE WHEN sla_status = 'At Risk' THEN 1 ELSE 0 END) AS at_risk_cases
        FROM case_management_cases
        GROUP BY case_source_type, case_priority
        ORDER BY case_source_type, case_priority;
        """
    )

    con.execute(
        """
        CREATE OR REPLACE VIEW vw_case_management_owner_queue AS
        SELECT
            case_owner,
            case_priority,
            COUNT(*) AS open_case_count,
            ROUND(AVG(risk_score), 2) AS average_risk_score,
            MAX(case_age_days) AS oldest_case_age_days,
            SUM(CASE WHEN sla_status = 'Breached' THEN 1 ELSE 0 END) AS breached_cases,
            SUM(CASE WHEN sla_status = 'At Risk' THEN 1 ELSE 0 END) AS at_risk_cases
        FROM case_management_cases
        WHERE case_status = 'Open'
        GROUP BY case_owner, case_priority
        ORDER BY open_case_count DESC;
        """
    )

    print("Saved case management tables and views to DuckDB")


def save_reports(
    cases_df: pd.DataFrame,
    case_summary: pd.DataFrame,
    work_queue: pd.DataFrame,
) -> None:
    cases_path = REPORTS_DIR / "stage9_case_management_cases.csv"
    summary_path = REPORTS_DIR / "stage9_case_management_summary.csv"
    work_queue_path = REPORTS_DIR / "stage9_case_management_work_queue.csv"
    json_summary_path = REPORTS_DIR / "stage9_case_management_summary.json"

    cases_df.to_csv(cases_path, index=False)
    case_summary.to_csv(summary_path, index=False)
    work_queue.to_csv(work_queue_path, index=False)

    json_summary = {
        "run_timestamp": datetime.now().isoformat(timespec="seconds"),
        "total_cases": int(len(cases_df)),
        "open_cases": int((cases_df["case_status"] == "Open").sum()),
        "p1_cases": int((cases_df["case_priority"] == "P1").sum()),
        "p2_cases": int((cases_df["case_priority"] == "P2").sum()),
        "p3_cases": int((cases_df["case_priority"] == "P3").sum()),
        "p4_cases": int((cases_df["case_priority"] == "P4").sum()),
        "breached_sla_cases": int((cases_df["sla_status"] == "Breached").sum()),
        "at_risk_sla_cases": int((cases_df["sla_status"] == "At Risk").sum()),
        "within_sla_cases": int((cases_df["sla_status"] == "Within SLA").sum()),
        "unique_customers_in_cases": int(cases_df["customer_id"].replace("", np.nan).nunique()),
        "unique_transactions_in_cases": int(cases_df["transaction_id"].replace("", np.nan).nunique()),
        "case_sources": cases_df["case_source_type"].value_counts().to_dict(),
    }

    json_summary_path.write_text(json.dumps(json_summary, indent=4))

    print(f"Saved {cases_path}")
    print(f"Saved {summary_path}")
    print(f"Saved {work_queue_path}")
    print(f"Saved {json_summary_path}")


def print_console_summary(
    cases_df: pd.DataFrame,
    case_summary: pd.DataFrame,
    work_queue: pd.DataFrame,
) -> None:
    print("\nCase Priority Summary")
    print("---------------------")
    print(cases_df["case_priority"].value_counts().to_string())

    print("\nCase Source Summary")
    print("-------------------")
    print(cases_df["case_source_type"].value_counts().to_string())

    print("\nSLA Status Summary")
    print("------------------")
    print(cases_df["sla_status"].value_counts().to_string())

    print("\nTop 15 Work Queue Cases")
    print("-----------------------")
    print(
        work_queue[
            [
                "queue_rank",
                "case_id",
                "case_source_type",
                "case_priority",
                "sla_status",
                "case_owner",
                "risk_score",
                "case_title",
            ]
        ]
        .head(15)
        .to_string(index=False)
    )


def main() -> None:
    check_database_exists()

    print(f"Running Stage 9 case management against: {DB_PATH}")

    with duckdb.connect(str(DB_PATH)) as con:
        reconciliation_breaks = load_table_if_exists(con, "reconciliation_breaks")
        rule_alerts = load_table_if_exists(con, "transaction_risk_alerts")
        ml_alerts = load_table_if_exists(con, "ml_transaction_anomaly_alerts")
        explainability_alerts = load_table_if_exists(con, "alert_explanations")
        graph_entities = load_table_if_exists(con, "graph_high_centrality_entities")
        transfer_patterns = load_table_if_exists(con, "graph_suspicious_transfer_patterns")
        graph_clusters = load_table_if_exists(con, "graph_risk_clusters")

        cases_df = build_unified_cases(
            reconciliation_breaks=reconciliation_breaks,
            rule_alerts=rule_alerts,
            ml_alerts=ml_alerts,
            explainability_alerts=explainability_alerts,
            graph_entities=graph_entities,
            transfer_patterns=transfer_patterns,
            graph_clusters=graph_clusters,
        )

        if cases_df.empty:
            raise RuntimeError("No cases were created. Run earlier stages first.")

        case_summary = create_case_summary(cases_df)
        work_queue = create_case_work_queue(cases_df)

        save_to_duckdb(con, cases_df, case_summary, work_queue)
        save_reports(cases_df, case_summary, work_queue)
        print_console_summary(cases_df, case_summary, work_queue)

    print("\nStage 9 case management completed successfully")


if __name__ == "__main__":
    main()