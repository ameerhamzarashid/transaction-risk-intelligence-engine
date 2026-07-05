from pathlib import Path
import json

import duckdb
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]

SYNTHETIC_DIR = BASE_DIR / "data" / "synthetic"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
REPORTS_DIR = BASE_DIR / "reports"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = PROCESSED_DIR / "transaction_risk.duckdb"


DATASETS = {
    "customers": "customers.csv",
    "merchants": "merchants.csv",
    "accounts": "accounts.csv",
    "transactions": "transactions.csv",
    "account_transfers": "account_transfers.csv",
    "watchlist": "watchlist.csv",
    "reconciliation_file_a": "reconciliation_file_a.csv",
    "reconciliation_file_b": "reconciliation_file_b.csv",
}


def duckdb_path(path: Path) -> str:
    """
    DuckDB works better with forward slashes, even on Windows.
    """
    return path.resolve().as_posix()


def check_required_files() -> None:
    missing_files = []

    for filename in DATASETS.values():
        file_path = SYNTHETIC_DIR / filename
        if not file_path.exists():
            missing_files.append(str(file_path))

    if missing_files:
        raise FileNotFoundError(
            "Missing required synthetic data files:\n" + "\n".join(missing_files)
        )


def load_csv_tables(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    table_counts = []

    for table_name, filename in DATASETS.items():
        csv_path = SYNTHETIC_DIR / filename

        con.execute(
            f"""
            CREATE OR REPLACE TABLE {table_name} AS
            SELECT *
            FROM read_csv_auto('{duckdb_path(csv_path)}', HEADER=TRUE);
            """
        )

        row_count = con.execute(f"SELECT COUNT(*) FROM {table_name};").fetchone()[0]

        table_counts.append(
            {
                "table_name": table_name,
                "source_file": filename,
                "row_count": row_count,
            }
        )

        print(f"Loaded {table_name}: {row_count:,} rows")

    return pd.DataFrame(table_counts)


def create_database_views(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        CREATE OR REPLACE VIEW vw_transaction_enriched AS
        SELECT
            t.transaction_id,
            t.transaction_timestamp,
            t.customer_id,
            c.full_name,
            c.country AS customer_master_country,
            c.country_risk_level,
            c.customer_segment,
            c.kyc_status,
            c.pep_flag AS customer_master_pep_flag,
            t.account_id,
            a.account_type,
            a.account_status,
            t.merchant_id,
            m.merchant_name,
            t.merchant_category,
            m.merchant_country,
            m.merchant_country_risk_level,
            t.amount,
            t.currency,
            t.channel,
            t.transaction_type,
            t.status,
            t.cross_border_flag,
            t.high_amount_flag,
            t.unusual_hour_flag,
            t.high_risk_category_flag,
            t.high_risk_country_flag,
            t.kyc_issue_flag,
            t.pep_flag,
            CASE
                WHEN wc.entity_id IS NOT NULL OR wm.entity_id IS NOT NULL THEN 1
                ELSE 0
            END AS watchlist_match_flag,
            COALESCE(wc.watchlist_type, wm.watchlist_type) AS watchlist_type,
            COALESCE(wc.risk_reason, wm.risk_reason) AS watchlist_risk_reason,
            t.suspicious_label
        FROM transactions t
        LEFT JOIN customers c
            ON t.customer_id = c.customer_id
        LEFT JOIN accounts a
            ON t.account_id = a.account_id
        LEFT JOIN merchants m
            ON t.merchant_id = m.merchant_id
        LEFT JOIN watchlist wc
            ON t.customer_id = wc.entity_id
        LEFT JOIN watchlist wm
            ON t.merchant_id = wm.entity_id;
        """
    )

    con.execute(
        """
        CREATE OR REPLACE VIEW vw_daily_transaction_summary AS
        SELECT
            CAST(transaction_timestamp AS DATE) AS transaction_date,
            COUNT(*) AS transaction_count,
            ROUND(SUM(amount), 2) AS total_amount,
            ROUND(AVG(amount), 2) AS average_amount,
            SUM(suspicious_label) AS suspicious_transaction_count,
            SUM(watchlist_match_flag) AS watchlist_match_count
        FROM vw_transaction_enriched
        GROUP BY CAST(transaction_timestamp AS DATE)
        ORDER BY transaction_date;
        """
    )

    con.execute(
        """
        CREATE OR REPLACE VIEW vw_reconciliation_overview AS
        SELECT
            'file_a' AS file_name,
            COUNT(*) AS row_count,
            ROUND(SUM(amount), 2) AS total_amount
        FROM reconciliation_file_a

        UNION ALL

        SELECT
            'file_b' AS file_name,
            COUNT(*) AS row_count,
            ROUND(SUM(amount), 2) AS total_amount
        FROM reconciliation_file_b;
        """
    )

    print("Created database views")


def query_single_value(con: duckdb.DuckDBPyConnection, query: str):
    return con.execute(query).fetchone()[0]


def run_database_checks(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    checks = [
        {
            "check_name": "customers_have_no_missing_customer_id",
            "check_type": "data_quality",
            "result_value": query_single_value(
                con,
                """
                SELECT COUNT(*)
                FROM customers
                WHERE customer_id IS NULL OR customer_id = '';
                """,
            ),
            "expected_result": 0,
        },
        {
            "check_name": "transactions_have_no_missing_transaction_id",
            "check_type": "data_quality",
            "result_value": query_single_value(
                con,
                """
                SELECT COUNT(*)
                FROM transactions
                WHERE transaction_id IS NULL OR transaction_id = '';
                """,
            ),
            "expected_result": 0,
        },
        {
            "check_name": "transactions_have_no_negative_amounts",
            "check_type": "data_quality",
            "result_value": query_single_value(
                con,
                """
                SELECT COUNT(*)
                FROM transactions
                WHERE amount < 0;
                """,
            ),
            "expected_result": 0,
        },
        {
            "check_name": "transactions_have_no_duplicate_ids",
            "check_type": "data_quality",
            "result_value": query_single_value(
                con,
                """
                SELECT COUNT(*)
                FROM (
                    SELECT transaction_id
                    FROM transactions
                    GROUP BY transaction_id
                    HAVING COUNT(*) > 1
                );
                """,
            ),
            "expected_result": 0,
        },
        {
            "check_name": "transactions_have_valid_customer_references",
            "check_type": "referential_integrity",
            "result_value": query_single_value(
                con,
                """
                SELECT COUNT(*)
                FROM transactions t
                LEFT JOIN customers c
                    ON t.customer_id = c.customer_id
                WHERE c.customer_id IS NULL;
                """,
            ),
            "expected_result": 0,
        },
        {
            "check_name": "transactions_have_valid_merchant_references",
            "check_type": "referential_integrity",
            "result_value": query_single_value(
                con,
                """
                SELECT COUNT(*)
                FROM transactions t
                LEFT JOIN merchants m
                    ON t.merchant_id = m.merchant_id
                WHERE m.merchant_id IS NULL;
                """,
            ),
            "expected_result": 0,
        },
        {
            "check_name": "accounts_have_valid_customer_references",
            "check_type": "referential_integrity",
            "result_value": query_single_value(
                con,
                """
                SELECT COUNT(*)
                FROM accounts a
                LEFT JOIN customers c
                    ON a.customer_id = c.customer_id
                WHERE c.customer_id IS NULL;
                """,
            ),
            "expected_result": 0,
        },
        {
            "check_name": "enriched_transaction_view_row_count",
            "check_type": "reconciliation",
            "result_value": query_single_value(
                con,
                """
                SELECT COUNT(*)
                FROM vw_transaction_enriched;
                """,
            ),
            "expected_result": query_single_value(
                con,
                """
                SELECT COUNT(*)
                FROM transactions;
                """,
            ),
        },
    ]

    checks_df = pd.DataFrame(checks)

    checks_df["status"] = checks_df.apply(
        lambda row: "PASS"
        if row["result_value"] == row["expected_result"]
        else "FAIL",
        axis=1,
    )

    return checks_df


def save_database_summary(
    table_counts: pd.DataFrame,
    checks_df: pd.DataFrame,
    con: duckdb.DuckDBPyConnection,
) -> None:
    table_counts_path = REPORTS_DIR / "stage2_table_counts.csv"
    checks_path = REPORTS_DIR / "stage2_database_quality_checks.csv"
    summary_path = REPORTS_DIR / "stage2_database_summary.json"

    table_counts.to_csv(table_counts_path, index=False)
    checks_df.to_csv(checks_path, index=False)

    summary = {
        "database_path": str(DB_PATH),
        "table_count": len(table_counts),
        "total_loaded_rows": int(table_counts["row_count"].sum()),
        "quality_checks": len(checks_df),
        "passed_checks": int((checks_df["status"] == "PASS").sum()),
        "failed_checks": int((checks_df["status"] == "FAIL").sum()),
        "transaction_rows": int(
            query_single_value(con, "SELECT COUNT(*) FROM transactions;")
        ),
        "enriched_transaction_rows": int(
            query_single_value(con, "SELECT COUNT(*) FROM vw_transaction_enriched;")
        ),
        "suspicious_transactions": int(
            query_single_value(
                con,
                "SELECT SUM(suspicious_label) FROM vw_transaction_enriched;",
            )
        ),
        "watchlist_matched_transactions": int(
            query_single_value(
                con,
                "SELECT SUM(watchlist_match_flag) FROM vw_transaction_enriched;",
            )
        ),
    }

    summary_path.write_text(json.dumps(summary, indent=4))

    print(f"Saved {table_counts_path}")
    print(f"Saved {checks_path}")
    print(f"Saved {summary_path}")


def main() -> None:
    check_required_files()

    print(f"Building DuckDB database at: {DB_PATH}")

    with duckdb.connect(str(DB_PATH)) as con:
        table_counts = load_csv_tables(con)
        create_database_views(con)
        checks_df = run_database_checks(con)
        save_database_summary(table_counts, checks_df, con)

    print("Stage 2 database build completed successfully")


if __name__ == "__main__":
    main()