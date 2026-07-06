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


def run_failure_count_query(con: duckdb.DuckDBPyConnection, query: str) -> int:
    result = con.execute(query).fetchone()[0]

    if result is None:
        return 0

    return int(result)


def determine_status(failure_count: int, severity: str, allowed_failures: int) -> str:
    if failure_count <= allowed_failures:
        return "PASS"

    if severity in ["Info", "Warning"]:
        return "WARN"

    return "FAIL"


def build_checks() -> list[dict]:
    return [
        {
            "check_id": "DQ001",
            "check_name": "customers_customer_id_not_missing",
            "table_name": "customers",
            "check_type": "completeness",
            "severity": "Critical",
            "allowed_failures": 0,
            "description": "Customer records must have a customer_id.",
            "query": """
                SELECT COUNT(*)
                FROM customers
                WHERE customer_id IS NULL OR customer_id = '';
            """,
            "recommended_action": "Investigate customer records with missing IDs before loading downstream tables.",
        },
        {
            "check_id": "DQ002",
            "check_name": "customers_customer_id_unique",
            "table_name": "customers",
            "check_type": "uniqueness",
            "severity": "Critical",
            "allowed_failures": 0,
            "description": "customer_id must be unique.",
            "query": """
                SELECT COUNT(*)
                FROM (
                    SELECT customer_id
                    FROM customers
                    GROUP BY customer_id
                    HAVING COUNT(*) > 1
                );
            """,
            "recommended_action": "Deduplicate customer master records.",
        },
        {
            "check_id": "DQ003",
            "check_name": "merchants_merchant_id_unique",
            "table_name": "merchants",
            "check_type": "uniqueness",
            "severity": "Critical",
            "allowed_failures": 0,
            "description": "merchant_id must be unique.",
            "query": """
                SELECT COUNT(*)
                FROM (
                    SELECT merchant_id
                    FROM merchants
                    GROUP BY merchant_id
                    HAVING COUNT(*) > 1
                );
            """,
            "recommended_action": "Deduplicate merchant master records.",
        },
        {
            "check_id": "DQ004",
            "check_name": "accounts_account_id_unique",
            "table_name": "accounts",
            "check_type": "uniqueness",
            "severity": "Critical",
            "allowed_failures": 0,
            "description": "account_id must be unique.",
            "query": """
                SELECT COUNT(*)
                FROM (
                    SELECT account_id
                    FROM accounts
                    GROUP BY account_id
                    HAVING COUNT(*) > 1
                );
            """,
            "recommended_action": "Investigate duplicate account records.",
        },
        {
            "check_id": "DQ005",
            "check_name": "transactions_transaction_id_unique",
            "table_name": "transactions",
            "check_type": "uniqueness",
            "severity": "Critical",
            "allowed_failures": 0,
            "description": "transaction_id must be unique in the transaction table.",
            "query": """
                SELECT COUNT(*)
                FROM (
                    SELECT transaction_id
                    FROM transactions
                    GROUP BY transaction_id
                    HAVING COUNT(*) > 1
                );
            """,
            "recommended_action": "Deduplicate transaction records before scoring risk.",
        },
        {
            "check_id": "DQ006",
            "check_name": "transactions_required_fields_not_missing",
            "table_name": "transactions",
            "check_type": "completeness",
            "severity": "Critical",
            "allowed_failures": 0,
            "description": "Core transaction fields must not be missing.",
            "query": """
                SELECT COUNT(*)
                FROM transactions
                WHERE transaction_id IS NULL
                   OR customer_id IS NULL
                   OR account_id IS NULL
                   OR merchant_id IS NULL
                   OR amount IS NULL
                   OR transaction_timestamp IS NULL;
            """,
            "recommended_action": "Fix missing transaction identifiers or core financial fields.",
        },
        {
            "check_id": "DQ007",
            "check_name": "transactions_no_negative_amounts",
            "table_name": "transactions",
            "check_type": "validity",
            "severity": "Critical",
            "allowed_failures": 0,
            "description": "Transaction amounts should not be negative.",
            "query": """
                SELECT COUNT(*)
                FROM transactions
                WHERE amount < 0;
            """,
            "recommended_action": "Investigate negative transaction amounts and confirm refund logic if applicable.",
        },
        {
            "check_id": "DQ008",
            "check_name": "transactions_valid_currency",
            "table_name": "transactions",
            "check_type": "validity",
            "severity": "High",
            "allowed_failures": 0,
            "description": "Transaction currency must be one of GBP, EUR or USD.",
            "query": """
                SELECT COUNT(*)
                FROM transactions
                WHERE currency NOT IN ('GBP', 'EUR', 'USD');
            """,
            "recommended_action": "Review currency mapping and source-system currency codes.",
        },
        {
            "check_id": "DQ009",
            "check_name": "transactions_valid_status",
            "table_name": "transactions",
            "check_type": "validity",
            "severity": "High",
            "allowed_failures": 0,
            "description": "Transaction status must be from the accepted status list.",
            "query": """
                SELECT COUNT(*)
                FROM transactions
                WHERE status NOT IN ('Completed', 'Pending', 'Failed', 'Reversed');
            """,
            "recommended_action": "Review transaction lifecycle status mapping.",
        },
        {
            "check_id": "DQ010",
            "check_name": "transactions_valid_customer_reference",
            "table_name": "transactions",
            "check_type": "referential_integrity",
            "severity": "Critical",
            "allowed_failures": 0,
            "description": "Every transaction customer_id must exist in customers.",
            "query": """
                SELECT COUNT(*)
                FROM transactions t
                LEFT JOIN customers c
                    ON t.customer_id = c.customer_id
                WHERE c.customer_id IS NULL;
            """,
            "recommended_action": "Investigate orphan transaction customer references.",
        },
        {
            "check_id": "DQ011",
            "check_name": "transactions_valid_account_reference",
            "table_name": "transactions",
            "check_type": "referential_integrity",
            "severity": "Critical",
            "allowed_failures": 0,
            "description": "Every transaction account_id must exist in accounts.",
            "query": """
                SELECT COUNT(*)
                FROM transactions t
                LEFT JOIN accounts a
                    ON t.account_id = a.account_id
                WHERE a.account_id IS NULL;
            """,
            "recommended_action": "Investigate orphan transaction account references.",
        },
        {
            "check_id": "DQ012",
            "check_name": "transactions_valid_merchant_reference",
            "table_name": "transactions",
            "check_type": "referential_integrity",
            "severity": "Critical",
            "allowed_failures": 0,
            "description": "Every transaction merchant_id must exist in merchants.",
            "query": """
                SELECT COUNT(*)
                FROM transactions t
                LEFT JOIN merchants m
                    ON t.merchant_id = m.merchant_id
                WHERE m.merchant_id IS NULL;
            """,
            "recommended_action": "Investigate orphan transaction merchant references.",
        },
        {
            "check_id": "DQ013",
            "check_name": "accounts_valid_customer_reference",
            "table_name": "accounts",
            "check_type": "referential_integrity",
            "severity": "Critical",
            "allowed_failures": 0,
            "description": "Every account customer_id must exist in customers.",
            "query": """
                SELECT COUNT(*)
                FROM accounts a
                LEFT JOIN customers c
                    ON a.customer_id = c.customer_id
                WHERE c.customer_id IS NULL;
            """,
            "recommended_action": "Investigate account records linked to missing customers.",
        },
        {
            "check_id": "DQ014",
            "check_name": "account_transfers_valid_source_account",
            "table_name": "account_transfers",
            "check_type": "referential_integrity",
            "severity": "Critical",
            "allowed_failures": 0,
            "description": "Every transfer source account must exist in accounts.",
            "query": """
                SELECT COUNT(*)
                FROM account_transfers t
                LEFT JOIN accounts a
                    ON t.source_account_id = a.account_id
                WHERE a.account_id IS NULL;
            """,
            "recommended_action": "Investigate invalid source account references in transfers.",
        },
        {
            "check_id": "DQ015",
            "check_name": "account_transfers_valid_destination_account",
            "table_name": "account_transfers",
            "check_type": "referential_integrity",
            "severity": "Critical",
            "allowed_failures": 0,
            "description": "Every transfer destination account must exist in accounts.",
            "query": """
                SELECT COUNT(*)
                FROM account_transfers t
                LEFT JOIN accounts a
                    ON t.destination_account_id = a.account_id
                WHERE a.account_id IS NULL;
            """,
            "recommended_action": "Investigate invalid destination account references in transfers.",
        },
        {
            "check_id": "DQ016",
            "check_name": "account_transfers_no_same_source_destination",
            "table_name": "account_transfers",
            "check_type": "validity",
            "severity": "High",
            "allowed_failures": 0,
            "description": "Source and destination account should not be the same.",
            "query": """
                SELECT COUNT(*)
                FROM account_transfers
                WHERE source_account_id = destination_account_id;
            """,
            "recommended_action": "Review transfer records where source and destination are identical.",
        },
        {
            "check_id": "DQ017",
            "check_name": "watchlist_entity_reference_valid",
            "table_name": "watchlist",
            "check_type": "referential_integrity",
            "severity": "High",
            "allowed_failures": 0,
            "description": "Watchlist entities should match either a customer or a merchant.",
            "query": """
                SELECT COUNT(*)
                FROM watchlist w
                LEFT JOIN customers c
                    ON w.entity_id = c.customer_id
                LEFT JOIN merchants m
                    ON w.entity_id = m.merchant_id
                WHERE c.customer_id IS NULL
                  AND m.merchant_id IS NULL;
            """,
            "recommended_action": "Review dummy watchlist records with no matching customer or merchant.",
        },
        {
            "check_id": "DQ018",
            "check_name": "reconciliation_file_a_no_negative_amounts",
            "table_name": "reconciliation_file_a",
            "check_type": "validity",
            "severity": "Critical",
            "allowed_failures": 0,
            "description": "Reconciliation File A should not contain negative amounts.",
            "query": """
                SELECT COUNT(*)
                FROM reconciliation_file_a
                WHERE amount < 0;
            """,
            "recommended_action": "Investigate negative values in reconciliation File A.",
        },
        {
            "check_id": "DQ019",
            "check_name": "reconciliation_file_b_no_negative_amounts",
            "table_name": "reconciliation_file_b",
            "check_type": "validity",
            "severity": "Critical",
            "allowed_failures": 0,
            "description": "Reconciliation File B should not contain negative amounts.",
            "query": """
                SELECT COUNT(*)
                FROM reconciliation_file_b
                WHERE amount < 0;
            """,
            "recommended_action": "Investigate negative values in reconciliation File B.",
        },
        {
            "check_id": "DQ020",
            "check_name": "reconciliation_file_b_duplicate_transaction_ids_warning",
            "table_name": "reconciliation_file_b",
            "check_type": "controlled_break_detection",
            "severity": "Warning",
            "allowed_failures": 0,
            "description": "Duplicate transaction IDs in File B are expected controlled reconciliation breaks.",
            "query": """
                SELECT COUNT(*)
                FROM (
                    SELECT transaction_id
                    FROM reconciliation_file_b
                    GROUP BY transaction_id
                    HAVING COUNT(*) > 1
                );
            """,
            "recommended_action": "Route duplicate transaction IDs into reconciliation break review.",
        },
        {
            "check_id": "DQ021",
            "check_name": "suspicious_label_binary",
            "table_name": "transactions",
            "check_type": "validity",
            "severity": "High",
            "allowed_failures": 0,
            "description": "suspicious_label must be either 0 or 1.",
            "query": """
                SELECT COUNT(*)
                FROM transactions
                WHERE suspicious_label NOT IN (0, 1);
            """,
            "recommended_action": "Review target label generation logic.",
        },
        {
            "check_id": "DQ022",
            "check_name": "transaction_risk_flags_binary",
            "table_name": "transactions",
            "check_type": "validity",
            "severity": "High",
            "allowed_failures": 0,
            "description": "Risk flags must be binary.",
            "query": """
                SELECT COUNT(*)
                FROM transactions
                WHERE cross_border_flag NOT IN (0, 1)
                   OR high_amount_flag NOT IN (0, 1)
                   OR unusual_hour_flag NOT IN (0, 1)
                   OR high_risk_category_flag NOT IN (0, 1)
                   OR high_risk_country_flag NOT IN (0, 1)
                   OR kyc_issue_flag NOT IN (0, 1)
                   OR pep_flag NOT IN (0, 1);
            """,
            "recommended_action": "Review risk flag generation logic.",
        },
    ]


