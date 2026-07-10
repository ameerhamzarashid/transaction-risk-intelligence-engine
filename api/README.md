# FastAPI Service

This folder contains the FastAPI service for the Transaction Risk Intelligence Engine.

## Run the API

From the project root:

```powershell
uvicorn api.main:app --reload
```

Then open:

```text
http://127.0.0.1:8000/docs
```

## Main Endpoints

| Endpoint | Purpose |
|---|---|
| GET /health | Check API and database status |
| GET /database/tables | List DuckDB tables and views |
| GET /summary/cases | Case-management summary |
| GET /summary/risk | Risk, ML and graph summaries |
| GET /cases | Search case-management cases |
| GET /cases/{case_id} | Get one case by case ID |
| GET /work-queue | Prioritised operational work queue |
| GET /transactions/{transaction_id} | Get transaction risk/explanation data |
| GET /customers/{customer_id}/risk | Get customer-level risk data |
| GET /alerts/explanations | Get explainable risk alerts |
| GET /reconciliation/breaks | Get reconciliation breaks |
| GET /graph/entities | Get high-risk graph entities |
| GET /graph/transfer-patterns | Get suspicious transfer patterns |
| POST /score-transaction | Score a new transaction using rule-based logic |

## Example POST Body

```json
{
  "amount": 7500,
  "currency": "GBP",
  "channel": "Mobile Banking",
  "transaction_type": "Transfer",
  "status": "Completed",
  "merchant_category": "Crypto Exchange",
  "cross_border_flag": 1,
  "high_amount_flag": 1,
  "unusual_hour_flag": 1,
  "high_risk_category_flag": 1,
  "high_risk_country_flag": 1,
  "kyc_issue_flag": 1,
  "pep_flag": 0,
  "watchlist_match_flag": 1
}
```