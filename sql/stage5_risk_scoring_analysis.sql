-- Stage 5 rule-based risk scoring analysis queries

-- 1. Transaction risk band summary
SELECT
    risk_band,
    alert_priority,
    COUNT(*) AS transaction_count,
    ROUND(SUM(amount), 2) AS total_amount,
    ROUND(AVG(rule_based_risk_score), 2) AS average_risk_score
FROM transaction_risk_scores
GROUP BY risk_band, alert_priority
ORDER BY average_risk_score DESC;


-- 2. Customer risk band summary
SELECT
    customer_risk_band,
    customer_review_priority,
    COUNT(*) AS customer_count,
    ROUND(AVG(customer_rule_based_risk_score), 2) AS average_customer_score,
    SUM(alert_count) AS total_alerts
FROM customer_risk_scores
GROUP BY customer_risk_band, customer_review_priority
ORDER BY average_customer_score DESC;


-- 3. Top 25 highest-risk transactions
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
ORDER BY rule_based_risk_score DESC, amount DESC
LIMIT 25;


-- 4. Open transaction risk alerts
SELECT
    alert_id,
    alert_priority,
    alert_owner,
    transaction_id,
    customer_id,
    full_name,
    amount,
    risk_band,
    rule_based_risk_score,
    reason_codes,
    recommended_action
FROM transaction_risk_alerts
WHERE alert_status = 'Open'
ORDER BY rule_based_risk_score DESC, amount DESC;


-- 5. Watchlist matched risk transactions
SELECT
    transaction_id,
    customer_id,
    full_name,
    merchant_id,
    merchant_name,
    amount,
    risk_band,
    rule_based_risk_score,
    watchlist_type,
    watchlist_risk_reason,
    reason_codes
FROM transaction_risk_scores
WHERE watchlist_match_flag = 1
ORDER BY rule_based_risk_score DESC, amount DESC;


-- 6. Top 25 highest-risk customers
SELECT
    customer_id,
    full_name,
    customer_segment,
    customer_country,
    country_risk_level,
    kyc_status,
    pep_flag,
    transaction_count,
    alert_count,
    critical_transaction_count,
    high_transaction_count,
    total_transaction_amount,
    customer_rule_based_risk_score,
    customer_risk_band,
    customer_review_priority
FROM customer_risk_scores
ORDER BY customer_rule_based_risk_score DESC, alert_count DESC
LIMIT 25;


-- 7. Most common reason-code combinations
SELECT
    reason_codes,
    COUNT(*) AS transaction_count,
    ROUND(AVG(rule_based_risk_score), 2) AS average_risk_score,
    ROUND(SUM(amount), 2) AS total_amount
FROM transaction_risk_scores
WHERE should_create_alert = 1
GROUP BY reason_codes
ORDER BY transaction_count DESC
LIMIT 25;


-- 8. Dashboard-ready transaction risk summary
SELECT *
FROM vw_transaction_risk_summary;


-- 9. Dashboard-ready customer risk summary
SELECT *
FROM vw_customer_risk_summary;