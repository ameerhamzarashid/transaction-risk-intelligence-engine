from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st


BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "processed" / "transaction_risk.duckdb"


RISK_COLORS = {
    "Critical": "#991b1b",
    "High": "#c2410c",
    "Medium": "#a16207",
    "Low": "#15803d",
    "P1": "#991b1b",
    "P2": "#c2410c",
    "P3": "#a16207",
    "P4": "#1d4ed8",
    "No Alert": "#475569",
    "Within SLA": "#15803d",
    "At Risk": "#a16207",
    "Breached": "#991b1b",
    "Closed": "#475569",
    "Rule and ML": "#4c1d95",
    "Rule Only": "#1d4ed8",
    "ML Only": "#0f766e",
    "No Review": "#475569",
}


st.set_page_config(
    page_title="Transaction Risk Intelligence Engine",
    layout="wide",
    initial_sidebar_state="expanded",
)


def apply_custom_css() -> None:
    st.markdown(
        """
        <style>
        .main {
            background: #f8fafc;
        }

        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 3rem;
            max-width: 1500px;
        }

        .hero-card {
            padding: 1.5rem 1.7rem;
            border-radius: 14px;
            background: #0f172a;
            color: white;
            border: 1px solid #1e293b;
            box-shadow: 0 10px 28px rgba(15, 23, 42, 0.16);
            margin-bottom: 1.2rem;
        }

        .hero-title {
            font-size: 1.75rem;
            font-weight: 700;
            margin-bottom: 0.35rem;
            letter-spacing: -0.02em;
        }

        .hero-subtitle {
            color: #cbd5e1;
            font-size: 0.98rem;
            line-height: 1.5;
            max-width: 1100px;
        }

        .kpi-card {
            padding: 1rem 1.05rem;
            border-radius: 12px;
            background: #ffffff;
            border: 1px solid #e2e8f0;
            box-shadow: 0 6px 18px rgba(15, 23, 42, 0.06);
            min-height: 118px;
        }

        .kpi-label {
            color: #64748b;
            font-size: 0.78rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.035em;
        }

        .kpi-value {
            color: #0f172a;
            font-size: 1.8rem;
            font-weight: 750;
            margin-top: 0.35rem;
        }

        .kpi-help {
            color: #64748b;
            font-size: 0.8rem;
            margin-top: 0.25rem;
        }

        .kpi-critical {
            border-left: 5px solid #991b1b;
        }

        .kpi-high {
            border-left: 5px solid #c2410c;
        }

        .kpi-medium {
            border-left: 5px solid #a16207;
        }

        .kpi-good {
            border-left: 5px solid #15803d;
        }

        .section-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 1rem;
            box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05);
            margin-bottom: 1rem;
        }

        .badge {
            display: inline-block;
            padding: 0.22rem 0.55rem;
            border-radius: 999px;
            color: white;
            font-weight: 700;
            font-size: 0.74rem;
            margin-right: 0.35rem;
            letter-spacing: 0.01em;
        }

        .badge-red { background: #991b1b; }
        .badge-orange { background: #c2410c; }
        .badge-yellow { background: #a16207; }
        .badge-green { background: #15803d; }
        .badge-blue { background: #1d4ed8; }
        .badge-purple { background: #5b21b6; }
        .badge-gray { background: #475569; }

        div[data-testid="stSidebar"] {
            background: #111827;
            border-right: 1px solid #1f2937;
        }

        div[data-testid="stSidebar"] * {
            color: #f9fafb;
        }

        div[data-testid="stSidebar"] input,
        div[data-testid="stSidebar"] select,
        div[data-testid="stSidebar"] textarea {
            color: #111827 !important;
        }

        h1, h2, h3 {
            color: #0f172a;
            letter-spacing: -0.02em;
        }

        div[data-testid="stMetric"] {
            background: white;
            border: 1px solid #e2e8f0;
            padding: 0.8rem;
            border-radius: 12px;
        }

        .stDataFrame {
            border-radius: 10px;
            overflow: hidden;
            border: 1px solid #e2e8f0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def database_exists() -> bool:
    return DB_PATH.exists()


@st.cache_data(show_spinner=False)
def query_df(query: str, params: tuple = ()) -> pd.DataFrame:
    with duckdb.connect(str(DB_PATH), read_only=True) as con:
        return con.execute(query, params).df()


@st.cache_data(show_spinner=False)
def table_exists(table_name: str) -> bool:
    if not database_exists():
        return False

    with duckdb.connect(str(DB_PATH), read_only=True) as con:
        result = con.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_name = ?
            """,
            [table_name],
        ).fetchone()[0]

    return result > 0


def safe_count(table_name: str) -> int:
    if not table_exists(table_name):
        return 0

    df = query_df(f"SELECT COUNT(*) AS row_count FROM {table_name};")
    return int(df["row_count"].iloc[0])


