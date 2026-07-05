-- Stage 3 reconciliation analysis queries

-- 1. Overall reconciliation status
SELECT
    reconciliation_status,
    COUNT(*) AS record_count
FROM reconciliation_results
GROUP BY reconciliation_status
ORDER BY record_count DESC;


-- 2. Break summary by category and severity
SELECT
    primary_break_category,
    severity,
    COUNT(*) AS break_count,
    ROUND(SUM(COALESCE(absolute_amount_difference, 0)), 2) AS total_absolute_amount_difference,
    ROUND(AVG(case_age_days), 2) AS average_case_age_days
FROM reconciliation_breaks
GROUP BY primary_break_category, severity
ORDER BY break_count DESC;


-- 3. High-severity reconciliation breaks
SELECT
    case_id,
    transaction_id,
    break_type,
    severity,
    a_amount,
    b_amount,
    amount_difference,
    a_booking_date,
    b_booking_date,
    case_age_days,
    recommended_action
FROM reconciliation_breaks
WHERE severity = 'High'
ORDER BY absolute_amount_difference DESC;


-- 4. Amount mismatch cases
SELECT
    case_id,
    transaction_id,
    a_amount,
    b_amount,
    amount_difference,
    absolute_amount_difference,
    severity,
    recommended_action
FROM reconciliation_breaks
WHERE break_type LIKE '%AMOUNT_MISMATCH%'
ORDER BY absolute_amount_difference DESC;


-- 5. Missing records
SELECT
    case_id,
    transaction_id,
    break_type,
    severity,
    a_recon_references,
    b_recon_references,
    recommended_action
FROM reconciliation_breaks
WHERE break_type IN ('MISSING_IN_A', 'MISSING_IN_B')
ORDER BY break_type, transaction_id;


-- 6. Duplicate cases
SELECT
    case_id,
    transaction_id,
    break_type,
    severity,
    a_record_count,
    b_record_count,
    recommended_action
FROM reconciliation_breaks
WHERE break_type LIKE '%DUPLICATE%'
ORDER BY b_record_count DESC, a_record_count DESC;


-- 7. Aged open cases
SELECT
    case_id,
    transaction_id,
    break_type,
    severity,
    case_age_days,
    case_owner,
    recommended_action
FROM reconciliation_breaks
WHERE case_status = 'Open'
ORDER BY case_age_days DESC
LIMIT 25;