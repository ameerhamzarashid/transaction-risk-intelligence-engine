# Run Guide

This guide explains how to run the Transaction Risk Intelligence Engine from start to finish.

The instructions are written for Windows PowerShell.

---

## 1. Prerequisites

Install these first:

* Python 3.10 or newer
* Git
* VS Code
* Docker Desktop, optional but recommended

Check Python:

```powershell
python --version
```

Check Git:

```powershell
git --version
```

Check Docker, optional:

```powershell
docker --version
```

---

## 2. Open the Project

Go to the project folder:

```powershell
cd C:\MyDrive\transaction-risk-intelligence-engine
```

Open VS Code:

```powershell
code .
```

---

## 3. Create and Activate Virtual Environment

Create the virtual environment if it does not already exist:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then activate again:

```powershell
.\.venv\Scripts\Activate.ps1
```

When activated, your terminal should show:

```text
(.venv)
```

---

## 4. Install Dependencies

Install all required packages:

```powershell
pip install -r requirements.txt
```

The project uses:

* pandas
* numpy
* duckdb
* scikit-learn
* networkx
* fastapi
* uvicorn
* streamlit
* plotly

---

## 5. Run the Full Pipeline Automatically

The easiest way to reproduce the project is to run the full pipeline script:

```powershell
python scripts\run_full_pipeline.py
```

This runs the core stages in order:

```text
Stage 1 - Synthetic data generation
Stage 2 - DuckDB database build
Stage 3 - Reconciliation engine
Stage 4 - Data quality checks
Stage 5 - Rule-based risk scoring
Stage 6 - ML anomaly detection
Stage 7 - Explainability layer
Stage 8 - Graph analytics
Stage 9 - Case management
```

Expected final output:

```text
Full pipeline completed successfully
```

After this, the local database and reports should be ready.

---

## 6. Run Each Stage Manually

If you want to run each stage yourself, use the commands below in this exact order.

### Stage 1: Generate Synthetic Data

```powershell
python src\data_generation\generate_synthetic_data.py
```

Expected outputs:

```text
data/synthetic/customers.csv
data/synthetic/merchants.csv
data/synthetic/accounts.csv
data/synthetic/transactions.csv
data/synthetic/account_transfers.csv
data/synthetic/watchlist.csv
data/synthetic/reconciliation_file_a.csv
data/synthetic/reconciliation_file_b.csv
data/synthetic/generation_summary.json
```

---

### Stage 2: Build DuckDB Database

```powershell
python src\database\build_duckdb_database.py
```

Expected output:

```text
data/processed/transaction_risk.duckdb
```

Expected reports:

```text
reports/stage2_table_counts.csv
reports/stage2_database_quality_checks.csv
reports/stage2_database_summary.json
```

---

### Stage 3: Run Reconciliation Engine

```powershell
python src\reconciliation\run_reconciliation.py
```

Expected reports:

```text
reports/stage3_reconciliation_full_results.csv
reports/stage3_reconciliation_breaks.csv
reports/stage3_break_type_summary.csv
reports/stage3_reconciliation_summary.json
```

---

### Stage 4: Run Data Quality Checks

```powershell
python src\data_quality\run_data_quality_checks.py
```

Expected reports:

```text
reports/stage4_data_quality_results.csv
reports/stage4_failed_data_quality_checks.csv
reports/stage4_data_quality_summary.json
```

A warning for controlled duplicate reconciliation records is acceptable because the synthetic data intentionally includes controlled breaks.

---

### Stage 5: Run Rule-Based Risk Scoring

```powershell
python src\risk_scoring\run_rule_based_risk_scoring.py
```

Expected reports:

```text
reports/stage5_transaction_risk_scores.csv
reports/stage5_customer_risk_scores.csv
reports/stage5_transaction_risk_alerts.csv
reports/stage5_risk_scoring_summary.json
```

---

### Stage 6: Run ML Anomaly Detection

```powershell
python src\ml\run_anomaly_detection.py
```

Expected reports:

