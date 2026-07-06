# Transaction Risk Intelligence Engine

A financial crime, reconciliation and transaction risk analytics project built with Python, SQL, anomaly detection, graph analytics and explainable machine learning.

## Project Objective

This project simulates a financial services transaction monitoring environment where transactions must be checked for:

- Fraud anomalies
- Suspicious customer or merchant behaviour
- Reconciliation breaks
- Duplicate or near-duplicate payments
- High-risk customer/entity clusters
- Watchlist matches
- Prioritised operational alerts

## Planned Tech Stack

- Python
- SQL
- DuckDB / PostgreSQL
- PySpark
- scikit-learn
- XGBoost
- NetworkX
- SHAP
- FastAPI
- Streamlit
- Docker
- GitHub

## Project Stages

1. Project setup and GitHub foundation
2. Synthetic financial data generation
3. Database layer
4. Reconciliation engine
5. Data quality checks
6. Rule-based risk scoring
7. Machine learning anomaly detection
8. Explainability
9. Graph analytics
10. Alert case management
11. FastAPI service
12. Dashboard
13. Docker and final documentation

## Current Stage

Stage 1: Synthetic financial data generation.

## Stage 0: Project Setup and GitHub Foundation

Stage 0 created the project repository, folder structure, starter files and initial GitHub commit.

Main folders include:

- data
- notebooks
- src
- sql
- reports
- dashboards
- api
- tests
- docs

## Stage 1: Synthetic Financial Data Generator

Stage 1 creates realistic synthetic datasets for transaction monitoring, reconciliation and financial crime analytics.

Generated datasets include:

- customers
- merchants
- accounts
- transactions
- account-to-account transfers
- dummy watchlist records
- reconciliation file A
- reconciliation file B

The data generator injects controlled risk patterns such as high-value payments, unusual-hour activity, cross-border transactions, high-risk merchant categories, watchlist entities and reconciliation breaks.

To regenerate the data, run:

```powershell
python src\data_generation\generate_synthetic_data.py
```

Outputs are saved in:

```text
data/synthetic/
```

## Generated Data Summary

| Dataset | Rows |
|---|---:|
| customers.csv | 1,000 |
| merchants.csv | 250 |
| accounts.csv | 1,300 |
| transactions.csv | 10,000 |
| account_transfers.csv | 2,500 |
| watchlist.csv | 20 |
| reconciliation_file_a.csv | 3,000 |
| reconciliation_file_b.csv | 2,990 |

## Why This Project Matters

This project demonstrates:

- financial transaction data understanding
- reconciliation and control thinking
- fraud and anomaly detection
- AML-style suspicious activity scoring
- graph analytics for linked entities
- explainable risk scoring
- production-style analytics engineering

## Stage 2: DuckDB Database Layer

Stage 2 loads the synthetic CSV files into a local DuckDB database and creates SQL views for analysis.

Created database objects include:

- customers table
- merchants table
- accounts table
- transactions table
- account_transfers table
- watchlist table
- reconciliation_file_a table
- reconciliation_file_b table
- vw_transaction_enriched view
- vw_daily_transaction_summary view
- vw_reconciliation_overview view

To build the database, run:

```powershell
python src\database\build_duckdb_database.py

## Stage 3: Reconciliation Engine 

Stage 3 compares two synthetic reconciliation files that represent records from two financial systems:

- Payment processor file
- Core banking file

The reconciliation engine detects and classifies:

- missing records in File A
- missing records in File B
- duplicate records
- amount mismatches
- date mismatches
- currency mismatches
- account mismatches
- status mismatches
- matched records

To run the reconciliation engine:

```powershell
python src\reconciliation\run_reconciliation.py

## Stage 4: Data Quality Checks

Stage 4 adds a data-quality validation layer using Python and DuckDB.

The checks cover:

- missing customer IDs
- missing transaction IDs
- duplicate customer, merchant, account and transaction IDs
- negative transaction amounts
- invalid currencies
- invalid transaction statuses
- invalid customer references
- invalid account references
- invalid merchant references
- invalid transfer account references
- invalid watchlist references
- reconciliation file quality issues
- controlled duplicate reconciliation records

To run the data quality checks:

```powershell
python src\data_quality\run_data_quality_checks.py
```

Stage 4 creates these DuckDB objects:

- data_quality_results table
- vw_data_quality_summary view

Stage 4 creates these reports:

- reports/stage4_data_quality_results.csv
- reports/stage4_failed_data_quality_checks.csv
- reports/stage4_data_quality_summary.json

The data quality layer gives each check a status:

- PASS
- WARN
- FAIL
- ERROR

Warnings are used for controlled issues such as deliberately injected duplicate reconciliation records.