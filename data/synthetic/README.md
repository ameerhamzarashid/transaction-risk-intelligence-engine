# Synthetic Financial Data

This folder contains fully synthetic financial datasets generated for the Transaction Risk Intelligence Engine project.

## Files

| File | Purpose |
|---|---|
| customers.csv | Synthetic customer profiles with country, KYC, PEP and segment fields |
| merchants.csv | Synthetic merchant records with category and country risk fields |
| accounts.csv | Synthetic customer account records |
| transactions.csv | Synthetic payment, card and transfer transactions with risk flags |
| account_transfers.csv | Synthetic account-to-account transfer records |
| watchlist.csv | Dummy sanctions, PEP and internal high-risk lookup table |
| reconciliation_file_a.csv | Payment processor style reconciliation file |
| reconciliation_file_b.csv | Core banking style reconciliation file with injected breaks |
| generation_summary.json | Summary of generated row counts |

## Important Note

All data is synthetic and does not contain real personal, banking or customer information.

## Injected Risk Patterns

The generated data includes deliberate patterns for later stages:

- high-value transactions
- cross-border transactions
- unusual-hour transactions
- high-risk merchant categories
- high-risk countries
- KYC issues
- PEP flags
- dummy watchlist matches
- reconciliation amount mismatches
- reconciliation date mismatches
- missing records
- duplicate records
- unmatched records
