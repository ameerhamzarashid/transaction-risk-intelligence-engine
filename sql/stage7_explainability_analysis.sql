-- Stage 7 explainability analysis queries

-- 1. Explainability priority summary
SELECT
    explanation_priority,
    review_queue,
    main_trigger,
    COUNT(*) AS alert_count,
    ROUND(AVG(combined_explanation_score), 2) AS average_combined_score,
    ROUND(SUM(amount), 2) AS total_amount
FROM alert_explanations
GROUP BY explanation_priority, review_queue, main_trigger
ORDER BY average_combined_score DESC;


-- 2. Top plain-English alert explanations
SELECT
    explanation_id,
    explanation_priority,
    review_queue,
    main_trigger,
    transaction_id,
    customer_id,
    full_name,
    amount,
    currency,
    combined_explanation_score,
    plain_english_explanation,
    recommended_investigation_action
FROM alert_explanations
ORDER BY combined_explanation_score DESC
LIMIT 25;


-- 3. Most common explanation reasons
SELECT
    reason_source,
    reason_code,
    human_reason,
    transaction_count,
    average_combined_explanation_score,
    p1_count,
    p2_count,
    p3_count
FROM explanation_reason_summary
ORDER BY transaction_count DESC, average_combined_explanation_score DESC;


-- 4. P1 critical explanations
SELECT
    explanation_id,
    transaction_id,
    customer_id,
    full_name,
    merchant_name,
    merchant_category,
    amount,
    currency,
    rule_based_risk_score,
    anomaly_score_percentile,
    reconciliation_break_type,
    combined_explanation_score,
    plain_english_explanation,
    recommended_investigation_action
FROM alert_explanations
WHERE explanation_priority = 'P1'
ORDER BY combined_explanation_score DESC;


-- 5. Rule + ML agreement explanations
SELECT
    explanation_id,
    transaction_id,
    customer_id,
    full_name,
    amount,
    rule_based_risk_score,
    anomaly_score_percentile,
    main_trigger,
    evidence_summary,
    plain_english_explanation
FROM alert_explanations
WHERE main_trigger LIKE '%Rule%ML%'
ORDER BY combined_explanation_score DESC;


-- 6. Reconciliation-linked explanations
SELECT
    explanation_id,
    transaction_id,
    customer_id,
    full_name,
    amount,
    reconciliation_case_id,
    reconciliation_break_type,
    reconciliation_severity,
    reconciliation_case_age_days,
    plain_english_explanation,
    recommended_investigation_action
FROM alert_explanations
WHERE reconciliation_case_id IS NOT NULL
  AND reconciliation_case_id <> ''
ORDER BY combined_explanation_score DESC;


-- 7. Customer explanation summary
SELECT
    customer_id,
    full_name,
    alert_explanation_count,
    p1_alerts,
    p2_alerts,
    p3_alerts,
    max_combined_explanation_score,
    average_combined_explanation_score,
    total_alert_amount,
    customer_explanation_priority
FROM customer_explanation_summary
ORDER BY max_combined_explanation_score DESC, alert_explanation_count DESC
LIMIT 25;


-- 8. Dashboard-ready explainability priority summary
SELECT *
FROM vw_explainability_priority_summary;


-- 9. Dashboard-ready top explanation reasons
SELECT *
FROM vw_top_explanation_reasons;