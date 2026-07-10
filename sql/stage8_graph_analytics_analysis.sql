-- Stage 8 graph analytics analysis queries

-- 1. Graph entity risk summary
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


-- 2. Top high-risk / high-centrality entities
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
ORDER BY graph_priority_score DESC
LIMIT 25;


-- 3. Graph edge summary
SELECT
    edge_type,
    COUNT(*) AS edge_count,
    ROUND(SUM(total_amount), 2) AS total_amount,
    ROUND(AVG(edge_risk_score), 2) AS average_edge_risk_score,
    MAX(edge_risk_score) AS max_edge_risk_score
FROM graph_edges
GROUP BY edge_type
ORDER BY edge_count DESC;


-- 4. Risk cluster summary
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


-- 5. Top risky graph clusters
SELECT
    cluster_id,
    node_count,
    edge_count,
    customer_count,
    account_count,
    merchant_count,
    watchlist_node_count,
    high_risk_node_count,
    max_node_risk_score,
    average_node_risk_score,
    total_edge_amount,
    cluster_risk_score,
    cluster_risk_band,
    top_priority_nodes
FROM graph_risk_clusters
ORDER BY cluster_risk_score DESC, node_count DESC
LIMIT 25;


-- 6. Suspicious transfer patterns
SELECT
    pattern_id,
    pattern_type,
    source_account_id,
    destination_account_id,
    source_customer_id,
    destination_customer_id,
    transfer_count,
    total_amount,
    max_amount,
    pattern_risk_score,
    pattern_explanation,
    recommended_action
FROM graph_suspicious_transfer_patterns
ORDER BY pattern_risk_score DESC, total_amount DESC;


-- 7. Reciprocal transfer patterns only
SELECT
    pattern_id,
    source_account_id,
    destination_account_id,
    source_customer_id,
    destination_customer_id,
    transfer_count,
    total_amount,
    pattern_risk_score,
    recommended_action
FROM graph_suspicious_transfer_patterns
WHERE pattern_type = 'RECIPROCAL_TRANSFERS'
ORDER BY pattern_risk_score DESC;


-- 8. High outbound transfer hubs
SELECT
    pattern_id,
    source_account_id,
    source_customer_id,
    transfer_count,
    total_amount,
    max_amount,
    pattern_risk_score,
    recommended_action
FROM graph_suspicious_transfer_patterns
WHERE pattern_type = 'HIGH_OUTBOUND_TRANSFER_HUB'
ORDER BY pattern_risk_score DESC;


-- 9. High inbound collection hubs
SELECT
    pattern_id,
    destination_account_id,
    destination_customer_id,
    transfer_count,
    total_amount,
    max_amount,
    pattern_risk_score,
    recommended_action
FROM graph_suspicious_transfer_patterns
WHERE pattern_type = 'HIGH_INBOUND_COLLECTION_HUB'
ORDER BY pattern_risk_score DESC;


-- 10. Dashboard-ready graph entity risk summary
SELECT *
FROM vw_graph_entity_risk_summary;


-- 11. Dashboard-ready graph cluster summary
SELECT *
FROM vw_graph_cluster_summary;