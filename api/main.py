from pathlib import Path
from typing import Optional, Any

import duckdb
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field


BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "processed" / "transaction_risk.duckdb"


app = FastAPI(
    title="Transaction Risk Intelligence Engine API",
    description=(
        "FastAPI service for financial crime, reconciliation, transaction risk, "
        "ML anomaly detection, graph analytics and case management outputs."
    ),
    version="1.0.0",
)


class TransactionScoreRequest(BaseModel):
    amount: float = Field(..., example=2500.00)
    currency: str = Field("GBP", example="GBP")
    channel: str = Field("E-Commerce", example="Mobile Banking")
    transaction_type: str = Field("Purchase", example="Transfer")
    status: str = Field("Completed", example="Completed")
    merchant_category: str = Field("Online Marketplace", example="Crypto Exchange")

    cross_border_flag: int = Field(0, ge=0, le=1)
    high_amount_flag: Optional[int] = Field(None, ge=0, le=1)
    unusual_hour_flag: int = Field(0, ge=0, le=1)
    high_risk_category_flag: int = Field(0, ge=0, le=1)
    high_risk_country_flag: int = Field(0, ge=0, le=1)
    kyc_issue_flag: int = Field(0, ge=0, le=1)
    pep_flag: int = Field(0, ge=0, le=1)
    watchlist_match_flag: int = Field(0, ge=0, le=1)


def check_database_exists() -> None:
    if not DB_PATH.exists():
        raise HTTPException(
            status_code=500,
            detail=(
                f"DuckDB database not found at {DB_PATH}. "
                "Run earlier stages first, especially Stage 2."
            ),
        )


def get_connection() -> duckdb.DuckDBPyConnection:
    check_database_exists()
    return duckdb.connect(str(DB_PATH), read_only=True)


def dataframe_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty:
        return []

    df = df.replace({np.nan: None})

    return df.to_dict(orient="records")


def single_row_to_dict(df: pd.DataFrame) -> dict[str, Any]:
    records = dataframe_to_records(df)

    if not records:
        raise HTTPException(status_code=404, detail="Record not found")

    return records[0]


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


def require_table(con: duckdb.DuckDBPyConnection, table_name: str) -> None:
    if not table_exists(con, table_name):
        raise HTTPException(
            status_code=404,
            detail=f"Required table not found: {table_name}. Run the related project stage first.",
        )


def run_scalar(con: duckdb.DuckDBPyConnection, query: str) -> Any:
    try:
        return con.execute(query).fetchone()[0]
    except Exception:
        return None


def assign_risk_band(score: int) -> str:
    if score >= 75:
        return "Critical"
    if score >= 55:
        return "High"
    if score >= 30:
        return "Medium"
    return "Low"


def assign_alert_priority(score: int) -> str:
    if score >= 75:
        return "P1"
    if score >= 55:
        return "P2"
    if score >= 30:
        return "P3"
    return "No Alert"


