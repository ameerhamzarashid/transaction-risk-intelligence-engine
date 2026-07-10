-- Stage 9 case management analysis queries

-- 1. Case priority summary
SELECT
    case_priority,
    case_status,
    sla_status,
    COUNT(*) AS case_count,
    ROUND(AVG(risk_score), 2) AS average_risk_score,
    ROUND(SUM(amount), 2) AS total_amount,
    MAX(case_age_days) AS oldest_case_age_days
FROM case_management_cases
GROUP BY case_priority, case_status, sla_status
ORDER BY
    CASE case_priority
        WHEN 'P1' THEN 1
        WHEN 'P2' THEN 2
        WHEN 'P3' THEN 3
        WHEN 'P4' THEN 4
        ELSE 9
    END,
    case_count DESC;


-- 2. Case source summary
SELECT
    case_source_type,
    case_priority,
    COUNT(*) AS case_count,
    ROUND(AVG(risk_score), 2) AS average_risk_score,
    ROUND(SUM(amount), 2) AS total_amount,
    SUM(CASE WHEN sla_status = 'Breached' THEN 1 ELSE 0 END) AS breached_cases,
    SUM(CASE WHEN sla_status = 'At Risk' THEN 1 ELSE 0 END) AS at_risk_cases
FROM case_management_cases
GROUP BY case_source_type, case_priority
ORDER BY case_source_type, case_priority;


-- 3. Analyst owner queue
SELECT
    case_owner,
    case_priority,
    COUNT(*) AS open_case_count,
    ROUND(AVG(risk_score), 2) AS average_risk_score,
    MAX(case_age_days) AS oldest_case_age_days,
    SUM(CASE WHEN sla_status = 'Breached' THEN 1 ELSE 0 END) AS breached_cases,
    SUM(CASE WHEN sla_status = 'At Risk' THEN 1 ELSE 0 END) AS at_risk_cases
FROM case_management_cases
WHERE case_status = 'Open'
GROUP BY case_owner, case_priority
ORDER BY open_case_count DESC;


-- 4. Prioritised work queue
SELECT
    queue_rank,
    case_id,
    case_source_type,
    case_priority,
    case_status,
    sla_status,
    case_owner,
    case_title,
    customer_id,
    transaction_id,
    account_id,
    merchant_id,
    amount,
    risk_score,
    risk_band,
    case_age_days,
    case_age_bucket,
    created_at,
    sla_due_at,
    main_trigger,
    recommended_action
FROM case_management_work_queue
ORDER BY queue_rank;


-- 5. P1 cases
SELECT
    case_id,
    case_source_type,
    case_priority,
    sla_status,
    case_owner,
    case_title,
    case_description,
    customer_id,
    transaction_id,
    amount,
    risk_score,
    created_at,
    sla_due_at,
    recommended_action
FROM case_management_cases
WHERE case_priority = 'P1'
ORDER BY risk_score DESC, amount DESC;


-- 6. Breached or at-risk SLA cases
SELECT
    case_id,
    case_source_type,
    case_priority,
    sla_status,
    case_owner,
    case_title,
    risk_score,
    case_age_days,
    created_at,
    sla_due_at,
    recommended_action
FROM case_management_cases
WHERE sla_status IN ('Breached', 'At Risk')
ORDER BY
    CASE sla_status
        WHEN 'Breached' THEN 1
        WHEN 'At Risk' THEN 2
        ELSE 3
    END,
    risk_score DESC;


-- 7. Aged open cases
SELECT
    case_id,
    case_source_type,
    case_priority,
    case_owner,
    case_title,
    case_age_days,
    case_age_bucket,
    risk_score,
    recommended_action
FROM case_management_cases
WHERE case_status = 'Open'
ORDER BY case_age_days DESC, risk_score DESC
LIMIT 50;


-- 8. Customer case concentration
SELECT
    customer_id,
    customer_name,
    COUNT(*) AS case_count,
    SUM(CASE WHEN case_priority = 'P1' THEN 1 ELSE 0 END) AS p1_cases,
    SUM(CASE WHEN case_priority = 'P2' THEN 1 ELSE 0 END) AS p2_cases,
    ROUND(SUM(amount), 2) AS total_case_amount,
    ROUND(AVG(risk_score), 2) AS average_risk_score,
    MAX(risk_score) AS max_risk_score
FROM case_management_cases
WHERE customer_id IS NOT NULL
  AND customer_id <> ''
GROUP BY customer_id, customer_name
ORDER BY case_count DESC, max_risk_score DESC
LIMIT 25;


-- 9. Transaction case concentration
SELECT
    transaction_id,
    COUNT(*) AS case_count,
    STRING_AGG(DISTINCT case_source_type, '; ') AS case_sources,
    MAX(case_priority) AS max_priority,
    ROUND(MAX(risk_score), 2) AS max_risk_score,
    ROUND(SUM(amount), 2) AS total_amount
FROM case_management_cases
WHERE transaction_id IS NOT NULL
  AND transaction_id <> ''
GROUP BY transaction_id
HAVING COUNT(*) > 1
ORDER BY case_count DESC, max_risk_score DESC
LIMIT 25;


-- 10. Dashboard-ready priority summary
SELECT *
FROM vw_case_management_priority_summary;


-- 11. Dashboard-ready source summary
SELECT *
FROM vw_case_management_source_summary;


-- 12. Dashboard-ready owner queue
SELECT *
FROM vw_case_management_owner_queue;