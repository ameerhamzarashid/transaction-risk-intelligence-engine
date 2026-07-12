from pathlib import Path
from typing import Any
from html import escape

import duckdb
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st


BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "processed" / "transaction_risk.duckdb"


RISK_COLORS = {
    "Critical": "#8b1e1e",
    "High": "#b45309",
    "Medium": "#a16207",
    "Low": "#166534",
    "P1": "#8b1e1e",
    "P2": "#b45309",
    "P3": "#a16207",
    "P4": "#1d4ed8",
    "No Alert": "#64748b",
    "Within SLA": "#166534",
    "At Risk": "#a16207",
    "Breached": "#8b1e1e",
    "Closed": "#64748b",
    "Rule and ML": "#3730a3",
    "Rule Only": "#1d4ed8",
    "ML Only": "#0f766e",
    "No Review": "#64748b",
}

NEUTRAL_BLUE = "#1e3a8a"
SLATE = "#0f172a"


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
            padding-top: 1.2rem;
            padding-bottom: 3rem;
            max-width: 1540px;
        }

        .product-header {
            background: #0f172a;
            color: #ffffff;
            border-radius: 10px;
            padding: 1.35rem 1.55rem;
            margin-bottom: 1rem;
            border: 1px solid #1e293b;
            box-shadow: 0 8px 22px rgba(15, 23, 42, 0.16);
        }

        .product-title {
            font-size: 1.62rem;
            font-weight: 720;
            letter-spacing: -0.025em;
            margin-bottom: 0.25rem;
        }

        .product-subtitle {
            font-size: 0.96rem;
            color: #cbd5e1;
            max-width: 1120px;
            line-height: 1.5;
        }

        .status-strip {
            display: flex;
            gap: 0.6rem;
            margin-top: 1rem;
            flex-wrap: wrap;
        }

        .status-pill {
            border: 1px solid #334155;
            background: #111827;
            color: #e5e7eb;
            border-radius: 999px;
            padding: 0.28rem 0.7rem;
            font-size: 0.76rem;
            font-weight: 650;
        }

        .kpi-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 0.95rem 1rem;
            min-height: 112px;
            box-shadow: 0 4px 14px rgba(15, 23, 42, 0.055);
        }

        .kpi-critical { border-left: 5px solid #8b1e1e; }
        .kpi-high { border-left: 5px solid #b45309; }
        .kpi-medium { border-left: 5px solid #a16207; }
        .kpi-good { border-left: 5px solid #166534; }
        .kpi-neutral { border-left: 5px solid #1e3a8a; }

        .kpi-label {
            color: #64748b;
            font-size: 0.76rem;
            font-weight: 720;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            margin-bottom: 0.3rem;
        }

        .kpi-value {
            color: #0f172a;
            font-size: 1.72rem;
            font-weight: 760;
            letter-spacing: -0.03em;
            line-height: 1.1;
        }

        .kpi-help {
            color: #64748b;
            font-size: 0.78rem;
            margin-top: 0.35rem;
            line-height: 1.35;
        }

        .section-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 1rem 1rem;
            box-shadow: 0 4px 14px rgba(15, 23, 42, 0.045);
            margin-bottom: 1rem;
        }

        .section-title {
            font-size: 1.05rem;
            color: #0f172a;
            font-weight: 720;
            margin-bottom: 0.25rem;
        }

        .section-caption {
            color: #64748b;
            font-size: 0.86rem;
            margin-bottom: 0.75rem;
        }

        .detail-label {
            color: #64748b;
            font-size: 0.76rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.035em;
            margin-bottom: 0.15rem;
        }

        .detail-value {
            color: #0f172a;
            font-size: 0.95rem;
            font-weight: 600;
            margin-bottom: 0.65rem;
        }

        .badge {
            display: inline-block;
            padding: 0.22rem 0.55rem;
            border-radius: 999px;
            color: #ffffff;
            font-weight: 700;
            font-size: 0.72rem;
            margin-right: 0.3rem;
            margin-bottom: 0.25rem;
        }

        .badge-red { background: #8b1e1e; }
        .badge-orange { background: #b45309; }
        .badge-yellow { background: #a16207; }
        .badge-green { background: #166534; }
        .badge-blue { background: #1d4ed8; }
        .badge-purple { background: #3730a3; }
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

        .stTabs [data-baseweb="tab-list"] {
            gap: 0.4rem;
            border-bottom: 1px solid #e2e8f0;
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 8px 8px 0 0;
            padding: 0.6rem 1rem;
            font-weight: 650;
        }

        .stDataFrame {
            border-radius: 8px;
            border: 1px solid #e2e8f0;
            overflow: hidden;
        }

        button[kind="primary"] {
            background: #0f172a !important;
            border: 1px solid #0f172a !important;
        }

        .small-note {
            color: #64748b;
            font-size: 0.82rem;
            line-height: 1.45;
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


def safe_scalar(query: str, default: Any = 0) -> Any:
    try:
        df = query_df(query)
        if df.empty:
            return default
        return df.iloc[0, 0]
    except Exception:
        return default


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


def metric_card(label: str, value: Any, help_text: str, style: str = "neutral") -> None:
    st.markdown(
        f"""
        <div class="kpi-card kpi-{style}">
            <div class="kpi-label">{escape(str(label))}</div>
            <div class="kpi-value">{escape(str(value))}</div>
            <div class="kpi-help">{escape(str(help_text))}</div>
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

    return f'<span class="badge {colour_class}">{escape(str(value))}</span>'


def render_header() -> None:
    st.markdown(
        """
        <div class="product-header">
            <div class="product-title">Transaction Risk Intelligence Engine</div>
            <div class="product-subtitle">
                Integrated risk operations console for transaction monitoring, reconciliation controls,
                anomaly detection, graph analytics, explainable alerts and operational case management.
            </div>
            <div class="status-strip">
                <div class="status-pill">Synthetic data environment</div>
                <div class="status-pill">DuckDB analytics layer</div>
                <div class="status-pill">FastAPI service ready</div>
                <div class="status-pill">Case-management workflow</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not database_exists():
        st.error("DuckDB database not found. Run the full pipeline first.")
        st.code("python scripts\\run_full_pipeline.py", language="powershell")
        st.stop()


def render_section(title: str, caption: str = "") -> None:
    st.markdown(
        f"""
        <div class="section-card">
            <div class="section-title">{escape(title)}</div>
            <div class="section-caption">{escape(caption)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def plot_bar(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str,
    color: str | None = None,
    height: int = 360,
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
        template="plotly_white",
    )

    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=55, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        title_font=dict(size=16, color="#0f172a"),
        font=dict(size=12, color="#334155"),
        legend_title_text="",
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def plot_donut(df: pd.DataFrame, names: str, values: str, title: str, height: int = 360) -> None:
    if df.empty:
        st.info("No data available.")
        return

    fig = px.pie(
        df,
        names=names,
        values=values,
        hole=0.58,
        title=title,
        color=names,
        color_discrete_map=RISK_COLORS,
        template="plotly_white",
    )

    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=55, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        title_font=dict(size=16, color="#0f172a"),
        font=dict(size=12, color="#334155"),
        legend_title_text="",
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


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


def control_room_page() -> None:
    st.subheader("Control Room")

    total_cases = safe_count("case_management_cases")
    total_transactions = safe_count("transactions")
    total_recon_breaks = safe_count("reconciliation_breaks")
    total_graph_entities = safe_count("graph_nodes")
    total_explanations = safe_count("alert_explanations")

    p1_cases = safe_scalar(
        """
        SELECT COUNT(*)
        FROM case_management_cases
        WHERE case_priority = 'P1';
        """,
        0,
    )

    breached_cases = safe_scalar(
        """
        SELECT COUNT(*)
        FROM case_management_cases
        WHERE sla_status = 'Breached';
        """,
        0,
    )

    risk_alerts = safe_count("transaction_risk_alerts")
    ml_alerts = safe_count("ml_transaction_anomaly_alerts")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        metric_card("Transactions", format_number(total_transactions), "Base population analysed", "neutral")

    with c2:
        metric_card("Open Cases", format_number(total_cases), "Unified investigation queue", "medium")

    with c3:
        metric_card("P1 Cases", format_number(p1_cases), "Highest-priority cases", "critical")

    with c4:
        metric_card("SLA Breaches", format_number(breached_cases), "Cases outside SLA", "critical")

    c5, c6, c7, c8 = st.columns(4)

    with c5:
        metric_card("Rule Alerts", format_number(risk_alerts), "Rule-based risk alerts", "high")

    with c6:
        metric_card("ML Alerts", format_number(ml_alerts), "Anomaly-based alerts", "high")

    with c7:
        metric_card("Recon Breaks", format_number(total_recon_breaks), "Control breaks detected", "medium")

    with c8:
        metric_card("Graph Entities", format_number(total_graph_entities), "Network entities scored", "good")

    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "Operational Overview",
            "Risk Signals",
            "Controls",
            "Latest Work Queue",
        ]
    )

    with tab1:
        if not table_exists("case_management_cases"):
            st.warning("Run Stage 9 to generate case-management outputs.")
        else:
            left, right = st.columns(2)

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
                plot_bar(ml_df, "combined_risk_signal", "transaction_count", "Rule vs ML Detection Signal")

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
                plot_bar(recon_df, "primary_break_category", "break_count", "Reconciliation Break Types")

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
                plot_donut(cluster_df, "cluster_risk_band", "cluster_count", "Graph Cluster Risk")

    with tab4:
        if table_exists("case_management_work_queue"):
            queue_df = query_df(
                """
                SELECT
                    queue_rank,
                    case_id,
                    case_source_type,
                    case_priority,
                    sla_status,
                    case_owner,
                    case_title,
                    customer_id,
                    transaction_id,
                    amount,
                    risk_score,
                    recommended_action
                FROM case_management_work_queue
                ORDER BY queue_rank
                LIMIT 25;
                """
            )

            st.dataframe(queue_df, use_container_width=True, hide_index=True)
        else:
            st.warning("Run Stage 9 to generate the work queue.")


def case_management_page() -> None:
    st.subheader("Case Management")

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
        search_text = st.text_input("Search case text")
        limit = st.slider("Rows", 10, 500, 120)

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
            OR LOWER(recommended_action) LIKE ?
        )
        """
        search_param = f"%{search_text.lower()}%"
        params.extend([search_param] * 5)

    query += f"""
        ORDER BY priority_rank ASC, risk_score DESC, amount DESC
        LIMIT {limit};
    """

    df = query_df(query, tuple(params))

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        metric_card("Cases in View", format_number(len(df)), "Filtered case volume", "neutral")

    with c2:
        metric_card(
            "P1 Cases",
            format_number((df["case_priority"] == "P1").sum() if not df.empty else 0),
            "Immediate review",
            "critical",
        )

    with c3:
        metric_card(
            "SLA Breached",
            format_number((df["sla_status"] == "Breached").sum() if not df.empty else 0),
            "Outside target",
            "critical",
        )

    with c4:
        metric_card(
            "Total Case Amount",
            format_money(df["amount"].sum() if not df.empty else 0),
            "Value represented in view",
            "high",
        )

    if df.empty:
        st.info("No cases match the selected filters.")
        return

    left, right = st.columns([1.7, 1])

    with left:
        st.markdown("### Work Queue")

        queue_view = df[
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
            ]
        ]

        st.dataframe(queue_view, use_container_width=True, hide_index=True)
        download_csv(df, "case_management_filtered.csv")

    with right:
        st.markdown("### Case Detail")

        selected_case_id = st.selectbox(
            "Select a case",
            df["case_id"].tolist(),
        )

        selected = df[df["case_id"] == selected_case_id].iloc[0]

        st.markdown(
            f"""
            <div class="section-card">
                {badge(str(selected["case_priority"]))}
                {badge(str(selected["sla_status"]))}
                <div class="detail-label">Case ID</div>
                <div class="detail-value">{escape(str(selected["case_id"]))}</div>

                <div class="detail-label">Source</div>
                <div class="detail-value">{escape(str(selected["case_source_type"]))}</div>

                <div class="detail-label">Owner</div>
                <div class="detail-value">{escape(str(selected["case_owner"]))}</div>

                <div class="detail-label">Title</div>
                <div class="detail-value">{escape(str(selected["case_title"]))}</div>

                <div class="detail-label">Risk Score</div>
                <div class="detail-value">{escape(str(selected["risk_score"]))}</div>

                <div class="detail-label">Recommended Action</div>
                <div class="detail-value">{escape(str(selected["recommended_action"]))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("### Case Mix in Current View")

    chart_df = (
        df.groupby(["case_priority", "sla_status"])
        .size()
        .reset_index(name="case_count")
    )

    plot_bar(chart_df, "case_priority", "case_count", "Filtered Case Mix", "sla_status")


def risk_signals_page() -> None:
    st.subheader("Risk Signals")

    tab1, tab2, tab3 = st.tabs(
        [
            "Rule-Based Scoring",
            "ML Anomaly Detection",
            "Explainability",
        ]
    )

    with tab1:
        if not table_exists("transaction_risk_scores"):
            st.warning("Run Stage 5 first.")
        else:
            with st.sidebar:
                st.markdown("### Rule Filters")
                risk_band = st.selectbox("Risk Band", ["All", "Critical", "High", "Medium", "Low"])
                min_amount = st.number_input("Minimum transaction amount", min_value=0.0, value=0.0, step=100.0)
                top_n = st.slider("Risk rows", 10, 300, 100)

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
                metric_card("Rows Shown", format_number(len(df)), "Filtered transactions", "neutral")

            with c2:
                metric_card(
                    "Max Risk Score",
                    format_number(df["rule_based_risk_score"].max() if not df.empty else 0),
                    "Highest rule-based score",
                    "critical",
                )

            with c3:
                metric_card(
                    "Total Amount",
                    format_money(df["amount"].sum() if not df.empty else 0),
                    "Value in current view",
                    "high",
                )

            if not df.empty:
                fig = px.scatter(
                    df,
                    x="amount",
                    y="rule_based_risk_score",
                    color="risk_band",
                    hover_data=["transaction_id", "customer_id", "merchant_category", "reason_codes"],
                    title="Transaction Amount vs Rule-Based Risk Score",
                    color_discrete_map=RISK_COLORS,
                    template="plotly_white",
                )

                fig.update_layout(
                    height=430,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    title_font=dict(size=16),
                    legend_title_text="",
                )

                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

                st.dataframe(df, use_container_width=True, hide_index=True)
                download_csv(df, "rule_based_risk_signals.csv")

    with tab2:
        if not table_exists("ml_transaction_anomaly_scores"):
            st.warning("Run Stage 6 first.")
        else:
            signal = st.selectbox(
                "Detection signal",
                ["All", "Rule and ML", "ML Only", "Rule Only", "No Alert"],
                key="ml_signal_filter",
            )

            anomaly_band = st.selectbox(
                "Anomaly band",
                ["All", "Critical", "High", "Medium", "Low"],
                key="ml_band_filter",
            )

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

            if signal != "All":
                query += " AND combined_risk_signal = ?"
                params.append(signal)

            if anomaly_band != "All":
                query += " AND ml_anomaly_band = ?"
                params.append(anomaly_band)

            query += """
                ORDER BY anomaly_score_percentile DESC, rule_based_risk_score DESC
                LIMIT 150;
            """

            df = query_df(query, tuple(params))

            c1, c2, c3 = st.columns(3)

            with c1:
                metric_card("Rows Shown", format_number(len(df)), "Filtered ML signals", "neutral")

            with c2:
                metric_card(
                    "Max Anomaly Percentile",
                    format_number(df["anomaly_score_percentile"].max() if not df.empty else 0),
                    "Highest ML outlier strength",
                    "critical",
                )

            with c3:
                metric_card(
                    "Rule and ML Agreement",
                    format_number((df["combined_risk_signal"] == "Rule and ML").sum() if not df.empty else 0),
                    "Cases detected by both methods",
                    "high",
                )

            if not df.empty:
                fig = px.scatter(
                    df,
                    x="rule_based_risk_score",
                    y="anomaly_score_percentile",
                    color="combined_risk_signal",
                    size="amount",
                    hover_data=["transaction_id", "customer_id", "merchant_category", "ml_reason_codes"],
                    title="Rule-Based Risk vs ML Anomaly Percentile",
                    color_discrete_map=RISK_COLORS,
                    template="plotly_white",
                )

                fig.update_layout(
                    height=430,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    title_font=dict(size=16),
                    legend_title_text="",
                )

                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
                st.dataframe(df, use_container_width=True, hide_index=True)
                download_csv(df, "ml_anomaly_signals.csv")

    with tab3:
        if not table_exists("alert_explanations"):
            st.warning("Run Stage 7 first.")
        else:
            priority = st.selectbox(
                "Explanation priority",
                ["All", "P1", "P2", "P3", "No Alert"],
                key="explanation_priority_filter",
            )

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

            query += """
                ORDER BY combined_explanation_score DESC
                LIMIT 30;
            """

            df = query_df(query, tuple(params))

            if df.empty:
                st.info("No explanations match the selected filters.")
            else:
                for _, row in df.head(8).iterrows():
                    st.markdown(
                        f"""
                        <div class="section-card">
                            {badge(str(row["explanation_priority"]))}
                            {badge(str(row["main_trigger"]))}
                            <div class="section-title">{escape(str(row["explanation_id"]))} - {escape(str(row["transaction_id"]))}</div>
                            <div class="section-caption">
                                Customer {escape(str(row["customer_id"]))} | Amount {escape(format_money(row["amount"]))}
                            </div>
                            <div class="detail-label">Explanation</div>
                            <div class="detail-value">{escape(str(row["plain_english_explanation"]))}</div>
                            <div class="detail-label">Recommended Action</div>
                            <div class="detail-value">{escape(str(row["recommended_investigation_action"]))}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                with st.expander("View explanation table"):
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    download_csv(df, "alert_explanations.csv")


def reconciliation_page() -> None:
    st.subheader("Reconciliation")

    if not table_exists("reconciliation_breaks"):
        st.warning("Run Stage 3 first.")
        return

    severity = st.selectbox("Severity", ["All", "High", "Medium", "Low"])
    search_text = st.text_input("Search break type")
    limit = st.slider("Rows to show", 10, 300, 120)

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

    if search_text:
        query += " AND LOWER(break_type) LIKE ?"
        params.append(f"%{search_text.lower()}%")

    query += f"""
        ORDER BY
            CASE severity
                WHEN 'High' THEN 1
                WHEN 'Medium' THEN 2
                WHEN 'Low' THEN 3
                ELSE 9
            END,
            absolute_amount_difference DESC
        LIMIT {limit};
    """

    df = query_df(query, tuple(params))

    c1, c2, c3 = st.columns(3)

    with c1:
        metric_card("Breaks in View", format_number(len(df)), "Filtered reconciliation breaks", "neutral")

    with c2:
        metric_card(
            "High Severity",
            format_number((df["severity"] == "High").sum() if not df.empty else 0),
            "Priority control issues",
            "critical",
        )

    with c3:
        metric_card(
            "Absolute Difference",
            format_money(df["absolute_amount_difference"].sum() if not df.empty else 0),
            "Total break value",
            "high",
        )

    if df.empty:
        st.info("No reconciliation breaks match the selected filters.")
        return

    left, right = st.columns(2)

    with left:
        category_df = (
            df.groupby(["primary_break_category", "severity"])
            .size()
            .reset_index(name="break_count")
        )

        plot_bar(category_df, "primary_break_category", "break_count", "Break Category by Severity", "severity")

    with right:
        severity_df = (
            df.groupby("severity")
            .size()
            .reset_index(name="break_count")
        )

        plot_donut(severity_df, "severity", "break_count", "Severity Mix")

    st.dataframe(df, use_container_width=True, hide_index=True)
    download_csv(df, "reconciliation_breaks.csv")


def network_page() -> None:
    st.subheader("Network Analytics")

    if not table_exists("graph_high_centrality_entities"):
        st.warning("Run Stage 8 first.")
        return

    node_type = st.selectbox("Node type", ["All", "Customer", "Account", "Merchant"])
    min_score = st.slider("Minimum graph priority score", 0, 100, 0)
    limit = st.slider("Rows", 10, 250, 100)

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

    params = [min_score]

    if node_type != "All":
        query += " AND node_type = ?"
        params.append(node_type)

    query += f"""
        ORDER BY graph_priority_score DESC, total_degree DESC
        LIMIT {limit};
    """

    df = query_df(query, tuple(params))

    c1, c2, c3 = st.columns(3)

    with c1:
        metric_card("Entities in View", format_number(len(df)), "Filtered graph entities", "neutral")

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
            "Average connectedness",
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
            template="plotly_white",
        )

        fig.update_layout(
            height=430,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            title_font=dict(size=16),
            legend_title_text="",
        )

        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.dataframe(df, use_container_width=True, hide_index=True)
        download_csv(df, "graph_entities.csv")

    st.markdown("### Suspicious Transfer Patterns")

    if table_exists("graph_suspicious_transfer_patterns"):
        patterns = query_df(
            """
            SELECT *
            FROM graph_suspicious_transfer_patterns
            ORDER BY pattern_risk_score DESC, total_amount DESC
            LIMIT 100;
            """
        )

        st.dataframe(patterns, use_container_width=True, hide_index=True)


def investigation_page() -> None:
    st.subheader("Investigation Lookup")

    lookup_type = st.radio("Lookup type", ["Transaction", "Customer"], horizontal=True)

    if lookup_type == "Transaction":
        transaction_id = st.text_input("Transaction ID", value="TXN00000001")

        if st.button("Search Transaction", type="primary"):
            found = False

            for table_name in [
                "alert_explanations",
                "ml_transaction_anomaly_scores",
                "transaction_risk_scores",
                "case_management_cases",
            ]:
                if table_exists(table_name):
                    df = query_df(
                        f"""
                        SELECT *
                        FROM {table_name}
                        WHERE transaction_id = ?
                        LIMIT 20;
                        """,
                        (transaction_id,),
                    )

                    if not df.empty:
                        found = True
                        st.markdown(f"### {table_name}")
                        st.dataframe(df, use_container_width=True, hide_index=True)

            if not found:
                st.warning("No transaction found.")

    else:
        customer_id = st.text_input("Customer ID", value="CUST000001")

        if st.button("Search Customer", type="primary"):
            found = False

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
                        found = True
                        st.markdown(f"### {table_name}")
                        st.dataframe(df, use_container_width=True, hide_index=True)

            if not found:
                st.warning("No customer found.")


def transaction_scoring_page() -> None:
    st.subheader("Transaction Scoring")

    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">Rule-Based Transaction Scoring</div>
            <div class="section-caption">
                Simulate how a new transaction would be scored before it enters the monitoring queue.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("score_transaction_form"):
        col1, col2, col3 = st.columns(3)

        with col1:
            amount = st.number_input("Amount", min_value=0.0, value=7500.0, step=100.0)
            currency = st.selectbox("Currency", ["GBP", "EUR", "USD"])
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

            status = st.selectbox("Status", ["Completed", "Pending", "Failed", "Reversed"])

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

    if not submitted:
        return

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
        metric_card("Risk Band", result["risk_band"], "Severity classification", risk_style)

    with c3:
        metric_card("Priority", result["alert_priority"], "Operational handling", risk_style)

    with c4:
        metric_card("Create Alert", result["should_create_alert"], "Queue decision", risk_style)

    st.markdown("### Reason Codes")

    st.markdown(
        f"""
        <div class="section-card">
            <div class="detail-value">{escape(result["reason_codes"])}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("Input transaction"):
        st.json(input_data)


def main() -> None:
    apply_custom_css()
    render_header()

    st.sidebar.title("Risk Operations Console")

    page = st.sidebar.radio(
        "Workspace",
        [
            "Control Room",
            "Case Management",
            "Risk Signals",
            "Reconciliation",
            "Network Analytics",
            "Investigation Lookup",
            "Transaction Scoring",
        ],
    )

    st.sidebar.divider()
    st.sidebar.caption("Database")
    st.sidebar.code(str(DB_PATH))

    if st.sidebar.button("Clear cache"):
        st.cache_data.clear()
        st.rerun()

    if page == "Control Room":
        control_room_page()
    elif page == "Case Management":
        case_management_page()
    elif page == "Risk Signals":
        risk_signals_page()
    elif page == "Reconciliation":
        reconciliation_page()
    elif page == "Network Analytics":
        network_page()
    elif page == "Investigation Lookup":
        investigation_page()
    elif page == "Transaction Scoring":
        transaction_scoring_page()


if __name__ == "__main__":
    main()