def score_transaction_rule_based(transaction: TransactionScoreRequest) -> dict[str, Any]:
    score = 0
    reasons = []

    high_amount_flag = (
        transaction.high_amount_flag
        if transaction.high_amount_flag is not None
        else int(transaction.amount > 1500)
    )

    def add_reason(reason: str) -> None:
        if reason not in reasons:
            reasons.append(reason)

    if transaction.watchlist_match_flag == 1:
        score += 35
        add_reason("WATCHLIST_MATCH")

    if transaction.pep_flag == 1:
        score += 25
        add_reason("PEP_CUSTOMER")

    if transaction.kyc_issue_flag == 1:
        score += 20
        add_reason("KYC_ISSUE")

    if transaction.high_risk_country_flag == 1:
        score += 18
        add_reason("HIGH_RISK_COUNTRY")

    if transaction.high_risk_category_flag == 1:
        score += 18
        add_reason("HIGH_RISK_MERCHANT_CATEGORY")

    if high_amount_flag == 1:
        score += 15
        add_reason("HIGH_AMOUNT_TRANSACTION")

    if transaction.amount >= 5000:
        score += 15
        add_reason("VERY_HIGH_AMOUNT")

    if transaction.amount >= 10000:
        score += 10
        add_reason("EXTREME_AMOUNT")

    if transaction.cross_border_flag == 1:
        score += 10
        add_reason("CROSS_BORDER_TRANSACTION")

    if transaction.unusual_hour_flag == 1:
        score += 10
        add_reason("UNUSUAL_HOUR_ACTIVITY")

    if transaction.merchant_category in ["Crypto Exchange", "Gambling", "Money Transfer"]:
        score += 10
        add_reason("SENSITIVE_MERCHANT_CATEGORY")

    if transaction.merchant_category in ["Cash Withdrawal", "Luxury Goods"]:
        score += 6
        add_reason("ELEVATED_MERCHANT_CATEGORY")

    if transaction.channel in ["ATM", "API"]:
        score += 5
        add_reason("CHANNEL_MONITORING_FLAG")

    if transaction.status in ["Failed", "Reversed"]:
        score += 5
        add_reason("NON_STANDARD_TRANSACTION_STATUS")

    if transaction.cross_border_flag == 1 and high_amount_flag == 1:
        score += 8
        add_reason("HIGH_AMOUNT_CROSS_BORDER_COMBINATION")

    if transaction.watchlist_match_flag == 1 and transaction.cross_border_flag == 1:
        score += 10
        add_reason("WATCHLIST_CROSS_BORDER_COMBINATION")

    if transaction.pep_flag == 1 and high_amount_flag == 1:
        score += 10
        add_reason("PEP_HIGH_AMOUNT_COMBINATION")

    score = min(score, 100)

    if not reasons:
        reasons.append("NO_MAJOR_RULE_TRIGGERED")

    return {
        "rule_based_risk_score": score,
        "risk_band": assign_risk_band(score),
        "alert_priority": assign_alert_priority(score),
        "should_create_alert": int(score >= 30),
        "reason_codes": reasons,
        "input_transaction": transaction.model_dump(),
    }


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "service": "Transaction Risk Intelligence Engine API",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health_check() -> dict[str, Any]:
    database_exists = DB_PATH.exists()

    return {
        "api_status": "healthy",
        "database_exists": database_exists,
        "database_path": str(DB_PATH),
    }


@app.get("/database/tables")
def list_database_tables() -> dict[str, Any]:
    with get_connection() as con:
        df = con.execute(
            """
            SELECT table_name, table_type
            FROM information_schema.tables
            WHERE table_schema = 'main'
            ORDER BY table_type, table_name;
            """
        ).df()

    return {
        "table_count": len(df),
        "tables": dataframe_to_records(df),
    }


@app.get("/summary/cases")
def case_summary() -> dict[str, Any]:
    with get_connection() as con:
        require_table(con, "case_management_cases")

        summary = {
            "total_cases": run_scalar(con, "SELECT COUNT(*) FROM case_management_cases;"),
            "open_cases": run_scalar(
                con,
                "SELECT COUNT(*) FROM case_management_cases WHERE case_status = 'Open';",
            ),
            "p1_cases": run_scalar(
                con,
                "SELECT COUNT(*) FROM case_management_cases WHERE case_priority = 'P1';",
            ),
            "p2_cases": run_scalar(
                con,
                "SELECT COUNT(*) FROM case_management_cases WHERE case_priority = 'P2';",
            ),
            "breached_sla_cases": run_scalar(
                con,
                "SELECT COUNT(*) FROM case_management_cases WHERE sla_status = 'Breached';",
            ),
            "at_risk_sla_cases": run_scalar(
                con,
                "SELECT COUNT(*) FROM case_management_cases WHERE sla_status = 'At Risk';",
            ),
        }

        source_df = con.execute(
            """
            SELECT case_source_type, COUNT(*) AS case_count
            FROM case_management_cases
            GROUP BY case_source_type
            ORDER BY case_count DESC;
            """
        ).df()

        priority_df = con.execute(
            """
            SELECT case_priority, COUNT(*) AS case_count
            FROM case_management_cases
            GROUP BY case_priority
            ORDER BY
                CASE case_priority
                    WHEN 'P1' THEN 1
                    WHEN 'P2' THEN 2
                    WHEN 'P3' THEN 3
                    WHEN 'P4' THEN 4
                    ELSE 9
                END;
            """
        ).df()

    return {
        "summary": summary,
        "cases_by_source": dataframe_to_records(source_df),
        "cases_by_priority": dataframe_to_records(priority_df),
    }