def run_checks(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    checks = build_checks()
    results = []

    run_timestamp = datetime.now().isoformat(timespec="seconds")

    for check in checks:
        try:
            failure_count = run_failure_count_query(con, check["query"])
            status = determine_status(
                failure_count=failure_count,
                severity=check["severity"],
                allowed_failures=check["allowed_failures"],
            )
            error_message = ""
        except Exception as exc:
            failure_count = -1
            status = "ERROR"
            error_message = str(exc)

        results.append(
            {
                "run_timestamp": run_timestamp,
                "check_id": check["check_id"],
                "check_name": check["check_name"],
                "table_name": check["table_name"],
                "check_type": check["check_type"],
                "severity": check["severity"],
                "description": check["description"],
                "failure_count": failure_count,
                "allowed_failures": check["allowed_failures"],
                "status": status,
                "recommended_action": check["recommended_action"],
                "error_message": error_message,
            }
        )

    return pd.DataFrame(results)


def add_optional_reconciliation_checks(
    con: duckdb.DuckDBPyConnection,
    results_df: pd.DataFrame,
) -> pd.DataFrame:
    if not table_exists(con, "reconciliation_results"):
        return results_df

    optional_checks = []

    run_timestamp = datetime.now().isoformat(timespec="seconds")

    optional_query = """
        SELECT COUNT(*)
        FROM reconciliation_results
        WHERE reconciliation_status NOT IN ('Matched', 'Break');
    """

    failure_count = run_failure_count_query(con, optional_query)

    optional_checks.append(
        {
            "run_timestamp": run_timestamp,
            "check_id": "DQ023",
            "check_name": "reconciliation_status_valid",
            "table_name": "reconciliation_results",
            "check_type": "validity",
            "severity": "High",
            "description": "Reconciliation status must be either Matched or Break.",
            "failure_count": failure_count,
            "allowed_failures": 0,
            "status": determine_status(failure_count, "High", 0),
            "recommended_action": "Review reconciliation status assignment logic.",
            "error_message": "",
        }
    )

    optional_query = """
        SELECT COUNT(*)
        FROM reconciliation_breaks
        WHERE case_id IS NULL
           OR break_type IS NULL
           OR severity IS NULL
           OR case_status IS NULL;
    """

    failure_count = run_failure_count_query(con, optional_query)

    optional_checks.append(
        {
            "run_timestamp": run_timestamp,
            "check_id": "DQ024",
            "check_name": "reconciliation_break_cases_required_fields",
            "table_name": "reconciliation_breaks",
            "check_type": "completeness",
            "severity": "Critical",
            "description": "Reconciliation break cases must have case ID, break type, severity and case status.",
            "failure_count": failure_count,
            "allowed_failures": 0,
            "status": determine_status(failure_count, "Critical", 0),
            "recommended_action": "Review case creation logic in the reconciliation engine.",
            "error_message": "",
        }
    )

    optional_df = pd.DataFrame(optional_checks)

    return pd.concat([results_df, optional_df], ignore_index=True)


def save_results(con: duckdb.DuckDBPyConnection, results_df: pd.DataFrame) -> None:
    results_path = REPORTS_DIR / "stage4_data_quality_results.csv"
    failed_path = REPORTS_DIR / "stage4_failed_data_quality_checks.csv"
    summary_path = REPORTS_DIR / "stage4_data_quality_summary.json"

    results_df.to_csv(results_path, index=False)

    failed_or_warning_df = results_df[results_df["status"].isin(["WARN", "FAIL", "ERROR"])]
    failed_or_warning_df.to_csv(failed_path, index=False)

    summary = {
        "run_timestamp": datetime.now().isoformat(timespec="seconds"),
        "total_checks": int(len(results_df)),
        "passed_checks": int((results_df["status"] == "PASS").sum()),
        "warning_checks": int((results_df["status"] == "WARN").sum()),
        "failed_checks": int((results_df["status"] == "FAIL").sum()),
        "error_checks": int((results_df["status"] == "ERROR").sum()),
        "critical_checks": int((results_df["severity"] == "Critical").sum()),
        "high_severity_checks": int((results_df["severity"] == "High").sum()),
        "warning_severity_checks": int((results_df["severity"] == "Warning").sum()),
    }

    summary_path.write_text(json.dumps(summary, indent=4))

    con.register("data_quality_results_df", results_df)

    con.execute(
        """
        CREATE OR REPLACE TABLE data_quality_results AS
        SELECT *
        FROM data_quality_results_df;
        """
    )

    con.execute(
        """
        CREATE OR REPLACE VIEW vw_data_quality_summary AS
        SELECT
            status,
            severity,
            check_type,
            COUNT(*) AS check_count,
            SUM(CASE WHEN failure_count > 0 THEN failure_count ELSE 0 END) AS total_failure_count
        FROM data_quality_results
        GROUP BY status, severity, check_type
        ORDER BY status, severity, check_type;
        """
    )

    print(f"Saved {results_path}")
    print(f"Saved {failed_path}")
    print(f"Saved {summary_path}")
    print("Saved data_quality_results table and vw_data_quality_summary view to DuckDB")


def print_console_summary(results_df: pd.DataFrame) -> None:
    print("\nData Quality Result Summary")
    print("---------------------------")
    print(results_df["status"].value_counts().to_string())

    warnings_or_failures = results_df[results_df["status"].isin(["WARN", "FAIL", "ERROR"])]

    if not warnings_or_failures.empty:
        print("\nWarnings / Failures / Errors")
        print("----------------------------")
        print(
            warnings_or_failures[
                [
                    "check_id",
                    "check_name",
                    "table_name",
                    "severity",
                    "failure_count",
                    "status",
                ]
            ].to_string(index=False)
        )


def main() -> None:
    check_database_exists()

    print(f"Running Stage 4 data quality checks against: {DB_PATH}")

    with duckdb.connect(str(DB_PATH)) as con:
        results_df = run_checks(con)
        results_df = add_optional_reconciliation_checks(con, results_df)
        save_results(con, results_df)
        print_console_summary(results_df)

    print("\nStage 4 data quality checks completed successfully")


if __name__ == "__main__":
    main()