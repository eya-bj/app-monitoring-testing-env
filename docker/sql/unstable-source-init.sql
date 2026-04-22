-- ============================================================
-- Legacy Transaction Reconciliation Service — Source DB
-- Inherited from acquired competitor. Known issues. Scheduled
-- for decommissioning but still running for 2 legacy clients.
-- ============================================================

CREATE TABLE IF NOT EXISTS reconciliation_batches (
    id                SERIAL PRIMARY KEY,
    batch_date        DATE NOT NULL,
    source_count      INT NOT NULL,
    target_count      INT NOT NULL,
    mismatch_count    INT NOT NULL,
    status            VARCHAR(20) NOT NULL,  -- SUCCESS / FAILED / PARTIAL
    started_at        TIMESTAMP,
    finished_at       TIMESTAMP,
    error_message     VARCHAR(500)
);

CREATE TABLE IF NOT EXISTS unmatched_transactions (
    id                SERIAL PRIMARY KEY,
    transaction_ref   VARCHAR(50) NOT NULL,
    amount            DECIMAL(15,2) NOT NULL,
    currency          VARCHAR(3) NOT NULL,
    source_system     VARCHAR(50) NOT NULL,
    reported_at       TIMESTAMP NOT NULL,
    reason            VARCHAR(200)
);

CREATE TABLE IF NOT EXISTS sync_errors (
    id              SERIAL PRIMARY KEY,
    error_code      VARCHAR(20) NOT NULL,
    error_message   VARCHAR(500) NOT NULL,
    occurred_at     TIMESTAMP NOT NULL
);

-- ─── Seed reconciliation_batches (60 rows over last 30 days, MOSTLY FAILED) ───
INSERT INTO reconciliation_batches (batch_date, source_count, target_count, mismatch_count, status, started_at, finished_at, error_message)
SELECT
    (CURRENT_DATE - (gs || ' days')::INTERVAL)::DATE,
    1000 + (gs * 23),
    980 + (gs * 20),
    20 + (gs * 3),
    CASE
        WHEN gs % 7 = 0 THEN 'SUCCESS'
        WHEN gs % 3 = 0 THEN 'PARTIAL'
        ELSE 'FAILED'
    END,
    CURRENT_TIMESTAMP - ((gs || ' days'))::INTERVAL,
    CURRENT_TIMESTAMP - ((gs || ' days'))::INTERVAL + INTERVAL '45 minutes',
    CASE
        WHEN gs % 7 = 0 THEN NULL
        WHEN gs % 3 = 0 THEN 'Partial reconciliation: 23 records could not be matched'
        ELSE 'Batch aborted: source system returned unexpected format'
    END
FROM generate_series(1, 60) gs;

-- Today's batch: FAILED (this is what the data check will catch)
INSERT INTO reconciliation_batches (batch_date, source_count, target_count, mismatch_count, status, started_at, finished_at, error_message)
VALUES (
    CURRENT_DATE,
    1247,
    1122,
    125,
    'FAILED',
    NOW() - INTERVAL '2 hours',
    NOW() - INTERVAL '1 hour 15 minutes',
    'Nightly reconciliation aborted: connection to partner payment network lost after 1122 records'
);

-- ─── Seed unmatched_transactions (150 rows — way above healthy threshold) ───
INSERT INTO unmatched_transactions (transaction_ref, amount, currency, source_system, reported_at, reason)
SELECT
    'TXN-' || LPAD(gs::TEXT, 8, '0'),
    ROUND((RANDOM() * 5000 + 50)::NUMERIC, 2),
    CASE (gs % 3) WHEN 0 THEN 'TND' WHEN 1 THEN 'EUR' ELSE 'USD' END,
    CASE (gs % 4)
        WHEN 0 THEN 'SWIFT'
        WHEN 1 THEN 'SEPA'
        WHEN 2 THEN 'INTERNAL'
        ELSE        'PARTNER_NET'
    END,
    NOW() - ((gs * 10) || ' minutes')::INTERVAL,
    CASE (gs % 5)
        WHEN 0 THEN 'Amount mismatch between source and target'
        WHEN 1 THEN 'Transaction reference not found in target system'
        WHEN 2 THEN 'Duplicate transaction detected'
        WHEN 3 THEN 'Currency conversion failed'
        ELSE        'Timestamp out of sync'
    END
FROM generate_series(1, 150) gs;

-- ─── Seed sync_errors (80 recent errors — this system is on fire) ───
INSERT INTO sync_errors (error_code, error_message, occurred_at)
SELECT
    CASE (gs % 4)
        WHEN 0 THEN 'CONN_TIMEOUT'
        WHEN 1 THEN 'AUTH_FAILED'
        WHEN 2 THEN 'DATA_MISMATCH'
        ELSE        'FORMAT_ERROR'
    END,
    CASE (gs % 4)
        WHEN 0 THEN 'Partner network connection timed out after 30s'
        WHEN 1 THEN 'Authentication rejected by partner gateway'
        WHEN 2 THEN 'Source amount does not match target amount'
        ELSE        'Unexpected record format from partner feed'
    END,
    NOW() - ((gs * 15) || ' minutes')::INTERVAL
FROM generate_series(1, 80) gs;