```text
reports/stage6_ml_transaction_anomaly_scores.csv
reports/stage6_ml_transaction_anomaly_alerts.csv
reports/stage6_ml_customer_anomaly_summary.csv
reports/stage6_ml_anomaly_summary.json
```

---

### Stage 7: Run Explainability Layer

```powershell
python src\explainability\run_explainability_layer.py
```

Expected reports:

```text
reports/stage7_alert_explanations.csv
reports/stage7_explanation_reason_summary.csv
reports/stage7_customer_explanation_summary.csv
reports/stage7_explainability_summary.json
```

---

### Stage 8: Run Graph Analytics

```powershell
python src\graph\run_graph_analytics.py
```

Expected reports:

```text
reports/stage8_graph_nodes.csv
reports/stage8_graph_edges.csv
reports/stage8_graph_risk_clusters.csv
reports/stage8_suspicious_transfer_patterns.csv
reports/stage8_high_centrality_entities.csv
reports/stage8_graph_analytics_summary.json
```

---

### Stage 9: Run Case Management

```powershell
python src\case_management\run_case_management.py
```

Expected reports:

```text
reports/stage9_case_management_cases.csv
reports/stage9_case_management_summary.csv
reports/stage9_case_management_work_queue.csv
reports/stage9_case_management_summary.json
```

---

## 7. Check the Database

After running the pipeline, check the DuckDB database exists:

```powershell
Get-ChildItem data\processed
```

You should see:

```text
transaction_risk.duckdb
```

Check key database tables:

```powershell
python -c "import duckdb; con=duckdb.connect('data/processed/transaction_risk.duckdb'); print(con.execute('SHOW TABLES').fetchall())"
```

Check case count:

```powershell
python -c "import duckdb; con=duckdb.connect('data/processed/transaction_risk.duckdb'); print(con.execute('SELECT COUNT(*) FROM case_management_cases').fetchall())"
```

Check transaction count:

```powershell
python -c "import duckdb; con=duckdb.connect('data/processed/transaction_risk.duckdb'); print(con.execute('SELECT COUNT(*) FROM transactions').fetchall())"
```

Expected transaction count:

```text
10000
```

---

## 8. Check Reports

List generated reports:

```powershell
Get-ChildItem reports
```

Preview case-management work queue:

```powershell
python -c "import pandas as pd; df=pd.read_csv('reports/stage9_case_management_work_queue.csv'); print(df.head(10).to_string(index=False))"
```

Preview alert explanations:

```powershell
python -c "import pandas as pd; df=pd.read_csv('reports/stage7_alert_explanations.csv'); print(df[['explanation_id','transaction_id','explanation_priority','main_trigger','combined_explanation_score']].head(10).to_string(index=False))"
```

Preview graph entities:

```powershell
python -c "import pandas as pd; df=pd.read_csv('reports/stage8_high_centrality_entities.csv'); print(df[['centrality_case_id','node_id','node_type','node_risk_score','graph_priority_score']].head(10).to_string(index=False))"
```

---

## 9. Run the FastAPI Service

Start the API:

```powershell
uvicorn api.main:app --reload
```

Open in browser:

```text
http://127.0.0.1:8000/docs
```

Useful endpoints:

```text
GET /health
GET /database/tables
GET /summary/cases
GET /summary/risk
GET /cases
GET /work-queue
GET /alerts/explanations
GET /reconciliation/breaks
GET /graph/entities
GET /graph/transfer-patterns
POST /score-transaction
```

Stop the API:

```text
Ctrl + C
```

---

## 10. Test API from PowerShell

Open a second PowerShell terminal and run:

```powershell
cd C:\MyDrive\transaction-risk-intelligence-engine
.\.venv\Scripts\Activate.ps1
```

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Case summary:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/summary/cases
```

Work queue:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/work-queue?limit=5"
```

Score a sample transaction:

