from pathlib import Path
import json

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


def join_unique_values(values: pd.Series) -> str:
    clean_values = values.dropna().astype(str).unique().tolist()
    return "; ".join(sorted(clean_values))


def load_reconciliation_tables(con: duckdb.DuckDBPyConnection) -> tuple[pd.DataFrame, pd.DataFrame]:
    file_a = con.execute("SELECT * FROM reconciliation_file_a").df()
    file_b = con.execute("SELECT * FROM reconciliation_file_b").df()

    print(f"Loaded reconciliation_file_a: {len(file_a):,} rows")
    print(f"Loaded reconciliation_file_b: {len(file_b):,} rows")

    return file_a, file_b


def aggregate_reconciliation_file(df: pd.DataFrame, prefix: str) -> pd.DataFrame:
    df = df.copy()

    df["booking_date"] = pd.to_datetime(df["booking_date"]).dt.date.astype(str)

    aggregated = (
        df.groupby("transaction_id", dropna=False)
        .agg(
            **{
                f"{prefix}_record_count": ("transaction_id", "size"),
                f"{prefix}_recon_references": ("recon_reference", join_unique_values),
                f"{prefix}_source_systems": ("source_system", join_unique_values),
                f"{prefix}_account_id": ("account_id", "first"),
                f"{prefix}_booking_date": ("booking_date", "first"),
                f"{prefix}_amount": ("amount", "first"),
                f"{prefix}_currency": ("currency", "first"),
                f"{prefix}_status": ("status", "first"),
            }
        )
        .reset_index()
    )

    return aggregated


def classify_break(row: pd.Series) -> str:
    reasons = []

    if row["a_record_count"] == 0:
        return "MISSING_IN_A"

    if row["b_record_count"] == 0:
        return "MISSING_IN_B"

    if row["a_record_count"] > 1:
        reasons.append("DUPLICATE_IN_A")

    if row["b_record_count"] > 1:
        reasons.append("DUPLICATE_IN_B")

    if pd.notna(row["amount_difference"]) and abs(row["amount_difference"]) > 0.01:
        reasons.append("AMOUNT_MISMATCH")

    if row["a_booking_date"] != row["b_booking_date"]:
        reasons.append("DATE_MISMATCH")

    if row["a_currency"] != row["b_currency"]:
        reasons.append("CURRENCY_MISMATCH")

    if row["a_account_id"] != row["b_account_id"]:
        reasons.append("ACCOUNT_MISMATCH")

    if row["a_status"] != row["b_status"]:
        reasons.append("STATUS_MISMATCH")

    if not reasons:
        return "MATCHED"

    return " | ".join(reasons)


def get_primary_break_category(break_type: str) -> str:
    if break_type == "MATCHED":
        return "MATCHED"

    return break_type.split(" | ")[0]


def assign_severity(row: pd.Series) -> str:
    break_type = row["break_type"]
    amount_difference = abs(row["amount_difference"]) if pd.notna(row["amount_difference"]) else 0

    if break_type == "MATCHED":
        return "No Break"

    if "MISSING" in break_type:
        return "High"

    if "DUPLICATE" in break_type:
        return "High"

    if "AMOUNT_MISMATCH" in break_type and amount_difference >= 50:
        return "High"

    if "AMOUNT_MISMATCH" in break_type:
        return "Medium"

    if "DATE_MISMATCH" in break_type:
        return "Medium"

    return "Low"


def build_reconciliation_results(file_a: pd.DataFrame, file_b: pd.DataFrame) -> pd.DataFrame:
    a_agg = aggregate_reconciliation_file(file_a, "a")
    b_agg = aggregate_reconciliation_file(file_b, "b")

    results = a_agg.merge(
        b_agg,
        on="transaction_id",
        how="outer",
    )

    for column in ["a_record_count", "b_record_count"]:
        results[column] = results[column].fillna(0).astype(int)

    results["amount_difference"] = results["b_amount"] - results["a_amount"]

    results["absolute_amount_difference"] = results["amount_difference"].abs()

    results["break_type"] = results.apply(classify_break, axis=1)

    results["primary_break_category"] = results["break_type"].apply(
        get_primary_break_category
    )

    results["is_break"] = (results["break_type"] != "MATCHED").astype(int)

    results["severity"] = results.apply(assign_severity, axis=1)

    results["reconciliation_status"] = results["is_break"].map(
        {
            0: "Matched",
            1: "Break",
        }
    )

    date_for_age = results["a_booking_date"].combine_first(results["b_booking_date"])
    date_for_age = pd.to_datetime(date_for_age, errors="coerce")

    today = pd.Timestamp.today().normalize()

    results["case_age_days"] = (today - date_for_age).dt.days
    results["case_age_days"] = results["case_age_days"].fillna(0).astype(int)
    results.loc[results["case_age_days"] < 0, "case_age_days"] = 0

    results = results.sort_values(
        by=["is_break", "severity", "absolute_amount_difference"],
        ascending=[False, True, False],
    ).reset_index(drop=True)

    return results


