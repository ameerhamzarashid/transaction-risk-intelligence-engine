# Transaction Risk Intelligence Engine

A production-style financial crime and transaction risk analytics project built with Python, SQL, DuckDB, machine learning, graph analytics, FastAPI, Streamlit and Docker.

This project simulates a financial services monitoring environment where transactions need to be checked for suspicious behaviour, reconciliation breaks, risky customer/entity patterns and operational alerts.

---

## Project Objective

The objective of this project is to build an end-to-end transaction risk intelligence system that can:

* generate realistic synthetic financial datasets
* detect reconciliation breaks between two financial systems
* validate data quality across customer, account, merchant and transaction records
* apply transparent rule-based financial crime risk scoring
* detect unusual behaviour using unsupervised machine learning
* explain alerts in plain English for analyst review
* identify risky connected entities using graph analytics
* create an operational case-management queue
* expose outputs through a FastAPI service
* provide an interactive Streamlit risk operations dashboard
* support reproducible local and Docker-based execution

---

## Business Problem

Financial services teams process large volumes of transactions across multiple systems. Some transactions may be suspicious, some records may not reconcile, and some customers, accounts or merchants may be linked through risky networks.

Operational teams need a way to prioritise the highest-risk cases, understand why alerts were generated, and review cases through a structured workflow.

This project addresses that problem by combining transaction monitoring, reconciliation, anomaly detection, graph analytics, explainability and case management in one integrated system.

---

## Main Capabilities

* Synthetic financial data generation
* DuckDB analytical database layer
* Reconciliation break detection
* Data quality validation
* Rule-based transaction risk scoring
* Customer-level risk scoring
* Isolation Forest anomaly detection
* Human-readable alert explanations
* NetworkX graph analytics
* Suspicious transfer pattern detection
* Unified case-management work queue
* FastAPI service layer
* Streamlit risk operations dashboard
* Docker and Docker Compose support

---

## Technology Stack

| Area             | Tools                          |
| ---------------- | ------------------------------ |
| Programming      | Python                         |
| Data Processing  | pandas, NumPy                  |
| Database         | DuckDB, SQL                    |
| Machine Learning | scikit-learn, Isolation Forest |
| Graph Analytics  | NetworkX                       |
| API              | FastAPI, Uvicorn               |
| Dashboard        | Streamlit, Plotly              |
| Deployment       | Docker, Docker Compose         |
| Version Control  | Git, GitHub                    |

---

## Project Architecture

```text
Synthetic Data Generation
        ↓
DuckDB Database Layer
        ↓
Data Quality Checks + Reconciliation Engine
        ↓
Rule-Based Risk Scoring
        ↓
ML Anomaly Detection
        ↓
Explainability Layer + Graph Analytics
        ↓
Unified Case Management
        ↓
FastAPI Service + Streamlit Dashboard
        ↓
Dockerised Local Execution
```

---

## Project Stages

### Stage 0: Project Setup and GitHub Foundation

Created the project repository, folder structure, starter files and GitHub connection.

Main folders:

* data
* notebooks
* src
* sql
* reports
* dashboards
* api
* tests
* docs
* scripts

---

### Stage 1: Synthetic Financial Data Generation

Created realistic synthetic datasets for transaction monitoring, reconciliation and financial crime analytics.

Generated datasets include:

* customers
* merchants
* accounts
* transactions
* account-to-account transfers
* watchlist records
* reconciliation file A
* reconciliation file B

The generator injects controlled risk patterns such as high-value payments, unusual-hour transactions, cross-border activity, high-risk merchant categories, dummy watchlist exposure and reconciliation breaks.

Run:

```powershell
python src\data_generation\generate_synthetic_data.py
```

Outputs:

```text
data/synthetic/
```

---

### Stage 2: DuckDB Database Layer

Loads the synthetic CSV files into a local DuckDB database and creates SQL views for analysis.

Created database objects include:

* customers table
* merchants table
* accounts table
* transactions table
* account_transfers table
* watchlist table
* reconciliation_file_a table
* reconciliation_file_b table
* vw_transaction_enriched view
* vw_daily_transaction_summary view
* vw_reconciliation_overview view

Run:

```powershell
python src\database\build_duckdb_database.py
```

Database output:

