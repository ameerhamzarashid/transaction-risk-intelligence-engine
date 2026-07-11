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

## Stage 5: Rule-Based Risk Scoring Engine

Stage 5 adds an explainable transaction and customer risk scoring layer.

The rule-based scoring engine uses transparent financial crime and operational risk indicators such as:

- watchlist matches
- PEP flags
- KYC issues
- high-risk countries
- high-risk merchant categories
- high-value transactions
- cross-border transactions
- unusual-hour activity
- sensitive merchant categories
- failed or reversed transaction statuses
- risky rule combinations

To run the rule-based scoring engine:

```powershell
python src\risk_scoring\run_rule_based_risk_scoring.py
```

Stage 5 creates these DuckDB objects:

- transaction_risk_scores table
- customer_risk_scores table
- transaction_risk_alerts table
- vw_transaction_risk_summary view
- vw_customer_risk_summary view

Stage 5 creates these reports:

- reports/stage5_transaction_risk_scores.csv
- reports/stage5_customer_risk_scores.csv
- reports/stage5_transaction_risk_alerts.csv
- reports/stage5_risk_scoring_summary.json

Each scored transaction includes:

- rule-based risk score
- risk band
- alert priority
- reason codes
- alert recommendation
- case owner

## Stage 6: Machine Learning Anomaly Detection

Stage 6 adds an unsupervised machine learning anomaly detection layer using Isolation Forest.

The model uses transaction, customer, merchant, channel and rule-based risk features to identify unusual transaction behaviour.

Features include:

- transaction amount
- transaction hour
- transaction day of week
- cross-border flag
- high-amount flag
- unusual-hour flag
- high-risk category flag
- high-risk country flag
- KYC issue flag
- PEP flag
- watchlist match flag
- rule-based risk score
- merchant category
- currency
- channel
- transaction type
- transaction status
- customer segment
- country risk level

To run the ML anomaly detector:

```powershell
python src\ml\run_anomaly_detection.py
```

Stage 6 creates these DuckDB objects:

- ml_transaction_anomaly_scores table
- ml_transaction_anomaly_alerts table
- ml_customer_anomaly_summary table
- vw_ml_anomaly_summary view
- vw_ml_vs_rule_summary view

Stage 6 creates these reports:

- reports/stage6_ml_transaction_anomaly_scores.csv
- reports/stage6_ml_transaction_anomaly_alerts.csv
- reports/stage6_ml_customer_anomaly_summary.csv
- reports/stage6_ml_anomaly_summary.json

Each ML-scored transaction includes:

- Isolation Forest anomaly score
- anomaly score percentile
- ML anomaly flag
- ML anomaly band
- ML alert priority
- ML reason codes
- comparison against rule-based risk scoring

## Stage 7 explainability analysis queries

-- 1. Explainability priority summary
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


-- 2. Top plain-English alert explanations
SELECT
    explanation_id,
    explanation_priority,
    review_queue,
    main_trigger,
    transaction_id,
    customer_id,
    full_name,
    amount,
    currency,
    combined_explanation_score,
    plain_english_explanation,
    recommended_investigation_action
FROM alert_explanations
ORDER BY combined_explanation_score DESC
LIMIT 25;


-- 3. Most common explanation reasons
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


-- 4. P1 critical explanations
SELECT
    explanation_id,
    transaction_id,
    customer_id,
    full_name,
    merchant_name,
    merchant_category,
    amount,
    currency,
    rule_based_risk_score,
    anomaly_score_percentile,
    reconciliation_break_type,
    combined_explanation_score,
    plain_english_explanation,
    recommended_investigation_action
FROM alert_explanations
WHERE explanation_priority = 'P1'
ORDER BY combined_explanation_score DESC;


-- 5. Rule + ML agreement explanations
SELECT
    explanation_id,
    transaction_id,
    customer_id,
    full_name,
    amount,
    rule_based_risk_score,
    anomaly_score_percentile,
    main_trigger,
    evidence_summary,
    plain_english_explanation
FROM alert_explanations
WHERE main_trigger LIKE '%Rule%ML%'
ORDER BY combined_explanation_score DESC;


-- 6. Reconciliation-linked explanations
SELECT
    explanation_id,
    transaction_id,
    customer_id,
    full_name,
    amount,
    reconciliation_case_id,
    reconciliation_break_type,
    reconciliation_severity,
    reconciliation_case_age_days,
    plain_english_explanation,
    recommended_investigation_action
FROM alert_explanations
WHERE reconciliation_case_id IS NOT NULL
  AND reconciliation_case_id <> ''
ORDER BY combined_explanation_score DESC;


-- 7. Customer explanation summary
SELECT
    customer_id,
    full_name,
    alert_explanation_count,
    p1_alerts,
    p2_alerts,
    p3_alerts,
    max_combined_explanation_score,
    average_combined_explanation_score,
    total_alert_amount,
    customer_explanation_priority
FROM customer_explanation_summary
ORDER BY max_combined_explanation_score DESC, alert_explanation_count DESC
LIMIT 25;


-- 8. Dashboard-ready explainability priority summary
SELECT *
FROM vw_explainability_priority_summary;


