# Streamlit Dashboard

This folder contains the Streamlit dashboard for the Transaction Risk Intelligence Engine.

## Run the Dashboard

From the project root:

```powershell
streamlit run dashboards\streamlit_app.py
```

Then open:

```text
http://localhost:8501
```

## Dashboard Pages

| Page | Purpose |
|---|---|
| Executive Overview | High-level project KPIs and summaries |
| Case Management | Prioritised operational work queue |
| Rule-Based Risk | Transaction and customer risk scoring outputs |
| ML Anomaly Detection | Isolation Forest anomaly results and rule-vs-ML comparison |
| Reconciliation | Reconciliation breaks, categories and severity |
| Graph Analytics | High-risk entities, graph clusters and suspicious transfer patterns |
| Explainability | Plain-English alert explanations and reason-code summaries |
| Lookup | Search transaction or customer risk records |
| Score New Transaction | Score a new transaction using rule-based logic |

## Notes

The dashboard reads from the local DuckDB database:

```text
data/processed/transaction_risk.duckdb
```

The database file is generated locally and is intentionally not committed to GitHub.