```powershell
$body = @{
    amount = 7500
    currency = "GBP"
    channel = "Mobile Banking"
    transaction_type = "Transfer"
    status = "Completed"
    merchant_category = "Crypto Exchange"
    cross_border_flag = 1
    high_amount_flag = 1
    unusual_hour_flag = 1
    high_risk_category_flag = 1
    high_risk_country_flag = 1
    kyc_issue_flag = 1
    pep_flag = 0
    watchlist_match_flag = 1
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/score-transaction" -Method Post -Body $body -ContentType "application/json"
```

Expected response includes:

```text
rule_based_risk_score
risk_band
alert_priority
should_create_alert
reason_codes
```

---

## 11. Run the Streamlit Dashboard

Start dashboard:

```powershell
streamlit run dashboards\streamlit_app.py
```

Open in browser:

```text
http://localhost:8501
```

Dashboard workspaces:

```text
Control Room
Case Management
Risk Signals
Reconciliation
Network Analytics
Investigation Lookup
Transaction Scoring
```

Stop dashboard:

```text
Ctrl + C
```

---

## 12. Run with Docker

Make sure Docker Desktop is running.

Check Docker:

```powershell
docker --version
```

Build image:

```powershell
docker build -t transaction-risk-intelligence-engine .
```

Run the full pipeline inside Docker:

```powershell
docker run --rm transaction-risk-intelligence-engine
```

Expected final output:

```text
Full pipeline completed successfully
```

---

## 13. Run API and Dashboard with Docker Compose

Start services:

```powershell
docker compose up --build
```

Open API:

```text
http://127.0.0.1:8000/docs
```

Open dashboard:

```text
http://127.0.0.1:8501
```

Stop services:

```text
Ctrl + C
```

Then clean up:

```powershell
docker compose down
```

---

## 14. GitHub Workflow

Check current changes:

```powershell
git status
```

Add changes:

```powershell
git add .
```

Commit changes:

```powershell
git commit -m "Update project documentation and run guide"
```

Push to GitHub:

```powershell
git push
```

Final check:

```powershell
git status
```

Expected:

```text
nothing to commit, working tree clean
```

---

## 15. Common Issues and Fixes

### Virtual environment will not activate

Run:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then:

```powershell
.\.venv\Scripts\Activate.ps1
```

---

### ModuleNotFoundError

Example:

```text
ModuleNotFoundError: No module named 'duckdb'
```

Fix:

```powershell
pip install -r requirements.txt
```

---

### Database not found

Error:

```text
DuckDB database not found
```

Fix:

```powershell
python scripts\run_full_pipeline.py
```

---

### Streamlit dashboard does not update

Use the sidebar button:

```text
Clear cache
```

Or stop and restart:

```powershell
streamlit run dashboards\streamlit_app.py
```

---

### API does not start

Make sure the database exists:

```powershell
Get-ChildItem data\processed
```

Then rerun:

```powershell
python scripts\run_full_pipeline.py
```

Start API again:

```powershell
uvicorn api.main:app --reload
```

---

### Docker command fails

Make sure Docker Desktop is open.

Then check:

```powershell
docker --version
```

If Docker is working, rebuild:

```powershell
docker compose up --build
```

---

## 16. Recommended Reproducible Run Order

For a clean local run:

```powershell
cd C:\MyDrive\transaction-risk-intelligence-engine
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python scripts\run_full_pipeline.py
streamlit run dashboards\streamlit_app.py
```

For API:

```powershell
uvicorn api.main:app --reload
```

For Docker:

```powershell
docker compose up --build
```

---

## 17. Expected Final Outputs

After a successful run, you should have:

```text
data/synthetic/
data/processed/transaction_risk.duckdb
reports/
api/
dashboards/
docs/
sql/
src/
```

The most important outputs are:

```text
reports/stage9_case_management_work_queue.csv
reports/stage7_alert_explanations.csv
reports/stage8_high_centrality_entities.csv
data/processed/transaction_risk.duckdb
```

The most important user-facing apps are:

```text
FastAPI:
http://127.0.0.1:8000/docs

Streamlit dashboard:
http://localhost:8501
```