@app.get("/summary/risk")
def risk_summary() -> dict[str, Any]:
    with get_connection() as con:
        summaries = {}

        if table_exists(con, "transaction_risk_scores"):
            risk_df = con.execute(
                """
                SELECT risk_band, COUNT(*) AS transaction_count
                FROM transaction_risk_scores
                GROUP BY risk_band
                ORDER BY transaction_count DESC;
                """
            ).df()
            summaries["transaction_risk_bands"] = dataframe_to_records(risk_df)

        if table_exists(con, "ml_transaction_anomaly_scores"):
            ml_df = con.execute(
                """
                SELECT ml_anomaly_band, COUNT(*) AS transaction_count
                FROM ml_transaction_anomaly_scores
                GROUP BY ml_anomaly_band
                ORDER BY transaction_count DESC;
                """
            ).df()
            summaries["ml_anomaly_bands"] = dataframe_to_records(ml_df)

        if table_exists(con, "graph_nodes"):
            graph_df = con.execute(
                """
                SELECT node_type, node_risk_band, COUNT(*) AS entity_count
                FROM graph_nodes
                GROUP BY node_type, node_risk_band
                ORDER BY node_type, entity_count DESC;
                """
            ).df()
            summaries["graph_entity_risk_bands"] = dataframe_to_records(graph_df)

    return summaries


@app.get("/cases")
def get_cases(
    priority: Optional[str] = Query(None, example="P1"),
    source_type: Optional[str] = Query(None, example="ML Anomaly"),
    owner: Optional[str] = Query(None, example="Financial Crime Analyst"),
    limit: int = Query(25, ge=1, le=200),
) -> dict[str, Any]:
    with get_connection() as con:
        require_table(con, "case_management_cases")

        query = """
            SELECT *
            FROM case_management_cases
            WHERE 1 = 1
        """

        params = []

        if priority:
            query += " AND case_priority = ?"
            params.append(priority)

        if source_type:
            query += " AND case_source_type = ?"
            params.append(source_type)

        if owner:
            query += " AND case_owner = ?"
            params.append(owner)

        query += f"""
            ORDER BY priority_rank ASC, risk_score DESC, amount DESC
            LIMIT {limit};
        """

        df = con.execute(query, params).df()

    return {
        "count": len(df),
        "cases": dataframe_to_records(df),
    }


@app.get("/cases/{case_id}")
def get_case_by_id(case_id: str) -> dict[str, Any]:
    with get_connection() as con:
        require_table(con, "case_management_cases")

        df = con.execute(
            """
            SELECT *
            FROM case_management_cases
            WHERE case_id = ?;
            """,
            [case_id],
        ).df()

    return single_row_to_dict(df)


@app.get("/work-queue")
def get_work_queue(
    limit: int = Query(25, ge=1, le=200),
) -> dict[str, Any]:
    with get_connection() as con:
        require_table(con, "case_management_work_queue")

        df = con.execute(
            f"""
            SELECT *
            FROM case_management_work_queue
            ORDER BY queue_rank
            LIMIT {limit};
            """
        ).df()

    return {
        "count": len(df),
        "work_queue": dataframe_to_records(df),
    }


@app.get("/transactions/{transaction_id}")
def get_transaction_risk(transaction_id: str) -> dict[str, Any]:
    with get_connection() as con:
        if table_exists(con, "alert_explanations"):
            df = con.execute(
                """
                SELECT *
                FROM alert_explanations
                WHERE transaction_id = ?
                ORDER BY combined_explanation_score DESC
                LIMIT 1;
                """,
                [transaction_id],
            ).df()

            if not df.empty:
                return single_row_to_dict(df)

        if table_exists(con, "ml_transaction_anomaly_scores"):
            df = con.execute(
                """
                SELECT *
                FROM ml_transaction_anomaly_scores
                WHERE transaction_id = ?;
                """,
                [transaction_id],
            ).df()

            if not df.empty:
                return single_row_to_dict(df)

        require_table(con, "transaction_risk_scores")

        df = con.execute(
            """
            SELECT *
            FROM transaction_risk_scores
            WHERE transaction_id = ?;
            """,
            [transaction_id],
        ).df()

    return single_row_to_dict(df)


