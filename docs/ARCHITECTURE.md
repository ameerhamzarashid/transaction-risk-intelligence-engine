# Architecture

## Transaction Risk Intelligence Engine

This project follows a staged analytical pipeline that moves from synthetic data generation through database modelling, control checks, risk scoring, anomaly detection, graph analytics, case management, API delivery and dashboard presentation.

## Architecture Flow

```text
Synthetic Financial Data
        ↓
DuckDB Database Layer
        ↓
Data Quality Validation
        ↓
Reconciliation Engine
        ↓
Rule-Based Risk Scoring
        ↓
ML Anomaly Detection
        ↓
Explainability Layer
        ↓
Graph Analytics
        ↓
Unified Case Management
        ↓
FastAPI Service Layer
        ↓
Streamlit Risk Operations Dashboard