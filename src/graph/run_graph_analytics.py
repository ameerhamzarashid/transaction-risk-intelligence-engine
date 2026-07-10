from pathlib import Path
import json
from datetime import datetime

import duckdb
import networkx as nx
import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[2]

DB_PATH = BASE_DIR / "data" / "processed" / "transaction_risk.duckdb"
REPORTS_DIR = BASE_DIR / "reports"

REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def check_database_exists() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"DuckDB database not found at {DB_PATH}. "
            "Run Stage 2 first: python src\\database\\build_duckdb_database.py"
        )


def table_exists(con: duckdb.DuckDBPyConnection, table_name: str) -> bool:
    result = con.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_name = ?
        """,
        [table_name],
    ).fetchone()[0]

    return result > 0


def load_transactions(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    if table_exists(con, "ml_transaction_anomaly_scores"):
        table_name = "ml_transaction_anomaly_scores"
    elif table_exists(con, "transaction_risk_scores"):
        table_name = "transaction_risk_scores"
    else:
        table_name = "vw_transaction_enriched"

    df = con.execute(f"SELECT * FROM {table_name};").df()

    print(f"Loaded transactions from {table_name}: {len(df):,} rows")

    return df


def load_transfers(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    query = """
        SELECT
            t.*,
            sa.customer_id AS source_customer_id,
            da.customer_id AS destination_customer_id
        FROM account_transfers t
        LEFT JOIN accounts sa
            ON t.source_account_id = sa.account_id
        LEFT JOIN accounts da
            ON t.destination_account_id = da.account_id;
    """

    df = con.execute(query).df()

    print(f"Loaded account transfers: {len(df):,} rows")

    return df


def safe_numeric(df: pd.DataFrame, column: str, default_value: float = 0) -> pd.Series:
    if column not in df.columns:
        return pd.Series([default_value] * len(df))

    return pd.to_numeric(df[column], errors="coerce").fillna(default_value)


def ensure_transaction_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    defaults = {
        "rule_based_risk_score": 0,
        "risk_band": "Low",
        "anomaly_score_percentile": 0,
        "ml_anomaly_band": "Low",
        "watchlist_match_flag": 0,
        "should_create_alert": 0,
        "should_create_ml_alert": 0,
        "suspicious_label": 0,
        "amount": 0,
        "customer_id": "",
        "account_id": "",
        "merchant_id": "",
        "merchant_name": "",
        "merchant_category": "",
        "full_name": "",
        "customer_segment": "",
        "country_risk_level": "",
        "merchant_country_risk_level": "",
    }

    for column, default_value in defaults.items():
        if column not in df.columns:
            df[column] = default_value

    numeric_columns = [
        "rule_based_risk_score",
        "anomaly_score_percentile",
        "watchlist_match_flag",
        "should_create_alert",
        "should_create_ml_alert",
        "suspicious_label",
        "amount",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)

    return df


def create_graph_nodes(
    con: duckdb.DuckDBPyConnection,
    transactions: pd.DataFrame,
    transfers: pd.DataFrame,
) -> pd.DataFrame:
    transactions = ensure_transaction_columns(transactions)

    customers = con.execute("SELECT * FROM customers;").df()
    accounts = con.execute("SELECT * FROM accounts;").df()
    merchants = con.execute("SELECT * FROM merchants;").df()
    watchlist = con.execute("SELECT entity_id FROM watchlist;").df()

    watchlist_entities = set(watchlist["entity_id"].astype(str).tolist())

    customer_tx_summary = (
        transactions.groupby("customer_id")
        .agg(
            transaction_count=("transaction_id", "count"),
            total_transaction_amount=("amount", "sum"),
            max_rule_based_risk_score=("rule_based_risk_score", "max"),
            max_anomaly_score_percentile=("anomaly_score_percentile", "max"),
            alert_count=("should_create_alert", "sum"),
            ml_alert_count=("should_create_ml_alert", "sum"),
            suspicious_label_count=("suspicious_label", "sum"),
        )
        .reset_index()
    )

    merchant_tx_summary = (
        transactions.groupby("merchant_id")
        .agg(
            transaction_count=("transaction_id", "count"),
            total_transaction_amount=("amount", "sum"),
            max_rule_based_risk_score=("rule_based_risk_score", "max"),
            max_anomaly_score_percentile=("anomaly_score_percentile", "max"),
            alert_count=("should_create_alert", "sum"),
            ml_alert_count=("should_create_ml_alert", "sum"),
            suspicious_label_count=("suspicious_label", "sum"),
        )
        .reset_index()
    )

    account_tx_summary = (
        transactions.groupby("account_id")
        .agg(
            transaction_count=("transaction_id", "count"),
            total_transaction_amount=("amount", "sum"),
            max_rule_based_risk_score=("rule_based_risk_score", "max"),
            max_anomaly_score_percentile=("anomaly_score_percentile", "max"),
            alert_count=("should_create_alert", "sum"),
            ml_alert_count=("should_create_ml_alert", "sum"),
            suspicious_label_count=("suspicious_label", "sum"),
        )
        .reset_index()
    )

    transfer_source_summary = (
        transfers.groupby("source_account_id")
        .agg(
            outgoing_transfer_count=("transfer_id", "count"),
            outgoing_transfer_amount=("amount", "sum"),
        )
        .reset_index()
        .rename(columns={"source_account_id": "account_id"})
    )

    transfer_destination_summary = (
        transfers.groupby("destination_account_id")
        .agg(
            incoming_transfer_count=("transfer_id", "count"),
            incoming_transfer_amount=("amount", "sum"),
        )
        .reset_index()
        .rename(columns={"destination_account_id": "account_id"})
    )

    customer_nodes = customers.merge(
        customer_tx_summary,
        on="customer_id",
        how="left",
    )

    customer_nodes["node_id"] = customer_nodes["customer_id"]
    customer_nodes["node_type"] = "Customer"
    customer_nodes["node_label"] = customer_nodes["full_name"]
    customer_nodes["watchlist_flag"] = customer_nodes["customer_id"].isin(watchlist_entities).astype(int)

    merchant_nodes = merchants.merge(
        merchant_tx_summary,
        on="merchant_id",
        how="left",
    )

    merchant_nodes["node_id"] = merchant_nodes["merchant_id"]
    merchant_nodes["node_type"] = "Merchant"
    merchant_nodes["node_label"] = merchant_nodes["merchant_name"]
    merchant_nodes["watchlist_flag"] = merchant_nodes["merchant_id"].isin(watchlist_entities).astype(int)

    account_nodes = accounts.merge(
        account_tx_summary,
        on="account_id",
        how="left",
    )

    account_nodes = account_nodes.merge(
        transfer_source_summary,
        on="account_id",
        how="left",
    )

    account_nodes = account_nodes.merge(
        transfer_destination_summary,
        on="account_id",
        how="left",
    )

    account_nodes["node_id"] = account_nodes["account_id"]
    account_nodes["node_type"] = "Account"
    account_nodes["node_label"] = account_nodes["account_id"]
    account_nodes["watchlist_flag"] = 0

    common_columns = [
        "node_id",
        "node_type",
        "node_label",
        "watchlist_flag",
        "transaction_count",
        "total_transaction_amount",
        "max_rule_based_risk_score",
        "max_anomaly_score_percentile",
        "alert_count",
        "ml_alert_count",
        "suspicious_label_count",
    ]

    for df in [customer_nodes, merchant_nodes, account_nodes]:
        for column in common_columns:
            if column not in df.columns:
                df[column] = 0

    nodes = pd.concat(
        [
            customer_nodes[common_columns],
            merchant_nodes[common_columns],
            account_nodes[common_columns],
        ],
        ignore_index=True,
    )

    numeric_columns = [
        "watchlist_flag",
        "transaction_count",
        "total_transaction_amount",
        "max_rule_based_risk_score",
        "max_anomaly_score_percentile",
        "alert_count",
        "ml_alert_count",
        "suspicious_label_count",
    ]

    for column in numeric_columns:
        nodes[column] = pd.to_numeric(nodes[column], errors="coerce").fillna(0)

    nodes["node_risk_score"] = (
        nodes["max_rule_based_risk_score"] * 0.45
        + nodes["max_anomaly_score_percentile"] * 0.35
        + nodes["watchlist_flag"] * 10
        + nodes["alert_count"].clip(upper=10) * 1.5
        + nodes["ml_alert_count"].clip(upper=10) * 1.5
        + nodes["suspicious_label_count"].clip(upper=10) * 1.0
    ).clip(upper=100).round(2)

    nodes["node_risk_band"] = np.where(
        nodes["node_risk_score"] >= 80,
        "Critical",
        np.where(
            nodes["node_risk_score"] >= 60,
            "High",
            np.where(nodes["node_risk_score"] >= 35, "Medium", "Low"),
        ),
    )

    return nodes


def create_graph_edges(
    accounts: pd.DataFrame,
    transactions: pd.DataFrame,
    transfers: pd.DataFrame,
) -> pd.DataFrame:
    transactions = ensure_transaction_columns(transactions)

    ownership_edges = accounts[["customer_id", "account_id"]].copy()
    ownership_edges["source_node_id"] = ownership_edges["customer_id"]
    ownership_edges["target_node_id"] = ownership_edges["account_id"]
    ownership_edges["edge_type"] = "OWNS_ACCOUNT"
    ownership_edges["edge_count"] = 1
    ownership_edges["total_amount"] = 0.0
    ownership_edges["max_rule_based_risk_score"] = 0.0
    ownership_edges["max_anomaly_score_percentile"] = 0.0

    transaction_edges = (
        transactions.groupby(["account_id", "merchant_id"])
        .agg(
            edge_count=("transaction_id", "count"),
            total_amount=("amount", "sum"),
            max_rule_based_risk_score=("rule_based_risk_score", "max"),
            max_anomaly_score_percentile=("anomaly_score_percentile", "max"),
        )
        .reset_index()
    )

    transaction_edges["source_node_id"] = transaction_edges["account_id"]
    transaction_edges["target_node_id"] = transaction_edges["merchant_id"]
    transaction_edges["edge_type"] = "TRANSACTS_WITH"

    transfer_edges = (
        transfers.groupby(["source_account_id", "destination_account_id"])
        .agg(
            edge_count=("transfer_id", "count"),
            total_amount=("amount", "sum"),
            max_amount=("amount", "max"),
        )
        .reset_index()
    )

    transfer_edges["source_node_id"] = transfer_edges["source_account_id"]
    transfer_edges["target_node_id"] = transfer_edges["destination_account_id"]
    transfer_edges["edge_type"] = "TRANSFERS_TO"
    transfer_edges["max_rule_based_risk_score"] = 0.0
    transfer_edges["max_anomaly_score_percentile"] = 0.0

    common_columns = [
        "source_node_id",
        "target_node_id",
        "edge_type",
        "edge_count",
        "total_amount",
        "max_rule_based_risk_score",
        "max_anomaly_score_percentile",
    ]

    edges = pd.concat(
        [
            ownership_edges[common_columns],
            transaction_edges[common_columns],
            transfer_edges[common_columns],
        ],
        ignore_index=True,
    )

    edges["edge_id"] = [f"EDGE-{i + 1:08d}" for i in range(len(edges))]

    edges["total_amount"] = pd.to_numeric(edges["total_amount"], errors="coerce").fillna(0).round(2)

    edges["edge_risk_score"] = (
        pd.to_numeric(edges["max_rule_based_risk_score"], errors="coerce").fillna(0) * 0.50
        + pd.to_numeric(edges["max_anomaly_score_percentile"], errors="coerce").fillna(0) * 0.35
        + pd.to_numeric(edges["edge_count"], errors="coerce").fillna(0).clip(upper=20) * 0.75
    ).clip(upper=100).round(2)

    edges = edges[
        [
            "edge_id",
            "source_node_id",
            "target_node_id",
            "edge_type",
            "edge_count",
            "total_amount",
            "max_rule_based_risk_score",
            "max_anomaly_score_percentile",
            "edge_risk_score",
        ]
    ]

    return edges


def build_network_graph(nodes: pd.DataFrame, edges: pd.DataFrame) -> nx.DiGraph:
    graph = nx.DiGraph()

    for _, row in nodes.iterrows():
        graph.add_node(
            row["node_id"],
            node_type=row["node_type"],
            node_label=row["node_label"],
            node_risk_score=float(row["node_risk_score"]),
            node_risk_band=row["node_risk_band"],
            watchlist_flag=int(row["watchlist_flag"]),
        )

    for _, row in edges.iterrows():
        graph.add_edge(
            row["source_node_id"],
            row["target_node_id"],
            edge_type=row["edge_type"],
            weight=float(row["total_amount"]),
            edge_count=int(row["edge_count"]),
            edge_risk_score=float(row["edge_risk_score"]),
        )

    return graph


def add_centrality_metrics(graph: nx.DiGraph, nodes: pd.DataFrame) -> pd.DataFrame:
    nodes = nodes.copy()

    undirected_graph = graph.to_undirected()

    degree_centrality = nx.degree_centrality(undirected_graph)
    pagerank = nx.pagerank(graph, weight="weight", alpha=0.85)

    in_degree = dict(graph.in_degree())
    out_degree = dict(graph.out_degree())
    total_degree = dict(graph.degree())

    nodes["in_degree"] = nodes["node_id"].map(in_degree).fillna(0).astype(int)
    nodes["out_degree"] = nodes["node_id"].map(out_degree).fillna(0).astype(int)
    nodes["total_degree"] = nodes["node_id"].map(total_degree).fillna(0).astype(int)
    nodes["degree_centrality"] = nodes["node_id"].map(degree_centrality).fillna(0).round(6)
    nodes["pagerank_score"] = nodes["node_id"].map(pagerank).fillna(0).round(8)

    nodes["graph_priority_score"] = (
        nodes["node_risk_score"] * 0.60
        + nodes["degree_centrality"] * 100 * 0.20
        + nodes["pagerank_score"] * 1000 * 0.20
    ).clip(upper=100).round(2)

    nodes = nodes.sort_values(
        by=["graph_priority_score", "node_risk_score", "total_degree"],
        ascending=[False, False, False],
    ).reset_index(drop=True)

    return nodes


def create_cluster_summary(graph: nx.DiGraph, nodes: pd.DataFrame, edges: pd.DataFrame) -> pd.DataFrame:
    node_lookup = nodes.set_index("node_id").to_dict("index")
    rows = []

    components = list(nx.weakly_connected_components(graph))

    for index, component in enumerate(components, start=1):
        component_nodes = list(component)
        subgraph = graph.subgraph(component_nodes)

        component_node_df = nodes[nodes["node_id"].isin(component_nodes)]

        component_edges = edges[
            edges["source_node_id"].isin(component_nodes)
            & edges["target_node_id"].isin(component_nodes)
        ]

        node_type_counts = component_node_df["node_type"].value_counts().to_dict()

        max_node_risk = component_node_df["node_risk_score"].max() if not component_node_df.empty else 0
        average_node_risk = component_node_df["node_risk_score"].mean() if not component_node_df.empty else 0
        watchlist_node_count = int(component_node_df["watchlist_flag"].sum())
        high_risk_node_count = int(component_node_df["node_risk_band"].isin(["High", "Critical"]).sum())

        cluster_score = (
            max_node_risk * 0.45
            + average_node_risk * 0.20
            + min(watchlist_node_count, 5) * 6
            + min(high_risk_node_count, 10) * 2
            + min(len(component_nodes), 50) * 0.2
        )

        cluster_score = round(float(min(cluster_score, 100)), 2)

        if cluster_score >= 80:
            cluster_risk_band = "Critical"
        elif cluster_score >= 60:
            cluster_risk_band = "High"
        elif cluster_score >= 35:
            cluster_risk_band = "Medium"
        else:
            cluster_risk_band = "Low"

        top_nodes = (
            component_node_df.sort_values(
                by=["graph_priority_score", "node_risk_score"],
                ascending=[False, False],
            )["node_id"]
            .head(10)
            .tolist()
        )

        rows.append(
            {
                "cluster_id": f"GRAPH-CLUSTER-{index:05d}",
                "node_count": len(component_nodes),
                "edge_count": subgraph.number_of_edges(),
                "customer_count": int(node_type_counts.get("Customer", 0)),
                "account_count": int(node_type_counts.get("Account", 0)),
                "merchant_count": int(node_type_counts.get("Merchant", 0)),
                "watchlist_node_count": watchlist_node_count,
                "high_risk_node_count": high_risk_node_count,
                "max_node_risk_score": round(float(max_node_risk), 2),
                "average_node_risk_score": round(float(average_node_risk), 2),
                "total_edge_amount": round(float(component_edges["total_amount"].sum()), 2),
                "cluster_risk_score": cluster_score,
                "cluster_risk_band": cluster_risk_band,
                "top_priority_nodes": "; ".join(top_nodes),
            }
        )

    clusters = pd.DataFrame(rows)

    clusters = clusters.sort_values(
        by=["cluster_risk_score", "node_count", "total_edge_amount"],
        ascending=[False, False, False],
    ).reset_index(drop=True)

    return clusters


def create_suspicious_transfer_patterns(transfers: pd.DataFrame) -> pd.DataFrame:
    rows = []

    pair_summary = (
        transfers.groupby(
            [
                "source_account_id",
                "destination_account_id",
                "source_customer_id",
                "destination_customer_id",
            ],
            dropna=False,
        )
        .agg(
            transfer_count=("transfer_id", "count"),
            total_amount=("amount", "sum"),
            max_amount=("amount", "max"),
        )
        .reset_index()
    )

    pair_lookup = {
        (row["source_account_id"], row["destination_account_id"]): row
        for _, row in pair_summary.iterrows()
    }

    seen_pairs = set()

    for _, row in pair_summary.iterrows():
        source = row["source_account_id"]
        destination = row["destination_account_id"]
        reverse_key = (destination, source)

        if reverse_key in pair_lookup and tuple(sorted([source, destination])) not in seen_pairs:
            reverse = pair_lookup[reverse_key]
            seen_pairs.add(tuple(sorted([source, destination])))

            combined_amount = float(row["total_amount"]) + float(reverse["total_amount"])
            combined_count = int(row["transfer_count"]) + int(reverse["transfer_count"])

            rows.append(
                {
                    "pattern_type": "RECIPROCAL_TRANSFERS",
                    "source_account_id": source,
                    "destination_account_id": destination,
                    "source_customer_id": row["source_customer_id"],
                    "destination_customer_id": row["destination_customer_id"],
                    "transfer_count": combined_count,
                    "total_amount": round(combined_amount, 2),
                    "max_amount": round(max(float(row["max_amount"]), float(reverse["max_amount"])), 2),
                    "pattern_risk_score": min(100, 40 + min(combined_count, 20) * 2 + min(combined_amount / 1000, 40)),
                    "pattern_explanation": "Two accounts send funds to each other, creating a reciprocal transfer pattern.",
                    "recommended_action": "Review whether transfers have a legitimate purpose or indicate circular fund movement.",
                }
            )

    outgoing_summary = (
        transfers.groupby(["source_account_id", "source_customer_id"])
        .agg(
            transfer_count=("transfer_id", "count"),
            unique_destinations=("destination_account_id", "nunique"),
            total_amount=("amount", "sum"),
            max_amount=("amount", "max"),
        )
        .reset_index()
    )

    outgoing_count_threshold = max(5, outgoing_summary["transfer_count"].quantile(0.95))
    outgoing_amount_threshold = outgoing_summary["total_amount"].quantile(0.95)

    high_outgoing = outgoing_summary[
        (outgoing_summary["transfer_count"] >= outgoing_count_threshold)
        | (outgoing_summary["total_amount"] >= outgoing_amount_threshold)
    ]

    for _, row in high_outgoing.iterrows():
        rows.append(
            {
                "pattern_type": "HIGH_OUTBOUND_TRANSFER_HUB",
                "source_account_id": row["source_account_id"],
                "destination_account_id": "",
                "source_customer_id": row["source_customer_id"],
                "destination_customer_id": "",
                "transfer_count": int(row["transfer_count"]),
                "total_amount": round(float(row["total_amount"]), 2),
                "max_amount": round(float(row["max_amount"]), 2),
                "pattern_risk_score": min(
                    100,
                    35
                    + min(float(row["transfer_count"]), 30)
                    + min(float(row["total_amount"]) / 1500, 35),
                ),
                "pattern_explanation": "One account sends funds to many destinations or sends unusually high total transfer value.",
                "recommended_action": "Review outgoing transfer activity and verify customer purpose.",
            }
        )

    incoming_summary = (
        transfers.groupby(["destination_account_id", "destination_customer_id"])
        .agg(
            transfer_count=("transfer_id", "count"),
            unique_sources=("source_account_id", "nunique"),
            total_amount=("amount", "sum"),
            max_amount=("amount", "max"),
        )
        .reset_index()
    )

    incoming_source_threshold = max(5, incoming_summary["unique_sources"].quantile(0.95))
    incoming_amount_threshold = incoming_summary["total_amount"].quantile(0.95)

    high_incoming = incoming_summary[
        (incoming_summary["unique_sources"] >= incoming_source_threshold)
        | (incoming_summary["total_amount"] >= incoming_amount_threshold)
    ]

    for _, row in high_incoming.iterrows():
        rows.append(
            {
                "pattern_type": "HIGH_INBOUND_COLLECTION_HUB",
                "source_account_id": "",
                "destination_account_id": row["destination_account_id"],
                "source_customer_id": "",
                "destination_customer_id": row["destination_customer_id"],
                "transfer_count": int(row["transfer_count"]),
                "total_amount": round(float(row["total_amount"]), 2),
                "max_amount": round(float(row["max_amount"]), 2),
                "pattern_risk_score": min(
                    100,
                    35
                    + min(float(row["unique_sources"]) * 4, 30)
                    + min(float(row["total_amount"]) / 1500, 35),
                ),
                "pattern_explanation": "One account receives funds from many sources or receives unusually high total transfer value.",
                "recommended_action": "Review whether this account is acting as a collection point.",
            }
        )

    patterns = pd.DataFrame(rows)

    if patterns.empty:
        patterns = pd.DataFrame(
            columns=[
                "pattern_id",
                "pattern_type",
                "source_account_id",
                "destination_account_id",
                "source_customer_id",
                "destination_customer_id",
                "transfer_count",
                "total_amount",
                "max_amount",
                "pattern_risk_score",
                "pattern_explanation",
                "recommended_action",
            ]
        )
        return patterns

    patterns["pattern_risk_score"] = pd.to_numeric(
        patterns["pattern_risk_score"],
        errors="coerce",
    ).fillna(0).round(2)

    patterns = patterns.sort_values(
        by=["pattern_risk_score", "total_amount", "transfer_count"],
        ascending=[False, False, False],
    ).reset_index(drop=True)

    patterns.insert(
        0,
        "pattern_id",
        [f"GRAPH-PATTERN-{i + 1:06d}" for i in range(len(patterns))],
    )

    return patterns


def create_high_centrality_entities(nodes: pd.DataFrame) -> pd.DataFrame:
    high_centrality = nodes[
        (nodes["total_degree"] >= nodes["total_degree"].quantile(0.95))
        | (nodes["graph_priority_score"] >= nodes["graph_priority_score"].quantile(0.95))
        | (nodes["node_risk_band"].isin(["High", "Critical"]))
    ].copy()

    high_centrality = high_centrality.sort_values(
        by=["graph_priority_score", "total_degree", "node_risk_score"],
        ascending=[False, False, False],
    ).reset_index(drop=True)

    high_centrality.insert(
        0,
        "centrality_case_id",
        [f"CENTRALITY-{i + 1:06d}" for i in range(len(high_centrality))],
    )

    high_centrality["recommended_action"] = np.where(
        high_centrality["node_risk_band"].isin(["High", "Critical"]),
        "Review high-risk graph entity and connected transaction network.",
        "Monitor central graph entity because it is highly connected.",
    )

    return high_centrality


def save_to_duckdb(
    con: duckdb.DuckDBPyConnection,
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    clusters: pd.DataFrame,
    patterns: pd.DataFrame,
    high_centrality: pd.DataFrame,
) -> None:
    con.register("graph_nodes_df", nodes)
    con.register("graph_edges_df", edges)
    con.register("graph_risk_clusters_df", clusters)
    con.register("graph_suspicious_transfer_patterns_df", patterns)
    con.register("graph_high_centrality_entities_df", high_centrality)

    con.execute(
        """
        CREATE OR REPLACE TABLE graph_nodes AS
        SELECT *
        FROM graph_nodes_df;
        """
    )

    con.execute(
        """
        CREATE OR REPLACE TABLE graph_edges AS
        SELECT *
        FROM graph_edges_df;
        """
    )

    con.execute(
        """
        CREATE OR REPLACE TABLE graph_risk_clusters AS
        SELECT *
        FROM graph_risk_clusters_df;
        """
    )

    con.execute(
        """
        CREATE OR REPLACE TABLE graph_suspicious_transfer_patterns AS
        SELECT *
        FROM graph_suspicious_transfer_patterns_df;
        """
    )

    con.execute(
        """
        CREATE OR REPLACE TABLE graph_high_centrality_entities AS
        SELECT *
        FROM graph_high_centrality_entities_df;
        """
    )

    con.execute(
        """
        CREATE OR REPLACE VIEW vw_graph_entity_risk_summary AS
        SELECT
            node_type,
            node_risk_band,
            COUNT(*) AS entity_count,
            ROUND(AVG(node_risk_score), 2) AS average_node_risk_score,
            ROUND(AVG(total_degree), 2) AS average_total_degree,
            SUM(watchlist_flag) AS watchlist_entity_count
        FROM graph_nodes
        GROUP BY node_type, node_risk_band
        ORDER BY average_node_risk_score DESC;
        """
    )

    con.execute(
        """
        CREATE OR REPLACE VIEW vw_graph_cluster_summary AS
        SELECT
            cluster_risk_band,
            COUNT(*) AS cluster_count,
            ROUND(AVG(cluster_risk_score), 2) AS average_cluster_risk_score,
            SUM(node_count) AS total_nodes,
            SUM(edge_count) AS total_edges,
            SUM(watchlist_node_count) AS total_watchlist_nodes,
            ROUND(SUM(total_edge_amount), 2) AS total_edge_amount
        FROM graph_risk_clusters
        GROUP BY cluster_risk_band
        ORDER BY average_cluster_risk_score DESC;
        """
    )

    print("Saved graph analytics tables and views to DuckDB")


def save_reports(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    clusters: pd.DataFrame,
    patterns: pd.DataFrame,
    high_centrality: pd.DataFrame,
) -> None:
    nodes_path = REPORTS_DIR / "stage8_graph_nodes.csv"
    edges_path = REPORTS_DIR / "stage8_graph_edges.csv"
    clusters_path = REPORTS_DIR / "stage8_graph_risk_clusters.csv"
    patterns_path = REPORTS_DIR / "stage8_suspicious_transfer_patterns.csv"
    centrality_path = REPORTS_DIR / "stage8_high_centrality_entities.csv"
    summary_path = REPORTS_DIR / "stage8_graph_analytics_summary.json"

    nodes.to_csv(nodes_path, index=False)
    edges.to_csv(edges_path, index=False)
    clusters.to_csv(clusters_path, index=False)
    patterns.to_csv(patterns_path, index=False)
    high_centrality.to_csv(centrality_path, index=False)

    summary = {
        "run_timestamp": datetime.now().isoformat(timespec="seconds"),
        "nodes_created": int(len(nodes)),
        "edges_created": int(len(edges)),
        "clusters_detected": int(len(clusters)),
        "suspicious_transfer_patterns_detected": int(len(patterns)),
        "high_centrality_entities_detected": int(len(high_centrality)),
        "customer_nodes": int((nodes["node_type"] == "Customer").sum()),
        "account_nodes": int((nodes["node_type"] == "Account").sum()),
        "merchant_nodes": int((nodes["node_type"] == "Merchant").sum()),
        "critical_nodes": int((nodes["node_risk_band"] == "Critical").sum()),
        "high_risk_nodes": int((nodes["node_risk_band"] == "High").sum()),
        "critical_clusters": int((clusters["cluster_risk_band"] == "Critical").sum()),
        "high_risk_clusters": int((clusters["cluster_risk_band"] == "High").sum()),
    }

    summary_path.write_text(json.dumps(summary, indent=4))

    print(f"Saved {nodes_path}")
    print(f"Saved {edges_path}")
    print(f"Saved {clusters_path}")
    print(f"Saved {patterns_path}")
    print(f"Saved {centrality_path}")
    print(f"Saved {summary_path}")


def print_console_summary(
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    clusters: pd.DataFrame,
    patterns: pd.DataFrame,
    high_centrality: pd.DataFrame,
) -> None:
    print("\nGraph Node Summary")
    print("------------------")
    print(nodes["node_type"].value_counts().to_string())

    print("\nGraph Edge Summary")
    print("------------------")
    print(edges["edge_type"].value_counts().to_string())

    print("\nCluster Risk Summary")
    print("--------------------")
    print(clusters["cluster_risk_band"].value_counts().to_string())

    print("\nTop 10 High Centrality / High Risk Entities")
    print("-------------------------------------------")
    print(
        high_centrality[
            [
                "centrality_case_id",
                "node_id",
                "node_type",
                "node_risk_band",
                "node_risk_score",
                "total_degree",
                "graph_priority_score",
            ]
        ]
        .head(10)
        .to_string(index=False)
    )

    print("\nTop 10 Suspicious Transfer Patterns")
    print("-----------------------------------")
    if patterns.empty:
        print("No suspicious transfer patterns detected.")
    else:
        print(
            patterns[
                [
                    "pattern_id",
                    "pattern_type",
                    "source_account_id",
                    "destination_account_id",
                    "transfer_count",
                    "total_amount",
                    "pattern_risk_score",
                ]
            ]
            .head(10)
            .to_string(index=False)
        )


def main() -> None:
    check_database_exists()

    print(f"Running Stage 8 graph analytics against: {DB_PATH}")

    with duckdb.connect(str(DB_PATH)) as con:
        transactions = load_transactions(con)
        transfers = load_transfers(con)
        accounts = con.execute("SELECT * FROM accounts;").df()

        nodes = create_graph_nodes(con, transactions, transfers)
        edges = create_graph_edges(accounts, transactions, transfers)

        graph = build_network_graph(nodes, edges)

        nodes = add_centrality_metrics(graph, nodes)
        clusters = create_cluster_summary(graph, nodes, edges)
        patterns = create_suspicious_transfer_patterns(transfers)
        high_centrality = create_high_centrality_entities(nodes)

        save_to_duckdb(con, nodes, edges, clusters, patterns, high_centrality)
        save_reports(nodes, edges, clusters, patterns, high_centrality)
        print_console_summary(nodes, edges, clusters, patterns, high_centrality)

    print("\nStage 8 graph analytics completed successfully")


if __name__ == "__main__":
    main()