@app.get("/customers/{customer_id}/risk")
def get_customer_risk(customer_id: str) -> dict[str, Any]:
    with get_connection() as con:
        response = {}

        if table_exists(con, "customer_risk_scores"):
            customer_df = con.execute(
                """
                SELECT *
                FROM customer_risk_scores
                WHERE customer_id = ?;
                """,
                [customer_id],
            ).df()

            response["rule_based_customer_risk"] = (
                single_row_to_dict(customer_df) if not customer_df.empty else None
            )

        if table_exists(con, "ml_customer_anomaly_summary"):
            ml_df = con.execute(
                """
                SELECT *
                FROM ml_customer_anomaly_summary
                WHERE customer_id = ?;
                """,
                [customer_id],
            ).df()

            response["ml_customer_anomaly_summary"] = (
                single_row_to_dict(ml_df) if not ml_df.empty else None
            )

        if table_exists(con, "customer_explanation_summary"):
            explanation_df = con.execute(
                """
                SELECT *
                FROM customer_explanation_summary
                WHERE customer_id = ?;
                """,
                [customer_id],
            ).df()

            response["customer_explanation_summary"] = (
                single_row_to_dict(explanation_df) if not explanation_df.empty else None
            )

        if table_exists(con, "case_management_cases"):
            cases_df = con.execute(
                """
                SELECT case_id, case_source_type, case_priority, case_status, case_title,
                       risk_score, amount, created_at, sla_due_at, recommended_action
                FROM case_management_cases
                WHERE customer_id = ?
                ORDER BY priority_rank ASC, risk_score DESC
                LIMIT 25;
                """,
                [customer_id],
            ).df()

            response["cases"] = dataframe_to_records(cases_df)

    if not response:
        raise HTTPException(status_code=404, detail="Customer risk data not found")

    return response


@app.get("/alerts/explanations")
def get_alert_explanations(
    priority: Optional[str] = Query(None, example="P1"),
    limit: int = Query(25, ge=1, le=200),
) -> dict[str, Any]:
    with get_connection() as con:
        require_table(con, "alert_explanations")

        query = """
            SELECT explanation_id, explanation_priority, review_queue, main_trigger,
                   combined_explanation_score, transaction_id, customer_id, full_name,
                   amount, plain_english_explanation, recommended_investigation_action
            FROM alert_explanations
            WHERE 1 = 1
        """

        params = []

        if priority:
            query += " AND explanation_priority = ?"
            params.append(priority)

        query += f"""
            ORDER BY combined_explanation_score DESC
            LIMIT {limit};
        """

        df = con.execute(query, params).df()

    return {
        "count": len(df),
        "alert_explanations": dataframe_to_records(df),
    }


@app.get("/reconciliation/breaks")
def get_reconciliation_breaks(
    severity: Optional[str] = Query(None, example="High"),
    limit: int = Query(25, ge=1, le=200),
) -> dict[str, Any]:
    with get_connection() as con:
        require_table(con, "reconciliation_breaks")

        query = """
            SELECT *
            FROM reconciliation_breaks
            WHERE 1 = 1
        """

        params = []

        if severity:
            query += " AND severity = ?"
            params.append(severity)

        query += f"""
            ORDER BY
                CASE severity
                    WHEN 'High' THEN 1
                    WHEN 'Medium' THEN 2
                    WHEN 'Low' THEN 3
                    ELSE 9
                END,
                absolute_amount_difference DESC
            LIMIT {limit};
        """

        df = con.execute(query, params).df()

    return {
        "count": len(df),
        "reconciliation_breaks": dataframe_to_records(df),
    }


@app.get("/graph/entities")
def get_graph_entities(
    node_type: Optional[str] = Query(None, example="Customer"),
    limit: int = Query(25, ge=1, le=200),
) -> dict[str, Any]:
    with get_connection() as con:
        require_table(con, "graph_high_centrality_entities")

        query = """
            SELECT *
            FROM graph_high_centrality_entities
            WHERE 1 = 1
        """

        params = []

        if node_type:
            query += " AND node_type = ?"
            params.append(node_type)

        query += f"""
            ORDER BY graph_priority_score DESC, node_risk_score DESC
            LIMIT {limit};
        """

        df = con.execute(query, params).df()

    return {
        "count": len(df),
        "graph_entities": dataframe_to_records(df),
    }


@app.get("/graph/transfer-patterns")
def get_transfer_patterns(
    pattern_type: Optional[str] = Query(None, example="RECIPROCAL_TRANSFERS"),
    limit: int = Query(25, ge=1, le=200),
) -> dict[str, Any]:
    with get_connection() as con:
        require_table(con, "graph_suspicious_transfer_patterns")

        query = """
            SELECT *
            FROM graph_suspicious_transfer_patterns
            WHERE 1 = 1
        """

        params = []

        if pattern_type:
            query += " AND pattern_type = ?"
            params.append(pattern_type)

        query += f"""
            ORDER BY pattern_risk_score DESC, total_amount DESC
            LIMIT {limit};
        """

        df = con.execute(query, params).df()

    return {
        "count": len(df),
        "transfer_patterns": dataframe_to_records(df),
    }


@app.post("/score-transaction")
def score_transaction(transaction: TransactionScoreRequest) -> dict[str, Any]:
    return score_transaction_rule_based(transaction)