```text
data/processed/transaction_risk.duckdb
```

---

### Stage 3: Reconciliation Engine

Compares two synthetic reconciliation files representing records from two financial systems.

The reconciliation engine detects:

* missing records
* duplicate records
* amount mismatches
* date mismatches
* currency mismatches
* account mismatches
* status mismatches
* matched records

Run:

```powershell
python src\reconciliation\run_reconciliation.py
```

Outputs include:

* reconciliation_results table
* reconciliation_breaks table
* vw_reconciliation_break_summary view
* stage3 reconciliation reports

---

### Stage 4: Data Quality Validation

Adds a data-quality validation layer using Python and DuckDB.

Checks include:

* missing IDs
* duplicate IDs
* invalid references
* negative transaction amounts
* invalid statuses
* invalid currencies
* reconciliation file quality issues
* controlled duplicate reconciliation records

Run:

```powershell
python src\data_quality\run_data_quality_checks.py
```

Outputs include:

* data_quality_results table
* vw_data_quality_summary view
* stage4 data quality reports

---

### Stage 5: Rule-Based Risk Scoring

Adds transparent transaction and customer risk scoring.

Risk indicators include:

* watchlist matches
* PEP flags
* KYC issues
* high-risk countries
* high-risk merchant categories
* high-value transactions
* cross-border transactions
* unusual-hour activity
* failed or reversed transaction statuses
* risky rule combinations

Run:

```powershell
python src\risk_scoring\run_rule_based_risk_scoring.py
```

Outputs include:

* transaction_risk_scores table
* customer_risk_scores table
* transaction_risk_alerts table
* vw_transaction_risk_summary view
* vw_customer_risk_summary view

---

### Stage 6: Machine Learning Anomaly Detection

Adds unsupervised machine learning anomaly detection using Isolation Forest.

The model uses transaction, customer, merchant, channel and rule-based risk features to identify unusual transaction behaviour.

Run:

```powershell
python src\ml\run_anomaly_detection.py
```

Outputs include:

* ml_transaction_anomaly_scores table
* ml_transaction_anomaly_alerts table
* ml_customer_anomaly_summary table
* vw_ml_anomaly_summary view
* vw_ml_vs_rule_summary view

---

### Stage 7: Explainability Layer

Converts rule-based scores, ML anomaly outputs and reconciliation evidence into analyst-friendly explanations.

Each explanation includes:

* transaction ID
* customer details
* main trigger
* combined explanation score
* rule-based reason codes
* ML reason codes
* reconciliation evidence where available
* plain-English explanation
* recommended investigation action

Run:

```powershell
python src\explainability\run_explainability_layer.py
```

Outputs include:

* alert_explanations table
* explanation_reason_summary table
* customer_explanation_summary table
* vw_explainability_priority_summary view
* vw_top_explanation_reasons view

---

### Stage 8: Graph Analytics

Adds graph analytics using NetworkX to identify connected entities, risky clusters and suspicious transfer patterns.

The graph represents relationships between:

* customers
* accounts
* merchants
* account-to-account transfers

The graph analytics layer detects:

* high-risk connected components
* high-centrality entities
* risky customers, accounts and merchants
* reciprocal transfer patterns
* high outbound transfer hubs
* high inbound collection hubs
* watchlist-linked graph clusters

Run:

```powershell
python src\graph\run_graph_analytics.py
```

Outputs include:

* graph_nodes table
* graph_edges table
* graph_risk_clusters table
* graph_suspicious_transfer_patterns table
* graph_high_centrality_entities table
* vw_graph_entity_risk_summary view
* vw_graph_cluster_summary view

---

### Stage 9: Alert Case Management

Creates a unified case-management layer across reconciliation, rule-based risk scoring, ML anomaly detection, explainability and graph analytics.

The case-management layer combines alerts from:

* reconciliation breaks
* rule-based transaction risk alerts
* ML anomaly alerts
* explainability alerts
* high-centrality graph entities
* suspicious transfer patterns
* graph risk clusters

Run:

```powershell
python src\case_management\run_case_management.py
```

Outputs include:

* case_management_cases table
* case_management_summary table
* case_management_work_queue table
* vw_case_management_priority_summary view
* vw_case_management_source_summary view
* vw_case_management_owner_queue view