def format_number(value: Any) -> str:
    try:
        return f"{float(value):,.0f}"
    except Exception:
        return "0"


def format_money(value: Any) -> str:
    try:
        return f"£{float(value):,.2f}"
    except Exception:
        return "£0.00"


def metric_card(label: str, value: Any, help_text: str, style: str = "good") -> None:
    st.markdown(
        f"""
        <div class="kpi-card kpi-{style}">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-help">{help_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def badge(value: str) -> str:
    colour_class = "badge-gray"

    if value in ["Critical", "P1", "Breached"]:
        colour_class = "badge-red"
    elif value in ["High", "P2", "At Risk"]:
        colour_class = "badge-orange"
    elif value in ["Medium", "P3"]:
        colour_class = "badge-yellow"
    elif value in ["Low", "Within SLA"]:
        colour_class = "badge-green"
    elif value in ["Rule and ML"]:
        colour_class = "badge-purple"
    elif value in ["Rule Only", "P4"]:
        colour_class = "badge-blue"

    return f'<span class="badge {colour_class}">{value}</span>'


def page_header() -> None:
    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-title">Transaction Risk Intelligence Engine</div>
            <div class="hero-subtitle">
                Financial crime monitoring, reconciliation controls, anomaly detection,
                graph analytics, explainable alerts and operational case management.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not database_exists():
        st.error("DuckDB database not found. Run the full pipeline first.")
        st.code("python scripts\\run_full_pipeline.py", language="powershell")
        st.stop()


def plot_bar(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    color: str | None = None,
) -> None:
    if df.empty:
        st.info("No data available.")
        return

    fig = px.bar(
        df,
        x=x,
        y=y,
        color=color or x,
        title=title,
        color_discrete_map=RISK_COLORS,
        text_auto=True,
    )

    fig.update_layout(
        height=380,
        margin=dict(l=10, r=10, t=60, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=12),
        title_font=dict(size=17),
        legend_title_text="",
    )

    st.plotly_chart(fig, use_container_width=True)


def plot_donut(df: pd.DataFrame, names: str, values: str, title: str) -> None:
    if df.empty:
        st.info("No data available.")
        return

    fig = px.pie(
        df,
        names=names,
        values=values,
        hole=0.55,
        title=title,
        color=names,
        color_discrete_map=RISK_COLORS,
    )

    fig.update_layout(
        height=380,
        margin=dict(l=10, r=10, t=60, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        title_font=dict(size=17),
        legend_title_text="",
    )

    st.plotly_chart(fig, use_container_width=True)


def download_csv(df: pd.DataFrame, filename: str) -> None:
    csv = df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Download CSV",
        data=csv,
        file_name=filename,
        mime="text/csv",
    )


def score_transaction_rule_based(input_data: dict) -> dict:
    score = 0
    reasons = []

    amount = float(input_data["amount"])
    high_amount_flag = int(input_data["high_amount_flag"])

    def add_reason(reason: str) -> None:
        if reason not in reasons:
            reasons.append(reason)

    if input_data["watchlist_match_flag"] == 1:
        score += 35
        add_reason("WATCHLIST_MATCH")

    if input_data["pep_flag"] == 1:
        score += 25
        add_reason("PEP_CUSTOMER")

    if input_data["kyc_issue_flag"] == 1:
        score += 20
        add_reason("KYC_ISSUE")

    if input_data["high_risk_country_flag"] == 1:
        score += 18
        add_reason("HIGH_RISK_COUNTRY")

    if input_data["high_risk_category_flag"] == 1:
        score += 18
        add_reason("HIGH_RISK_MERCHANT_CATEGORY")

    if high_amount_flag == 1:
        score += 15
        add_reason("HIGH_AMOUNT_TRANSACTION")

    if amount >= 5000:
        score += 15
        add_reason("VERY_HIGH_AMOUNT")

    if amount >= 10000:
        score += 10
        add_reason("EXTREME_AMOUNT")

    if input_data["cross_border_flag"] == 1:
        score += 10
        add_reason("CROSS_BORDER_TRANSACTION")

    if input_data["unusual_hour_flag"] == 1:
        score += 10
        add_reason("UNUSUAL_HOUR_ACTIVITY")

    if input_data["merchant_category"] in ["Crypto Exchange", "Gambling", "Money Transfer"]:
        score += 10
        add_reason("SENSITIVE_MERCHANT_CATEGORY")

    if input_data["merchant_category"] in ["Cash Withdrawal", "Luxury Goods"]:
        score += 6
        add_reason("ELEVATED_MERCHANT_CATEGORY")

    if input_data["channel"] in ["ATM", "API"]:
        score += 5
        add_reason("CHANNEL_MONITORING_FLAG")

    if input_data["status"] in ["Failed", "Reversed"]:
        score += 5
        add_reason("NON_STANDARD_TRANSACTION_STATUS")

    if input_data["cross_border_flag"] == 1 and high_amount_flag == 1:
        score += 8
        add_reason("HIGH_AMOUNT_CROSS_BORDER_COMBINATION")

    if input_data["watchlist_match_flag"] == 1 and input_data["cross_border_flag"] == 1:
        score += 10
        add_reason("WATCHLIST_CROSS_BORDER_COMBINATION")

    if input_data["pep_flag"] == 1 and high_amount_flag == 1:
        score += 10
        add_reason("PEP_HIGH_AMOUNT_COMBINATION")

    score = min(score, 100)

    if score >= 75:
        risk_band = "Critical"
        priority = "P1"
    elif score >= 55:
        risk_band = "High"
        priority = "P2"
    elif score >= 30:
        risk_band = "Medium"
        priority = "P3"
    else:
        risk_band = "Low"
        priority = "No Alert"

    if not reasons:
        reasons.append("NO_MAJOR_RULE_TRIGGERED")

    return {
        "risk_score": score,
        "risk_band": risk_band,
        "alert_priority": priority,
        "should_create_alert": "Yes" if score >= 30 else "No",
        "reason_codes": "; ".join(reasons),
    }


def executive_overview() -> None:
    st.subheader("Executive Command Centre")

    total_cases = safe_count("case_management_cases")
    p1_cases = 0
    breached_cases = 0
    total_alerts = safe_count("transaction_risk_alerts") + safe_count("ml_transaction_anomaly_alerts")

    if table_exists("case_management_cases"):
        p1_cases = int(
            query_df(
                """
                SELECT COUNT(*) AS n
                FROM case_management_cases
                WHERE case_priority = 'P1';
                """
            )["n"].iloc[0]
        )

        breached_cases = int(
            query_df(
                """
                SELECT COUNT(*) AS n
                FROM case_management_cases
                WHERE sla_status = 'Breached';
                """
            )["n"].iloc[0]
        )

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        metric_card(
            "Transactions",
            format_number(safe_count("transactions")),
            "Synthetic transaction population",
            "good",
        )

    with c2:
        metric_card(
            "Open Cases",
            format_number(total_cases),
            "Unified operational case volume",
            "medium",
        )

    with c3:
        metric_card(
            "P1 Cases",
            format_number(p1_cases),
            "Highest priority analyst cases",
            "critical",
        )

    with c4:
        metric_card(
            "Risk and ML Alerts",
            format_number(total_alerts),
            "Rule and ML generated alerts",
            "high",
        )

    c5, c6, c7, c8 = st.columns(4)

    with c5:
        metric_card(
            "SLA Breaches",
            format_number(breached_cases),
            "Cases outside SLA window",
            "critical",
        )

    with c6:
        metric_card(
            "Reconciliation Breaks",
            format_number(safe_count("reconciliation_breaks")),
            "Operational control breaks",
            "high",
        )

    with c7:
        metric_card(
            "Graph Entities",
            format_number(safe_count("graph_nodes")),
            "Network nodes analysed",
            "good",
        )

    with c8:
        metric_card(
            "Explainable Alerts",
            format_number(safe_count("alert_explanations")),
            "Plain-English alert explanations",
            "medium",
        )

    st.divider()

    tab1, tab2, tab3 = st.tabs(
        [
            "Case Overview",
            "Risk Overview",
            "Graph and Reconciliation",
        ]
    )

    with tab1:
        left, right = st.columns(2)

        if table_exists("case_management_cases"):
            priority_df = query_df(
                """
                SELECT case_priority, COUNT(*) AS case_count
                FROM case_management_cases
                GROUP BY case_priority
                ORDER BY
                    CASE case_priority
                        WHEN 'P1' THEN 1
                        WHEN 'P2' THEN 2
                        WHEN 'P3' THEN 3
                        WHEN 'P4' THEN 4
                        ELSE 9
                    END;
                """
            )

            source_df = query_df(
                """
                SELECT case_source_type, COUNT(*) AS case_count
                FROM case_management_cases
                GROUP BY case_source_type
                ORDER BY case_count DESC;
                """
            )

            with left:
                plot_donut(priority_df, "case_priority", "case_count", "Case Priority Mix")

            with right:
                plot_bar(source_df, "case_source_type", "case_count", "Case Volume by Source")
        else:
            st.warning("Run Stage 9 to generate case-management tables.")

    with tab2:
        left, right = st.columns(2)

        if table_exists("transaction_risk_scores"):
            risk_df = query_df(
                """
                SELECT risk_band, COUNT(*) AS transaction_count
                FROM transaction_risk_scores
                GROUP BY risk_band
                ORDER BY transaction_count DESC;
                """
            )

            with left:
                plot_donut(risk_df, "risk_band", "transaction_count", "Rule-Based Risk Bands")

        if table_exists("ml_transaction_anomaly_scores"):
            ml_df = query_df(
                """
                SELECT combined_risk_signal, COUNT(*) AS transaction_count
                FROM ml_transaction_anomaly_scores
                GROUP BY combined_risk_signal
                ORDER BY transaction_count DESC;
                """
            )

            with right:
                plot_bar(
                    ml_df,
                    "combined_risk_signal",
                    "transaction_count",
                    "Rule vs ML Detection Signal",
                )

    with tab3:
        left, right = st.columns(2)

        if table_exists("reconciliation_breaks"):
            recon_df = query_df(
                """
                SELECT primary_break_category, COUNT(*) AS break_count
                FROM reconciliation_breaks
                GROUP BY primary_break_category
                ORDER BY break_count DESC;
                """
            )

            with left:
                plot_bar(
                    recon_df,
                    "primary_break_category",
                    "break_count",
                    "Reconciliation Break Types",
                )

        if table_exists("graph_risk_clusters"):
            cluster_df = query_df(
                """
                SELECT cluster_risk_band, COUNT(*) AS cluster_count
                FROM graph_risk_clusters
                GROUP BY cluster_risk_band
                ORDER BY cluster_count DESC;
                """
            )

            with right:
                plot_donut(
                    cluster_df,
                    "cluster_risk_band",
                    "cluster_count",
                    "Graph Cluster Risk",
                )


def case_management_page() -> None:
    st.subheader("Case Management Work Queue")

    if not table_exists("case_management_cases"):
        st.warning("Run Stage 9 first.")
        return

    with st.sidebar:
        st.markdown("### Case Filters")

        selected_priority = st.selectbox(
            "Priority",
            ["All", "P1", "P2", "P3", "P4"],
        )

        selected_sla = st.selectbox(
            "SLA Status",
            ["All", "Within SLA", "At Risk", "Breached", "Closed"],
        )

        source_options = ["All"] + query_df(
            """
            SELECT DISTINCT case_source_type
            FROM case_management_cases
            ORDER BY case_source_type;
            """
        )["case_source_type"].tolist()

        selected_source = st.selectbox("Source Type", source_options)
        search_text = st.text_input("Search title, customer, transaction or description")
        limit = st.slider("Rows", 10, 500, 100)

    query = """
        SELECT *
        FROM case_management_cases
        WHERE 1 = 1
    """

    params = []

    if selected_priority != "All":
        query += " AND case_priority = ?"
        params.append(selected_priority)

    if selected_sla != "All":
        query += " AND sla_status = ?"
        params.append(selected_sla)

    if selected_source != "All":
        query += " AND case_source_type = ?"
        params.append(selected_source)

    if search_text:
        query += """
        AND (
            LOWER(case_title) LIKE ?
            OR LOWER(customer_id) LIKE ?
            OR LOWER(transaction_id) LIKE ?
            OR LOWER(case_description) LIKE ?
        )
        """
        search_param = f"%{search_text.lower()}%"
        params.extend([search_param, search_param, search_param, search_param])

    query += f"""
        ORDER BY priority_rank ASC, risk_score DESC, amount DESC
        LIMIT {limit};
    """

    df = query_df(query, tuple(params))

    k1, k2, k3, k4 = st.columns(4)

    with k1:
        metric_card("Filtered Cases", format_number(len(df)), "Current queue view", "medium")

    with k2:
        metric_card(
            "P1 in View",
            format_number((df["case_priority"] == "P1").sum() if not df.empty else 0),
            "Urgent cases",
            "critical",
        )

    with k3:
        metric_card(
            "Breached in View",
            format_number((df["sla_status"] == "Breached").sum() if not df.empty else 0),
            "SLA breaches",
            "critical",
        )

    with k4:
        metric_card(
            "Total Amount",
            format_money(df["amount"].sum() if not df.empty else 0),
            "Case value in view",
            "high",
        )

    if df.empty:
        st.info("No cases match the selected filters.")
        return

    st.markdown("### Priority Work Queue")

    st.dataframe(
        df[
            [
                "case_id",
                "case_source_type",
                "case_priority",
                "sla_status",
                "case_owner",
                "case_title",
                "customer_id",
                "transaction_id",
                "amount",
                "risk_score",
                "case_age_bucket",
                "recommended_action",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

    download_csv(df, "filtered_case_management_cases.csv")

    chart_df = (
        df.groupby(["case_priority", "sla_status"])
        .size()
        .reset_index(name="case_count")
    )

    plot_bar(
        chart_df,
        "case_priority",
        "case_count",
        "Filtered Cases by Priority and SLA",
        "sla_status",
    )


def risk_scoring_page() -> None:
    st.subheader("Rule-Based Transaction Risk Explorer")

    if not table_exists("transaction_risk_scores"):
        st.warning("Run Stage 5 first.")
        return

    with st.sidebar:
        st.markdown("### Risk Filters")
        risk_band = st.selectbox("Risk Band", ["All", "Critical", "High", "Medium", "Low"])
        min_amount = st.number_input("Minimum amount", min_value=0.0, value=0.0, step=100.0)
        top_n = st.slider("Top transactions", 10, 250, 75)

    query = """
        SELECT
            transaction_id,
            transaction_timestamp,
            customer_id,
            full_name,
            merchant_name,
            merchant_category,
            amount,
            currency,
            channel,
            rule_based_risk_score,
            risk_band,
            alert_priority,
            reason_codes
        FROM transaction_risk_scores
        WHERE amount >= ?
    """

    params = [min_amount]

    if risk_band != "All":
        query += " AND risk_band = ?"
        params.append(risk_band)

    query += f"""
        ORDER BY rule_based_risk_score DESC, amount DESC
        LIMIT {top_n};
    """

    df = query_df(query, tuple(params))

    c1, c2, c3 = st.columns(3)

    with c1:
        metric_card("Transactions Shown", format_number(len(df)), "Filtered results", "medium")

    with c2:
        metric_card(
            "Max Risk Score",
            format_number(df["rule_based_risk_score"].max() if not df.empty else 0),
            "Highest rule score",
            "critical",
        )

    with c3:
        metric_card(
            "Total Amount",
            format_money(df["amount"].sum() if not df.empty else 0),
            "Transaction value shown",
            "high",
        )

    if df.empty:
        st.info("No transactions match the selected filters.")
        return

    fig = px.scatter(
        df,
        x="amount",
        y="rule_based_risk_score",
        color="risk_band",
        hover_data=["transaction_id", "customer_id", "merchant_category", "reason_codes"],
        title="Amount vs Rule-Based Risk Score",
        color_discrete_map=RISK_COLORS,
    )

    fig.update_layout(
        height=430,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        title_font=dict(size=17),
        legend_title_text="",
    )

    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(df, use_container_width=True, hide_index=True)
    download_csv(df, "rule_based_risk_filtered.csv")


def ml_anomaly_page() -> None:
    st.subheader("ML Anomaly Detection Explorer")

    if not table_exists("ml_transaction_anomaly_scores"):
        st.warning("Run Stage 6 first.")
        return

    with st.sidebar:
        st.markdown("### ML Filters")
        anomaly_band = st.selectbox("Anomaly Band", ["All", "Critical", "High", "Medium", "Low"])
        signal = st.selectbox("Signal", ["All", "Rule and ML", "ML Only", "Rule Only", "No Alert"])
        top_n = st.slider("Top anomalies", 10, 250, 75)

    query = """
        SELECT
            transaction_id,
            customer_id,
            full_name,
            merchant_name,
            merchant_category,
            amount,
            rule_based_risk_score,
            risk_band,
            anomaly_score_percentile,
            ml_anomaly_band,
            combined_risk_signal,
            ml_reason_codes
        FROM ml_transaction_anomaly_scores
        WHERE 1 = 1
    """

    params = []

    if anomaly_band != "All":
        query += " AND ml_anomaly_band = ?"
        params.append(anomaly_band)

    if signal != "All":
        query += " AND combined_risk_signal = ?"
        params.append(signal)

    query += f"""
        ORDER BY anomaly_score_percentile DESC, rule_based_risk_score DESC
        LIMIT {top_n};
    """

    df = query_df(query, tuple(params))

    c1, c2, c3 = st.columns(3)

    with c1:
        metric_card("Anomalies Shown", format_number(len(df)), "Filtered ML output", "medium")

    with c2:
        metric_card(
            "Max Percentile",
            format_number(df["anomaly_score_percentile"].max() if not df.empty else 0),
            "Highest anomaly percentile",
            "critical",
        )

    with c3:
        metric_card(
            "Rule and ML",
            format_number((df["combined_risk_signal"] == "Rule and ML").sum() if not df.empty else 0),
            "Detection agreement",
            "high",
        )

    if df.empty:
        st.info("No ML anomalies match the selected filters.")
        return

    fig = px.scatter(
        df,
        x="rule_based_risk_score",
        y="anomaly_score_percentile",
        color="combined_risk_signal",
        size="amount",
        hover_data=["transaction_id", "customer_id", "merchant_category", "ml_reason_codes"],
        title="Rule-Based Risk vs ML Anomaly Percentile",
        color_discrete_map=RISK_COLORS,
    )

    fig.update_layout(
        height=430,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        title_font=dict(size=17),
        legend_title_text="",
    )

    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(df, use_container_width=True, hide_index=True)
    download_csv(df, "ml_anomaly_filtered.csv")


def reconciliation_page() -> None:
    st.subheader("Reconciliation Control Centre")

    if not table_exists("reconciliation_breaks"):
        st.warning("Run Stage 3 first.")
        return

    with st.sidebar:
        st.markdown("### Reconciliation Filters")
        severity = st.selectbox("Break Severity", ["All", "High", "Medium", "Low"])
        break_search = st.text_input("Search break type")
        top_n = st.slider("Break rows", 10, 300, 100)

    query = """
        SELECT
            case_id,
            transaction_id,
            break_type,
            primary_break_category,
            severity,
            amount_difference,
            absolute_amount_difference,
            case_age_days,
            case_owner,
            recommended_action
        FROM reconciliation_breaks
        WHERE 1 = 1
    """

    params = []

    if severity != "All":
        query += " AND severity = ?"
        params.append(severity)

    if break_search:
        query += " AND LOWER(break_type) LIKE ?"
        params.append(f"%{break_search.lower()}%")

    query += f"""
        ORDER BY
            CASE severity
                WHEN 'High' THEN 1
                WHEN 'Medium' THEN 2
                WHEN 'Low' THEN 3
                ELSE 9
            END,
            absolute_amount_difference DESC
        LIMIT {top_n};
    """

    df = query_df(query, tuple(params))

    c1, c2, c3 = st.columns(3)

    with c1:
        metric_card("Breaks Shown", format_number(len(df)), "Filtered reconciliation cases", "high")

    with c2:
        metric_card(
            "High Severity",
            format_number((df["severity"] == "High").sum() if not df.empty else 0),
            "Priority control breaks",
            "critical",
        )

    with c3:
        metric_card(
            "Total Abs Difference",
            format_money(df["absolute_amount_difference"].sum() if not df.empty else 0),
            "Total break value",
            "medium",
        )

    if df.empty:
        st.info("No reconciliation breaks match the selected filters.")
        return

    summary_df = (
        df.groupby(["primary_break_category", "severity"])
        .size()
        .reset_index(name="break_count")
    )

    plot_bar(
        summary_df,
        "primary_break_category",
        "break_count",
        "Break Category by Severity",
        "severity",
    )

    st.dataframe(df, use_container_width=True, hide_index=True)
    download_csv(df, "reconciliation_breaks_filtered.csv")


def graph_page() -> None:
    st.subheader("Graph Analytics and Entity Network Risk")

    if not table_exists("graph_high_centrality_entities"):
        st.warning("Run Stage 8 first.")
        return

    with st.sidebar:
        st.markdown("### Graph Filters")
        node_type = st.selectbox("Node Type", ["All", "Customer", "Account", "Merchant"])
        min_graph_score = st.slider("Minimum graph priority score", 0, 100, 0)
        top_n = st.slider("Graph rows", 10, 250, 75)

    query = """
        SELECT
            centrality_case_id,
            node_id,
            node_type,
            node_label,
            node_risk_band,
            node_risk_score,
            in_degree,
            out_degree,
            total_degree,
            degree_centrality,
            pagerank_score,
            graph_priority_score,
            recommended_action
        FROM graph_high_centrality_entities
        WHERE graph_priority_score >= ?
    """

    params = [min_graph_score]

    if node_type != "All":
        query += " AND node_type = ?"
        params.append(node_type)

    query += f"""
        ORDER BY graph_priority_score DESC, total_degree DESC
        LIMIT {top_n};
    """

    df = query_df(query, tuple(params))

    c1, c2, c3 = st.columns(3)

    with c1:
        metric_card("Entities Shown", format_number(len(df)), "Filtered graph entities", "medium")

    with c2:
        metric_card(
            "Max Graph Score",
            format_number(df["graph_priority_score"].max() if not df.empty else 0),
            "Highest network risk",
            "critical",
        )

    with c3:
        metric_card(
            "Average Degree",
            format_number(df["total_degree"].mean() if not df.empty else 0),
            "Average connections",
            "high",
        )

    if not df.empty:
        fig = px.scatter(
            df,
            x="total_degree",
            y="graph_priority_score",
            color="node_type",
            size="node_risk_score",
            hover_data=["node_id", "node_label", "node_risk_band"],
            title="Graph Centrality vs Priority Score",
        )

        fig.update_layout(
            height=430,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            title_font=dict(size=17),
            legend_title_text="",
        )

        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(df, use_container_width=True, hide_index=True)
        download_csv(df, "graph_entities_filtered.csv")
    else:
        st.info("No graph entities match the selected filters.")

    st.markdown("### Suspicious Transfer Patterns")

    if table_exists("graph_suspicious_transfer_patterns"):
        patterns = query_df(
            """
            SELECT *
            FROM graph_suspicious_transfer_patterns
            ORDER BY pattern_risk_score DESC, total_amount DESC
            LIMIT 75;
            """
        )

        st.dataframe(patterns, use_container_width=True, hide_index=True)


def explainability_page() -> None:
    st.subheader("Explainability and Analyst Reasoning")

    if not table_exists("alert_explanations"):
        st.warning("Run Stage 7 first.")
        return

    with st.sidebar:
        st.markdown("### Explanation Filters")
        priority = st.selectbox("Explanation Priority", ["All", "P1", "P2", "P3", "No Alert"])
        trigger_search = st.text_input("Search main trigger")
        top_n = st.slider("Explanations", 5, 100, 25)

    query = """
        SELECT
            explanation_id,
            explanation_priority,
            review_queue,
            main_trigger,
            combined_explanation_score,
            transaction_id,
            customer_id,
            full_name,
            amount,
            evidence_summary,
            plain_english_explanation,
            recommended_investigation_action
        FROM alert_explanations
        WHERE 1 = 1
    """

    params = []

    if priority != "All":
        query += " AND explanation_priority = ?"
        params.append(priority)

    if trigger_search:
        query += " AND LOWER(main_trigger) LIKE ?"
        params.append(f"%{trigger_search.lower()}%")

    query += f"""
        ORDER BY combined_explanation_score DESC
        LIMIT {top_n};
    """

    df = query_df(query, tuple(params))

    c1, c2, c3 = st.columns(3)

    with c1:
        metric_card("Explanations", format_number(len(df)), "Filtered explanations", "medium")

    with c2:
        metric_card(
            "P1 Explanations",
            format_number((df["explanation_priority"] == "P1").sum() if not df.empty else 0),
            "Highest priority explanations",
            "critical",
        )

    with c3:
        metric_card(
            "Max Explanation Score",
            format_number(df["combined_explanation_score"].max() if not df.empty else 0),
            "Strongest combined evidence",
            "high",
        )

    if df.empty:
        st.info("No explanations match the selected filters.")
        return

    for _, row in df.head(10).iterrows():
        st.markdown(
            f"""
            <div class="section-card">
                {badge(str(row['explanation_priority']))}
                {badge(str(row['main_trigger']))}
                <h4>{row['explanation_id']} - {row['transaction_id']}</h4>
                <p><b>Customer:</b> {row['customer_id']} | <b>Amount:</b> {format_money(row['amount'])}</p>
                <p><b>Explanation:</b> {row['plain_english_explanation']}</p>
                <p><b>Action:</b> {row['recommended_investigation_action']}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with st.expander("View explanation table"):
        st.dataframe(df, use_container_width=True, hide_index=True)
        download_csv(df, "alert_explanations_filtered.csv")

    if table_exists("explanation_reason_summary"):
        st.markdown("### Top Reason Codes")

        reason_df = query_df(
            """
            SELECT *
            FROM explanation_reason_summary
            ORDER BY transaction_count DESC, average_combined_explanation_score DESC
            LIMIT 50;
            """
        )

        st.dataframe(reason_df, use_container_width=True, hide_index=True)


def lookup_page() -> None:
    st.subheader("Customer and Transaction Lookup")

    lookup_type = st.radio(
        "Lookup Type",
        ["Transaction", "Customer"],
        horizontal=True,
    )

    if lookup_type == "Transaction":
        transaction_id = st.text_input("Transaction ID", value="TXN00000001")

        if st.button("Search Transaction", type="primary"):
            result_found = False

            for table_name in [
                "alert_explanations",
                "ml_transaction_anomaly_scores",
                "transaction_risk_scores",
            ]:
                if table_exists(table_name):
                    df = query_df(
                        f"""
                        SELECT *
                        FROM {table_name}
                        WHERE transaction_id = ?
                        LIMIT 5;
                        """,
                        (transaction_id,),
                    )

                    if not df.empty:
                        result_found = True
                        st.markdown(f"### Result from `{table_name}`")
                        st.dataframe(df, use_container_width=True, hide_index=True)

            if not result_found:
                st.warning("No transaction found.")

    else:
        customer_id = st.text_input("Customer ID", value="CUST000001")

        if st.button("Search Customer", type="primary"):
            result_found = False

            for table_name in [
                "customer_risk_scores",
                "ml_customer_anomaly_summary",
                "customer_explanation_summary",
                "case_management_cases",
            ]:
                if table_exists(table_name):
                    df = query_df(
                        f"""
                        SELECT *
                        FROM {table_name}
                        WHERE customer_id = ?
                        LIMIT 50;
                        """,
                        (customer_id,),
                    )

                    if not df.empty:
                        result_found = True
                        st.markdown(f"### Result from `{table_name}`")
                        st.dataframe(df, use_container_width=True, hide_index=True)

            if not result_found:
                st.warning("No customer found in risk outputs.")


def score_new_transaction_page() -> None:
    st.subheader("Score a New Transaction")

    st.markdown(
        """
        <div class="section-card">
        Use this form to simulate how a new transaction would be scored by the rule-based risk engine.
        The output shows the score, severity band, priority and reason codes.
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("score_transaction_form"):
        col1, col2, col3 = st.columns(3)

        with col1:
            amount = st.number_input(
                "Amount",
                min_value=0.0,
                value=7500.0,
                step=100.0,
            )

            currency = st.selectbox(
                "Currency",
                ["GBP", "EUR", "USD"],
            )

            channel = st.selectbox(
                "Channel",
                ["Card Present", "E-Commerce", "Mobile Banking", "Branch", "ATM", "API"],
                index=2,
            )

        with col2:
            transaction_type = st.selectbox(
                "Transaction Type",
                ["Purchase", "Cash Withdrawal", "Transfer", "Refund"],
                index=2,
            )

            status = st.selectbox(
                "Status",
                ["Completed", "Pending", "Failed", "Reversed"],
            )

            merchant_category = st.selectbox(
                "Merchant Category",
                [
                    "Groceries",
                    "Electronics",
                    "Travel",
                    "Gambling",
                    "Crypto Exchange",
                    "Luxury Goods",
                    "Restaurants",
                    "Fuel",
                    "Online Marketplace",
                    "Cash Withdrawal",
                    "Money Transfer",
                    "Subscription",
                    "Pharmacy",
                    "Hotels",
                ],
                index=4,
            )

        with col3:
            cross_border_flag = st.checkbox("Cross-border transaction", value=True)
            high_amount_flag = st.checkbox("High amount transaction", value=True)
            unusual_hour_flag = st.checkbox("Unusual-hour activity", value=True)
            high_risk_category_flag = st.checkbox("High-risk category", value=True)
            high_risk_country_flag = st.checkbox("High-risk country", value=True)
            kyc_issue_flag = st.checkbox("KYC issue", value=True)
            pep_flag = st.checkbox("PEP flag")
            watchlist_match_flag = st.checkbox("Watchlist match", value=True)

        submitted = st.form_submit_button("Score Transaction", type="primary")

    if submitted:
        input_data = {
            "amount": amount,
            "currency": currency,
            "channel": channel,
            "transaction_type": transaction_type,
            "status": status,
            "merchant_category": merchant_category,
            "cross_border_flag": int(cross_border_flag),
            "high_amount_flag": int(high_amount_flag),
            "unusual_hour_flag": int(unusual_hour_flag),
            "high_risk_category_flag": int(high_risk_category_flag),
            "high_risk_country_flag": int(high_risk_country_flag),
            "kyc_issue_flag": int(kyc_issue_flag),
            "pep_flag": int(pep_flag),
            "watchlist_match_flag": int(watchlist_match_flag),
        }

        result = score_transaction_rule_based(input_data)

        risk_style = "good"

        if result["risk_band"] == "Critical":
            risk_style = "critical"
        elif result["risk_band"] == "High":
            risk_style = "high"
        elif result["risk_band"] == "Medium":
            risk_style = "medium"

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            metric_card("Risk Score", result["risk_score"], "Rule-based score", risk_style)

        with c2:
            metric_card("Risk Band", result["risk_band"], "Severity category", risk_style)

        with c3:
            metric_card("Alert Priority", result["alert_priority"], "Operational priority", risk_style)

        with c4:
            metric_card("Create Alert", result["should_create_alert"], "Alert decision", risk_style)

        st.markdown("### Reason Codes")

        st.markdown(
            f"""
            <div class="section-card">
            <b>{result["reason_codes"]}</b>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("### Input Transaction")
        st.json(input_data)


def main() -> None:
    apply_custom_css()
    page_header()

    st.sidebar.title("Navigation")

    page = st.sidebar.radio(
        "Choose page",
        [
            "Executive Overview",
            "Case Management",
            "Rule-Based Risk",
            "ML Anomaly Detection",
            "Reconciliation",
            "Graph Analytics",
            "Explainability",
            "Lookup",
            "Score New Transaction",
        ],
    )

    st.sidebar.divider()
    st.sidebar.caption("Local DuckDB database")
    st.sidebar.code(str(DB_PATH))

    if st.sidebar.button("Clear cache and refresh"):
        st.cache_data.clear()
        st.rerun()

    if page == "Executive Overview":
        executive_overview()
    elif page == "Case Management":
        case_management_page()
    elif page == "Rule-Based Risk":
        risk_scoring_page()
    elif page == "ML Anomaly Detection":
        ml_anomaly_page()
    elif page == "Reconciliation":
        reconciliation_page()
    elif page == "Graph Analytics":
        graph_page()
    elif page == "Explainability":
        explainability_page()
    elif page == "Lookup":
        lookup_page()
    elif page == "Score New Transaction":
        score_new_transaction_page()


if __name__ == "__main__":
    main()