from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd
import streamlit as st


BASE_DIR = Path(__file__).resolve().parents[1]
DB_PATH = BASE_DIR / "data" / "processed" / "transaction_risk.duckdb"


st.set_page_config(
    page_title="Transaction Risk Intelligence Engine",
    page_icon="🏦",
    layout="wide",
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

    query = """
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_name = ?
    """

    with duckdb.connect(str(DB_PATH), read_only=True) as con:
        result = con.execute(query, [table_name]).fetchone()[0]

    return result > 0


def safe_count(table_name: str) -> int:
    if not table_exists(table_name):
        return 0

    df = query_df(f"SELECT COUNT(*) AS row_count FROM {table_name};")
    return int(df["row_count"].iloc[0])


def show_missing_table_warning(table_name: str, stage_name: str) -> None:
    st.warning(
        f"Table `{table_name}` was not found. Run {stage_name} first, then refresh the dashboard."
    )


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


def page_header() -> None:
    st.title("🏦 Transaction Risk Intelligence Engine")
    st.caption(
        "Financial crime, reconciliation, anomaly detection, graph analytics and case-management dashboard."
    )

    if not database_exists():
        st.error(
            "DuckDB database not found. Run Stage 2 and the later pipeline stages first."
        )
        st.stop()


def executive_overview() -> None:
    st.subheader("Executive Overview")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Transactions", format_number(safe_count("transactions")))
    col2.metric("Cases", format_number(safe_count("case_management_cases")))
    col3.metric("Risk Alerts", format_number(safe_count("transaction_risk_alerts")))
    col4.metric("ML Alerts", format_number(safe_count("ml_transaction_anomaly_alerts")))

    col5, col6, col7, col8 = st.columns(4)

    col5.metric("Reconciliation Breaks", format_number(safe_count("reconciliation_breaks")))
    col6.metric("Graph Entities", format_number(safe_count("graph_nodes")))
    col7.metric("Explainable Alerts", format_number(safe_count("alert_explanations")))
    col8.metric("Transfer Patterns", format_number(safe_count("graph_suspicious_transfer_patterns")))

    st.divider()

    left, right = st.columns(2)

    with left:
        st.markdown("### Case Priority Summary")

        if table_exists("case_management_cases"):
            df = query_df(
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

            st.bar_chart(df, x="case_priority", y="case_count")
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            show_missing_table_warning("case_management_cases", "Stage 9")

    with right:
        st.markdown("### Case Source Summary")

        if table_exists("case_management_cases"):
            df = query_df(
                """
                SELECT case_source_type, COUNT(*) AS case_count
                FROM case_management_cases
                GROUP BY case_source_type
                ORDER BY case_count DESC;
                """
            )

            st.bar_chart(df, x="case_source_type", y="case_count")
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            show_missing_table_warning("case_management_cases", "Stage 9")


def case_management_page() -> None:
    st.subheader("Case Management Work Queue")

    if not table_exists("case_management_work_queue"):
        show_missing_table_warning("case_management_work_queue", "Stage 9")
        return

    priority_options = ["All", "P1", "P2", "P3", "P4"]
    selected_priority = st.selectbox("Filter by priority", priority_options)

    limit = st.slider("Number of cases to show", 10, 200, 50)

    query = """
        SELECT *
        FROM case_management_work_queue
        WHERE 1 = 1
    """

    params = []

    if selected_priority != "All":
        query += " AND case_priority = ?"
        params.append(selected_priority)

    query += f"""
        ORDER BY queue_rank
        LIMIT {limit};
    """

    df = query_df(query, tuple(params))

    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("### Owner Queue Summary")

    if table_exists("vw_case_management_owner_queue"):
        owner_df = query_df("SELECT * FROM vw_case_management_owner_queue;")
        st.dataframe(owner_df, use_container_width=True, hide_index=True)


def risk_scoring_page() -> None:
    st.subheader("Rule-Based Transaction Risk")

    if not table_exists("transaction_risk_scores"):
        show_missing_table_warning("transaction_risk_scores", "Stage 5")
        return

    left, right = st.columns(2)

    with left:
        st.markdown("### Transaction Risk Bands")
        df = query_df(
            """
            SELECT risk_band, COUNT(*) AS transaction_count
            FROM transaction_risk_scores
            GROUP BY risk_band
            ORDER BY transaction_count DESC;
            """
        )
        st.bar_chart(df, x="risk_band", y="transaction_count")
        st.dataframe(df, use_container_width=True, hide_index=True)

    with right:
        st.markdown("### Customer Risk Bands")

        if table_exists("customer_risk_scores"):
            customer_df = query_df(
                """
                SELECT customer_risk_band, COUNT(*) AS customer_count
                FROM customer_risk_scores
                GROUP BY customer_risk_band
                ORDER BY customer_count DESC;
                """
            )
            st.bar_chart(customer_df, x="customer_risk_band", y="customer_count")
            st.dataframe(customer_df, use_container_width=True, hide_index=True)

    st.markdown("### Top Risk Transactions")

    top_df = query_df(
        """
        SELECT
            transaction_id,
            customer_id,
            full_name,
            merchant_name,
            merchant_category,
            amount,
            currency,
            rule_based_risk_score,
            risk_band,
            alert_priority,
            reason_codes
        FROM transaction_risk_scores
        ORDER BY rule_based_risk_score DESC, amount DESC
        LIMIT 50;
        """
    )

    st.dataframe(top_df, use_container_width=True, hide_index=True)


def ml_anomaly_page() -> None:
    st.subheader("ML Anomaly Detection")

    if not table_exists("ml_transaction_anomaly_scores"):
        show_missing_table_warning("ml_transaction_anomaly_scores", "Stage 6")
        return

    left, right = st.columns(2)

    with left:
        st.markdown("### ML Anomaly Bands")
        df = query_df(
            """
            SELECT ml_anomaly_band, COUNT(*) AS transaction_count
            FROM ml_transaction_anomaly_scores
            GROUP BY ml_anomaly_band
            ORDER BY transaction_count DESC;
            """
        )
        st.bar_chart(df, x="ml_anomaly_band", y="transaction_count")
        st.dataframe(df, use_container_width=True, hide_index=True)

    with right:
        st.markdown("### Rule vs ML Signal")
        signal_df = query_df(
            """
            SELECT combined_risk_signal, COUNT(*) AS transaction_count
            FROM ml_transaction_anomaly_scores
            GROUP BY combined_risk_signal
            ORDER BY transaction_count DESC;
            """
        )
        st.bar_chart(signal_df, x="combined_risk_signal", y="transaction_count")
        st.dataframe(signal_df, use_container_width=True, hide_index=True)

    st.markdown("### Top ML Anomaly Alerts")

    top_df = query_df(
        """
        SELECT
            transaction_id,
            customer_id,
            full_name,
            merchant_name,
            amount,
            rule_based_risk_score,
            anomaly_score_percentile,
            ml_anomaly_band,
            combined_risk_signal,
            ml_reason_codes
        FROM ml_transaction_anomaly_scores
        ORDER BY anomaly_score_percentile DESC, rule_based_risk_score DESC
        LIMIT 50;
        """
    )

    st.dataframe(top_df, use_container_width=True, hide_index=True)


def reconciliation_page() -> None:
    st.subheader("Reconciliation Breaks")

    if not table_exists("reconciliation_breaks"):
        show_missing_table_warning("reconciliation_breaks", "Stage 3")
        return

    left, right = st.columns(2)

    with left:
        st.markdown("### Break Category Summary")
        df = query_df(
            """
            SELECT primary_break_category, COUNT(*) AS break_count
            FROM reconciliation_breaks
            GROUP BY primary_break_category
            ORDER BY break_count DESC;
            """
        )
        st.bar_chart(df, x="primary_break_category", y="break_count")
        st.dataframe(df, use_container_width=True, hide_index=True)

    with right:
        st.markdown("### Severity Summary")
        severity_df = query_df(
            """
            SELECT severity, COUNT(*) AS break_count
            FROM reconciliation_breaks
            GROUP BY severity
            ORDER BY break_count DESC;
            """
        )
        st.bar_chart(severity_df, x="severity", y="break_count")
        st.dataframe(severity_df, use_container_width=True, hide_index=True)

    st.markdown("### Reconciliation Break Cases")

    breaks_df = query_df(
        """
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
        ORDER BY
            CASE severity
                WHEN 'High' THEN 1
                WHEN 'Medium' THEN 2
                WHEN 'Low' THEN 3
                ELSE 9
            END,
            absolute_amount_difference DESC
        LIMIT 100;
        """
    )

    st.dataframe(breaks_df, use_container_width=True, hide_index=True)


def graph_page() -> None:
    st.subheader("Graph Analytics")

    if not table_exists("graph_nodes"):
        show_missing_table_warning("graph_nodes", "Stage 8")
        return

    left, right = st.columns(2)

    with left:
        st.markdown("### Graph Entity Risk Summary")

        if table_exists("vw_graph_entity_risk_summary"):
            df = query_df("SELECT * FROM vw_graph_entity_risk_summary;")
            st.dataframe(df, use_container_width=True, hide_index=True)

    with right:
        st.markdown("### Graph Cluster Summary")

        if table_exists("vw_graph_cluster_summary"):
            cluster_df = query_df("SELECT * FROM vw_graph_cluster_summary;")
            st.dataframe(cluster_df, use_container_width=True, hide_index=True)

    st.markdown("### High Centrality / High Risk Entities")

    if table_exists("graph_high_centrality_entities"):
        centrality_df = query_df(
            """
            SELECT
                centrality_case_id,
                node_id,
                node_type,
                node_label,
                node_risk_band,
                node_risk_score,
                total_degree,
                degree_centrality,
                pagerank_score,
                graph_priority_score,
                recommended_action
            FROM graph_high_centrality_entities
            ORDER BY graph_priority_score DESC
            LIMIT 50;
            """
        )

        st.dataframe(centrality_df, use_container_width=True, hide_index=True)

    st.markdown("### Suspicious Transfer Patterns")

    if table_exists("graph_suspicious_transfer_patterns"):
        patterns_df = query_df(
            """
            SELECT *
            FROM graph_suspicious_transfer_patterns
            ORDER BY pattern_risk_score DESC, total_amount DESC
            LIMIT 50;
            """
        )

        st.dataframe(patterns_df, use_container_width=True, hide_index=True)


def explainability_page() -> None:
    st.subheader("Explainability and Human-Readable Alerts")

    if not table_exists("alert_explanations"):
        show_missing_table_warning("alert_explanations", "Stage 7")
        return

    left, right = st.columns(2)

    with left:
        st.markdown("### Explanation Priority")
        df = query_df(
            """
            SELECT explanation_priority, COUNT(*) AS alert_count
            FROM alert_explanations
            GROUP BY explanation_priority
            ORDER BY alert_count DESC;
            """
        )
        st.bar_chart(df, x="explanation_priority", y="alert_count")
        st.dataframe(df, use_container_width=True, hide_index=True)

    with right:
        st.markdown("### Main Trigger")
        trigger_df = query_df(
            """
            SELECT main_trigger, COUNT(*) AS alert_count
            FROM alert_explanations
            GROUP BY main_trigger
            ORDER BY alert_count DESC;
            """
        )
        st.bar_chart(trigger_df, x="main_trigger", y="alert_count")
        st.dataframe(trigger_df, use_container_width=True, hide_index=True)

    st.markdown("### Top Plain-English Explanations")

    explanations_df = query_df(
        """
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
        ORDER BY combined_explanation_score DESC
        LIMIT 50;
        """
    )

    st.dataframe(explanations_df, use_container_width=True, hide_index=True)

    st.markdown("### Top Reason Codes")

    if table_exists("explanation_reason_summary"):
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
        "Choose lookup type",
        ["Transaction", "Customer"],
        horizontal=True,
    )

    if lookup_type == "Transaction":
        transaction_id = st.text_input("Enter transaction ID", value="TXN00000001")

        if st.button("Search Transaction"):
            if table_exists("alert_explanations"):
                df = query_df(
                    """
                    SELECT *
                    FROM alert_explanations
                    WHERE transaction_id = ?
                    ORDER BY combined_explanation_score DESC
                    LIMIT 1;
                    """,
                    (transaction_id,),
                )

                if df.empty and table_exists("ml_transaction_anomaly_scores"):
                    df = query_df(
                        """
                        SELECT *
                        FROM ml_transaction_anomaly_scores
                        WHERE transaction_id = ?;
                        """,
                        (transaction_id,),
                    )

                if df.empty and table_exists("transaction_risk_scores"):
                    df = query_df(
                        """
                        SELECT *
                        FROM transaction_risk_scores
                        WHERE transaction_id = ?;
                        """,
                        (transaction_id,),
                    )

                if df.empty:
                    st.warning("No transaction found.")
                else:
                    st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.warning("Explainability table not found. Run Stage 7 first.")

    else:
        customer_id = st.text_input("Enter customer ID", value="CUST000001")

        if st.button("Search Customer"):
            sections = []

            if table_exists("customer_risk_scores"):
                df = query_df(
                    """
                    SELECT *
                    FROM customer_risk_scores
                    WHERE customer_id = ?;
                    """,
                    (customer_id,),
                )
                sections.append(("Rule-Based Customer Risk", df))

            if table_exists("ml_customer_anomaly_summary"):
                df = query_df(
                    """
                    SELECT *
                    FROM ml_customer_anomaly_summary
                    WHERE customer_id = ?;
                    """,
                    (customer_id,),
                )
                sections.append(("ML Customer Anomaly Summary", df))

            if table_exists("customer_explanation_summary"):
                df = query_df(
                    """
                    SELECT *
                    FROM customer_explanation_summary
                    WHERE customer_id = ?;
                    """,
                    (customer_id,),
                )
                sections.append(("Customer Explanation Summary", df))

            if table_exists("case_management_cases"):
                df = query_df(
                    """
                    SELECT *
                    FROM case_management_cases
                    WHERE customer_id = ?
                    ORDER BY priority_rank ASC, risk_score DESC
                    LIMIT 50;
                    """,
                    (customer_id,),
                )
                sections.append(("Customer Cases", df))

            found_any = False

            for title, df in sections:
                st.markdown(f"### {title}")

                if df.empty:
                    st.info("No records found.")
                else:
                    found_any = True
                    st.dataframe(df, use_container_width=True, hide_index=True)

            if not found_any:
                st.warning("No customer records found in risk outputs.")


def score_new_transaction_page() -> None:
    st.subheader("Score a New Transaction")

    with st.form("score_transaction_form"):
        col1, col2, col3 = st.columns(3)

        with col1:
            amount = st.number_input("Amount", min_value=0.0, value=7500.0, step=100.0)
            currency = st.selectbox("Currency", ["GBP", "EUR", "USD"])
            channel = st.selectbox(
                "Channel",
                ["Card Present", "E-Commerce", "Mobile Banking", "Branch", "ATM", "API"],
            )

        with col2:
            transaction_type = st.selectbox(
                "Transaction Type",
                ["Purchase", "Cash Withdrawal", "Transfer", "Refund"],
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
            )

        with col3:
            cross_border_flag = st.checkbox("Cross-border transaction")
            high_amount_flag = st.checkbox("High amount transaction", value=True)
            unusual_hour_flag = st.checkbox("Unusual-hour activity")
            high_risk_category_flag = st.checkbox("High-risk category")
            high_risk_country_flag = st.checkbox("High-risk country")
            kyc_issue_flag = st.checkbox("KYC issue")
            pep_flag = st.checkbox("PEP flag")
            watchlist_match_flag = st.checkbox("Watchlist match")

        submitted = st.form_submit_button("Score Transaction")

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

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Risk Score", result["risk_score"])
        col2.metric("Risk Band", result["risk_band"])
        col3.metric("Alert Priority", result["alert_priority"])
        col4.metric("Create Alert?", result["should_create_alert"])

        st.markdown("### Reason Codes")
        st.write(result["reason_codes"])

        st.markdown("### Input Transaction")
        st.json(input_data)


def main() -> None:
    page_header()

    st.sidebar.title("Navigation")

    selected_page = st.sidebar.radio(
        "Go to",
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
    st.sidebar.caption(f"Database: {DB_PATH}")

    if st.sidebar.button("Clear dashboard cache"):
        st.cache_data.clear()
        st.rerun()

    if selected_page == "Executive Overview":
        executive_overview()
    elif selected_page == "Case Management":
        case_management_page()
    elif selected_page == "Rule-Based Risk":
        risk_scoring_page()
    elif selected_page == "ML Anomaly Detection":
        ml_anomaly_page()
    elif selected_page == "Reconciliation":
        reconciliation_page()
    elif selected_page == "Graph Analytics":
        graph_page()
    elif selected_page == "Explainability":
        explainability_page()
    elif selected_page == "Lookup":
        lookup_page()
    elif selected_page == "Score New Transaction":
        score_new_transaction_page()


if __name__ == "__main__":
    main()