-- 9. Dashboard-ready top explanation reasons
SELECT *
FROM vw_top_explanation_reasons;

## Stage 8: Graph Analytics

Stage 8 adds graph analytics using NetworkX to identify connected entities, risky clusters and suspicious transfer patterns.

The graph represents relationships between:

- customers
- accounts
- merchants
- account-to-account transfers

The graph analytics layer detects:

- high-risk connected components
- high-centrality entities
- high-risk customers/accounts/merchants
- reciprocal transfer patterns
- high outbound transfer hubs
- high inbound collection hubs
- watchlist-linked graph clusters

To run the graph analytics layer:

```powershell
python src\graph\run_graph_analytics.py
```

Stage 8 creates these DuckDB objects:

- graph_nodes table
- graph_edges table
- graph_risk_clusters table
- graph_suspicious_transfer_patterns table
- graph_high_centrality_entities table
- vw_graph_entity_risk_summary view
- vw_graph_cluster_summary view

Stage 8 creates these reports:

- reports/stage8_graph_nodes.csv
- reports/stage8_graph_edges.csv
- reports/stage8_graph_risk_clusters.csv
- reports/stage8_suspicious_transfer_patterns.csv
- reports/stage8_high_centrality_entities.csv
- reports/stage8_graph_analytics_summary.json

Each graph entity includes:

- node type
- risk score
- risk band
- degree centrality
- PageRank score
- graph priority score
- watchlist flag
- transaction and alert counts

## Stage 9: Alert Case Management

Stage 9 creates a unified case-management layer across reconciliation, rule-based risk scoring, ML anomaly detection, explainability and graph analytics.

The case-management layer combines alerts from:

- reconciliation breaks
- rule-based transaction risk alerts
- ML anomaly alerts
- explainability alerts
- high-centrality graph entities
- suspicious transfer patterns
- graph risk clusters

To run the case-management layer:

```powershell
python src\case_management\run_case_management.py
```

Stage 9 creates these DuckDB objects:

- case_management_cases table
- case_management_summary table
- case_management_work_queue table
- vw_case_management_priority_summary view
- vw_case_management_source_summary view
- vw_case_management_owner_queue view

Stage 9 creates these reports:

- reports/stage9_case_management_cases.csv
- reports/stage9_case_management_summary.csv
- reports/stage9_case_management_work_queue.csv
- reports/stage9_case_management_summary.json

Each case includes:

- case ID
- source type
- source record ID
- priority
- status
- owner
- SLA due time
- SLA status
- age bucket
- customer, account, merchant and transaction references
- risk score
- case description
- recommended action

## Stage 10: FastAPI Service Layer

Stage 10 adds a FastAPI service layer so the transaction risk engine can be accessed through API endpoints.

The API exposes project outputs from:

- transaction risk scoring
- customer risk scoring
- ML anomaly detection
- reconciliation breaks
- graph analytics
- explainability alerts
- case management work queues

To run the API:

```powershell
uvicorn api.main:app --reload
```

Then open:

```text
http://127.0.0.1:8000/docs
```

Main API endpoints include:

- GET /health
- GET /database/tables
- GET /summary/cases
- GET /summary/risk
- GET /cases
- GET /cases/{case_id}
- GET /work-queue
- GET /transactions/{transaction_id}
- GET /customers/{customer_id}/risk
- GET /alerts/explanations
- GET /reconciliation/breaks
- GET /graph/entities
- GET /graph/transfer-patterns
- POST /score-transaction

The POST /score-transaction endpoint scores a new transaction using the rule-based risk logic and returns:

- rule-based risk score
- risk band
- alert priority
- alert decision
- reason codes

## Stage 11: Streamlit Dashboard

Stage 11 adds a Streamlit dashboard for exploring the transaction risk engine outputs.

The dashboard includes:

- executive overview
- case-management work queue
- rule-based transaction risk
- ML anomaly detection
- reconciliation breaks
- graph analytics
- explainability alerts
- customer and transaction lookup
- new transaction scoring form

To run the dashboard:

```powershell
streamlit run dashboards\streamlit_app.py
```

Then open:

```text
http://localhost:8501
```

The dashboard reads from the local DuckDB database created by the earlier pipeline stages.

Dashboard files:

- dashboards/streamlit_app.py
- dashboards/README.md

## Stage 12: Docker and Final Project Polish

Stage 12 adds Docker support, a full pipeline runner and final project documentation.

To run the full pipeline locally:

```powershell
python scripts\run_full_pipeline.py
```

To build the Docker image:

```powershell
docker build -t transaction-risk-intelligence-engine .
```

To run the full pipeline inside Docker:

```powershell
docker run --rm transaction-risk-intelligence-engine
```

To run the API and dashboard with Docker Compose:

```powershell
docker compose up --build
```

Then open:

```text
http://127.0.0.1:8000/docs
```

for the FastAPI service, and:

```text
http://127.0.0.1:8501
```

for the Streamlit dashboard.

Stage 12 adds:

- scripts/run_full_pipeline.py
- Dockerfile
- docker-compose.yml
- .dockerignore
- docs/PROJECT_OVERVIEW.md