def create_break_cases(results: pd.DataFrame) -> pd.DataFrame:
    breaks = results[results["is_break"] == 1].copy().reset_index(drop=True)

    breaks.insert(
        0,
        "case_id",
        [f"REC-CASE-{i + 1:06d}" for i in range(len(breaks))],
    )

    breaks["case_status"] = "Open"

    breaks["case_owner"] = breaks["severity"].map(
        {
            "High": "Senior Reconciliation Analyst",
            "Medium": "Reconciliation Analyst",
            "Low": "Operations Analyst",
        }
    )

    breaks["recommended_action"] = breaks["primary_break_category"].map(
        {
            "MISSING_IN_A": "Investigate record present in core banking file but missing from payment processor file.",
            "MISSING_IN_B": "Investigate record present in payment processor file but missing from core banking file.",
            "DUPLICATE_IN_A": "Review duplicate payment processor records and confirm whether duplicate posting occurred.",
            "DUPLICATE_IN_B": "Review duplicate core banking records and confirm whether duplicate posting occurred.",
            "AMOUNT_MISMATCH": "Compare source documents and investigate value difference.",
            "DATE_MISMATCH": "Check booking date, settlement date and posting delay.",
            "CURRENCY_MISMATCH": "Review currency mapping and FX handling.",
            "ACCOUNT_MISMATCH": "Check account mapping between systems.",
            "STATUS_MISMATCH": "Review transaction lifecycle status between systems.",
        }
    )

    breaks["recommended_action"] = breaks["recommended_action"].fillna(
        "Review reconciliation break and investigate source-system difference."
    )

    return breaks


def save_reports(results: pd.DataFrame, breaks: pd.DataFrame) -> None:
    full_results_path = REPORTS_DIR / "stage3_reconciliation_full_results.csv"
    breaks_path = REPORTS_DIR / "stage3_reconciliation_breaks.csv"
    break_type_summary_path = REPORTS_DIR / "stage3_break_type_summary.csv"
    summary_path = REPORTS_DIR / "stage3_reconciliation_summary.json"

    results.to_csv(full_results_path, index=False)
    breaks.to_csv(breaks_path, index=False)

    break_type_summary = (
        results.groupby(["primary_break_category", "severity", "reconciliation_status"])
        .size()
        .reset_index(name="record_count")
        .sort_values(by="record_count", ascending=False)
    )

    break_type_summary.to_csv(break_type_summary_path, index=False)

    summary = {
        "total_reconciliation_keys": int(len(results)),
        "matched_records": int((results["is_break"] == 0).sum()),
        "break_records": int((results["is_break"] == 1).sum()),
        "high_severity_breaks": int((breaks["severity"] == "High").sum()),
        "medium_severity_breaks": int((breaks["severity"] == "Medium").sum()),
        "low_severity_breaks": int((breaks["severity"] == "Low").sum()),
        "missing_in_a": int((results["primary_break_category"] == "MISSING_IN_A").sum()),
        "missing_in_b": int((results["primary_break_category"] == "MISSING_IN_B").sum()),
        "duplicates_in_b": int(results["break_type"].str.contains("DUPLICATE_IN_B").sum()),
        "amount_mismatches": int(results["break_type"].str.contains("AMOUNT_MISMATCH").sum()),
        "date_mismatches": int(results["break_type"].str.contains("DATE_MISMATCH").sum()),
    }

    summary_path.write_text(json.dumps(summary, indent=4))

    print(f"Saved {full_results_path}")
    print(f"Saved {breaks_path}")
    print(f"Saved {break_type_summary_path}")
    print(f"Saved {summary_path}")


def write_results_to_duckdb(
    con: duckdb.DuckDBPyConnection,
    results: pd.DataFrame,
    breaks: pd.DataFrame,
) -> None:
    con.register("reconciliation_results_df", results)
    con.register("reconciliation_breaks_df", breaks)

    con.execute(
        """
        CREATE OR REPLACE TABLE reconciliation_results AS
        SELECT *
        FROM reconciliation_results_df;
        """
    )

    con.execute(
        """
        CREATE OR REPLACE TABLE reconciliation_breaks AS
        SELECT *
        FROM reconciliation_breaks_df;
        """
    )

    con.execute(
        """
        CREATE OR REPLACE VIEW vw_reconciliation_break_summary AS
        SELECT
            primary_break_category,
            severity,
            COUNT(*) AS break_count,
            ROUND(SUM(COALESCE(absolute_amount_difference, 0)), 2) AS total_absolute_amount_difference,
            ROUND(AVG(case_age_days), 2) AS average_case_age_days
        FROM reconciliation_breaks
        GROUP BY primary_break_category, severity
        ORDER BY break_count DESC;
        """
    )

    print("Saved reconciliation_results and reconciliation_breaks tables to DuckDB")


def main() -> None:
    check_database_exists()

    with duckdb.connect(str(DB_PATH)) as con:
        file_a, file_b = load_reconciliation_tables(con)

        results = build_reconciliation_results(file_a, file_b)
        breaks = create_break_cases(results)

        write_results_to_duckdb(con, results, breaks)
        save_reports(results, breaks)

    print("Stage 3 reconciliation engine completed successfully")


if __name__ == "__main__":
    main()