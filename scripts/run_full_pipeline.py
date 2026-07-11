from pathlib import Path
import subprocess
import sys


BASE_DIR = Path(__file__).resolve().parents[1]


PIPELINE_STEPS = [
    ("Stage 1 - Synthetic data generation", "src/data_generation/generate_synthetic_data.py"),
    ("Stage 2 - DuckDB database build", "src/database/build_duckdb_database.py"),
    ("Stage 3 - Reconciliation engine", "src/reconciliation/run_reconciliation.py"),
    ("Stage 4 - Data quality checks", "src/data_quality/run_data_quality_checks.py"),
    ("Stage 5 - Rule-based risk scoring", "src/risk_scoring/run_rule_based_risk_scoring.py"),
    ("Stage 6 - ML anomaly detection", "src/ml/run_anomaly_detection.py"),
    ("Stage 7 - Explainability layer", "src/explainability/run_explainability_layer.py"),
    ("Stage 8 - Graph analytics", "src/graph/run_graph_analytics.py"),
    ("Stage 9 - Case management", "src/case_management/run_case_management.py"),
]


def run_step(step_name: str, script_path: str) -> None:
    full_script_path = BASE_DIR / script_path

    if not full_script_path.exists():
        raise FileNotFoundError(f"Missing script: {full_script_path}")

    print("\n" + "=" * 80)
    print(f"Running {step_name}")
    print("=" * 80)

    result = subprocess.run(
        [sys.executable, str(full_script_path)],
        cwd=BASE_DIR,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(f"{step_name} failed with exit code {result.returncode}")


def main() -> None:
    print("Starting full Transaction Risk Intelligence Engine pipeline")

    for step_name, script_path in PIPELINE_STEPS:
        run_step(step_name, script_path)

    print("\n" + "=" * 80)
    print("Full pipeline completed successfully")
    print("=" * 80)


if __name__ == "__main__":
    main()