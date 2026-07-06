-- Stage 4 data quality analysis queries

-- 1. Overall data quality status summary
SELECT
    status,
    COUNT(*) AS check_count
FROM data_quality_results
GROUP BY status
ORDER BY status;


-- 2. Data quality summary by status, severity and check type
SELECT
    status,
    severity,
    check_type,
    COUNT(*) AS check_count,
    SUM(CASE WHEN failure_count > 0 THEN failure_count ELSE 0 END) AS total_failure_count
FROM data_quality_results
GROUP BY status, severity, check_type
ORDER BY status, severity, check_type;


-- 3. Warnings, failures and errors
SELECT
    check_id,
    check_name,
    table_name,
    check_type,
    severity,
    failure_count,
    status,
    recommended_action
FROM data_quality_results
WHERE status IN ('WARN', 'FAIL', 'ERROR')
ORDER BY
    CASE status
        WHEN 'FAIL' THEN 1
        WHEN 'ERROR' THEN 2
        WHEN 'WARN' THEN 3
        ELSE 4
    END,
    failure_count DESC;


-- 4. Critical checks
SELECT
    check_id,
    check_name,
    table_name,
    check_type,
    failure_count,
    status,
    recommended_action
FROM data_quality_results
WHERE severity = 'Critical'
ORDER BY status, check_id;


-- 5. Referential integrity checks
SELECT
    check_id,
    check_name,
    table_name,
    failure_count,
    status,
    recommended_action
FROM data_quality_results
WHERE check_type = 'referential_integrity'
ORDER BY status, check_id;


-- 6. Data quality dashboard view
SELECT *
FROM vw_data_quality_summary;