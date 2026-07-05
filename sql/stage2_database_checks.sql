-- Stage 2 database checks for Transaction Risk Intelligence Engine

-- 1. Table row counts
SELECT 'customers' AS table_name, COUNT(*) AS row_count FROM customers
UNION ALL
SELECT 'merchants', COUNT(*) FROM merchants
UNION ALL
SELECT 'accounts', COUNT(*) FROM accounts
UNION ALL
SELECT 'transactions', COUNT(*) FROM transactions
UNION ALL
SELECT 'account_transfers', COUNT(*) FROM account_transfers
UNION ALL
SELECT 'watchlist', COUNT(*) FROM watchlist
UNION ALL
SELECT 'reconciliation_file_a', COUNT(*) FROM reconciliation_file_a
UNION ALL
SELECT 'reconciliation_file_b', COUNT(*) FROM reconciliation_file_b;


-- 2. Suspicious transaction count
SELECT
    suspicious_label,
    COUNT(*) AS transaction_count
FROM transactions
GROUP BY suspicious_label
ORDER BY suspicious_label;


-- 3. High-risk transaction sample
SELECT
    transaction_id,
    transaction_timestamp,
    customer_id,
    full_name,
    merchant_id,
    merchant_name,
    amount,
    currency,
    channel,
    cross_border_flag,
    high_amount_flag,
    unusual_hour_flag,
    high_risk_category_flag,
    high_risk_country_flag,
    kyc_issue_flag,
    pep_flag,
    watchlist_match_flag,
    suspicious_label
FROM vw_transaction_enriched
WHERE suspicious_label = 1
ORDER BY amount DESC
LIMIT 20;


-- 4. Watchlist matched transactions
SELECT
    transaction_id,
    customer_id,
    merchant_id,
    amount,
    watchlist_type,
    watchlist_risk_reason
FROM vw_transaction_enriched
WHERE watchlist_match_flag = 1
LIMIT 20;


-- 5. Reconciliation file overview
SELECT *
FROM vw_reconciliation_overview;