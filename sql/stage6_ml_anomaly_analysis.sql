-- Stage 6 ML anomaly detection analysis queries

-- 1. ML anomaly band summary
SELECT
    ml_anomaly_band,
    ml_alert_priority,
    COUNT(*) AS transaction_count,
    ROUND(AVG(anomaly_score_percentile), 2) AS average_anomaly_percentile,
    ROUND(AVG(rule_based_risk_score), 2) AS average_rule_score,
    ROUND(SUM(amount), 2) AS total_amount
FROM ml_transaction_anomaly_scores
GROUP BY ml_anomaly_band, ml_alert_priority
ORDER BY average_anomaly_percentile DESC;


-- 2. Rule-based vs ML signal comparison
SELECT
    combined_risk_signal,
    COUNT(*) AS transaction_count,
    ROUND(AVG(rule_based_risk_score), 2) AS average_rule_score,
    ROUND(AVG(anomaly_score_percentile), 2) AS average_anomaly_percentile,
    SUM(suspicious_label) AS known_suspicious_label_count
FROM ml_transaction_anomaly_scores
GROUP BY combined_risk_signal
ORDER BY transaction_count DESC;


-- 3. Top 25 ML anomaly transactions
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
    ml_anomaly_score,
    anomaly_score_percentile,
    ml_anomaly_band,
    combined_risk_signal,
    ml_reason_codes
FROM ml_transaction_anomaly_scores
ORDER BY anomaly_score_percentile DESC, rule_based_risk_score DESC, amount DESC
LIMIT 25;


-- 4. ML anomaly alerts
SELECT
    ml_alert_id,
    ml_alert_priority,
    ml_alert_owner,
    transaction_id,
    customer_id,
    full_name,
    amount,
    ml_anomaly_band,
    anomaly_score_percentile,
    rule_based_risk_score,
    combined_risk_signal,
    ml_reason_codes,
    ml_recommended_action
FROM ml_transaction_anomaly_alerts
WHERE ml_alert_status = 'Open'
ORDER BY anomaly_score_percentile DESC, rule_based_risk_score DESC;


-- 5. ML-only alerts
SELECT
    ml_alert_id,
    transaction_id,
    customer_id,
    full_name,
    merchant_name,
    amount,
    channel,
    ml_anomaly_band,
    anomaly_score_percentile,
    rule_based_risk_score,
    combined_risk_signal,
    ml_reason_codes
FROM ml_transaction_anomaly_alerts
WHERE combined_risk_signal = 'ML Only'
ORDER BY anomaly_score_percentile DESC;


-- 6. Rule and ML agreement alerts
SELECT
    ml_alert_id,
    transaction_id,
    customer_id,
    full_name,
    merchant_name,
    amount,
    risk_band,
    rule_based_risk_score,
    ml_anomaly_band,
    anomaly_score_percentile,
    combined_risk_signal,
    ml_reason_codes
FROM ml_transaction_anomaly_alerts
WHERE combined_risk_signal = 'Rule and ML'
ORDER BY anomaly_score_percentile DESC, rule_based_risk_score DESC;


-- 7. Highest anomaly customers
SELECT
    customer_id,
    full_name,
    customer_segment,
    customer_country,
    transaction_count,
    ml_alert_count,
    ml_anomaly_count,
    max_anomaly_score_percentile,
    average_rule_based_risk_score,
    max_rule_based_risk_score,
    total_amount,
    customer_ml_review_priority
FROM ml_customer_anomaly_summary
ORDER BY max_anomaly_score_percentile DESC, ml_alert_count DESC
LIMIT 25;


-- 8. Dashboard-ready ML anomaly summary
SELECT *
FROM vw_ml_anomaly_summary;


-- 9. Dashboard-ready ML vs rule summary
SELECT *
FROM vw_ml_vs_rule_summary;