---

### Stage 10: FastAPI Service Layer

Adds an API layer so project outputs can be accessed through endpoints.

Run:

```powershell
uvicorn api.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

Main endpoints include:

* GET /health
* GET /database/tables
* GET /summary/cases
* GET /summary/risk
* GET /cases
* GET /cases/{case_id}
* GET /work-queue
* GET /transactions/{transaction_id}
* GET /customers/{customer_id}/risk
* GET /alerts/explanations
* GET /reconciliation/breaks
* GET /graph/entities
* GET /graph/transfer-patterns
* POST /score-transaction

---

### Stage 11: Streamlit Risk Operations Dashboard

Adds an interactive dashboard for exploring project outputs.

The dashboard includes:

* control room overview
* case-management work queue
* risk signal monitoring
* reconciliation controls
* network analytics
* investigation lookup
* transaction scoring form

Run:

```powershell
streamlit run dashboards\streamlit_app.py
```

Open:

```text
http://localhost:8501
```

The dashboard uses:

* professional risk-operations styling
* muted financial-services colour grading
* interactive Plotly charts
* searchable case-management queues
* analyst-style drill-downs
* downloadable filtered CSV outputs

---

### Stage 12: Docker and Final Project Polish

Adds Docker support, Docker Compose and a full pipeline runner.

Run the full pipeline locally:

```powershell
python scripts\run_full_pipeline.py
```

Build Docker image:

```powershell
docker build -t transaction-risk-intelligence-engine .
```

Run full pipeline inside Docker:

```powershell
docker run --rm transaction-risk-intelligence-engine
```

Run API and dashboard using Docker Compose:

```powershell
docker compose up --build
```

Then open:

```text
http://127.0.0.1:8000/docs
```

for the API, and:

```text
http://127.0.0.1:8501
```

for the dashboard.

---

## Generated Reports

The project generates CSV and JSON outputs inside:

```text
reports/
```

Report outputs include:

* table counts
* data quality checks
* reconciliation results
* reconciliation breaks
* transaction risk scores
* customer risk scores
* ML anomaly scores
* ML anomaly alerts
* alert explanations
* graph nodes and edges
* graph risk clusters
* suspicious transfer patterns
* case-management work queue
* case-management summaries

---

## Project Structure

```text
transaction-risk-intelligence-engine/
│
├── api/
│   ├── main.py
│   └── README.md
│
├── dashboards/
│   ├── streamlit_app.py
│   └── README.md
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── synthetic/
│
├── docs/
│   ├── PROJECT_OVERVIEW.md
│   └── RUN_GUIDE.md
│
├── reports/
│
├── scripts/
│   └── run_full_pipeline.py
│
├── sql/
│
├── src/
│   ├── case_management/
│   ├── data_generation/
│   ├── data_quality/
│   ├── database/
│   ├── explainability/
│   ├── graph/
│   ├── ml/
│   ├── reconciliation/
│   ├── risk_scoring/
│   └── utils/
│
├── tests/
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## How to Run

For the detailed reproducibility guide, see:

```text
docs/RUN_GUIDE.md
```

The fastest local run is:

```powershell
python scripts\run_full_pipeline.py
```

Then run the dashboard:

```powershell
streamlit run dashboards\streamlit_app.py
```

Or run the API:

```powershell
uvicorn api.main:app --reload
```

---

## Skills Demonstrated

This project demonstrates:

* Python data engineering
* SQL analytics
* DuckDB database modelling
* data quality validation
* reconciliation control logic
* financial crime risk scoring
* fraud and AML-style transaction monitoring
* machine learning anomaly detection
* graph analytics
* explainable alerting
* operational case management
* API development
* dashboard development
* Docker-based reproducibility
* GitHub project organisation

---

## CV-Ready Project Summary

Transaction Risk Intelligence Engine – Fraud, Reconciliation and Graph Analytics

Built a production-style financial crime analytics engine using Python, DuckDB, SQL, scikit-learn, NetworkX, FastAPI and Streamlit to detect suspicious transactions, reconciliation breaks, risky entity clusters and operational alerts. Implemented synthetic financial data generation, rule-based risk scoring, Isolation Forest anomaly detection, explainable alert reasoning, graph analytics and a case-management dashboard with Docker support.
