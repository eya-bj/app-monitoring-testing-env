-- ============================================================
-- Banking Target DB (MySQL 8.0)
-- Simulates the REPLICATION TARGET — intentional 487 tx vs 500 source
-- ============================================================

CREATE TABLE IF NOT EXISTS accounts (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    account_number  VARCHAR(20) UNIQUE NOT NULL,
    holder_name     VARCHAR(100) NOT NULL,
    balance         DECIMAL(15,2) NOT NULL,
    currency        VARCHAR(3) NOT NULL,
    status          VARCHAR(20) NOT NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transactions (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    source_account  VARCHAR(20) NOT NULL,
    target_account  VARCHAR(20) NOT NULL,
    amount          DECIMAL(15,2) NOT NULL,
    currency        VARCHAR(3) NOT NULL,
    status          VARCHAR(20) NOT NULL,
    tx_type         VARCHAR(20) NOT NULL,
    created_at      DATETIME NOT NULL
);

-- ─── Seed accounts (200 rows — matches source) ────────────────
INSERT INTO accounts (account_number, holder_name, balance, currency, status)
SELECT
    CONCAT('ACC-', LPAD(n, 4, '0')),
    CONCAT('Holder ', n),
    ROUND(RAND() * 10000, 2),
    IF(n % 2 = 0, 'TND', 'EUR'),
    IF(n % 20 = 0, 'BLOCKED', 'ACTIVE')
FROM (
    SELECT a.N + b.N * 10 + c.N * 100 + 1 AS n
    FROM (SELECT 0 AS N UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4
          UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) a,
         (SELECT 0 AS N UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4
          UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) b,
         (SELECT 0 AS N UNION SELECT 1 UNION SELECT 2) c
    WHERE a.N + b.N * 10 + c.N * 100 < 200
) seq;

-- ─── Seed transactions for TODAY (487 rows — intentional mismatch) ──────
INSERT INTO transactions (source_account, target_account, amount, currency, status, tx_type, created_at)
SELECT
    CONCAT('ACC-', LPAD(1 + FLOOR(RAND() * 200), 4, '0')),
    CONCAT('ACC-', LPAD(1 + FLOOR(RAND() * 200), 4, '0')),
    ROUND(RAND() * 1000 + 10, 2),
    IF(n % 2 = 0, 'TND', 'EUR'),
    CASE
        WHEN n % 10 = 0 THEN 'FAILED'
        WHEN n % 15 = 0 THEN 'PENDING'
        ELSE 'SUCCESS'
    END,
    CASE n % 3
        WHEN 0 THEN 'TRANSFER'
        WHEN 1 THEN 'PAYMENT'
        ELSE 'WITHDRAWAL'
    END,
    DATE_ADD(CURDATE(), INTERVAL FLOOR(RAND() * 86400) SECOND)
FROM (
    SELECT a.N + b.N * 10 + c.N * 100 + 1 AS n
    FROM (SELECT 0 AS N UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4
          UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) a,
         (SELECT 0 AS N UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4
          UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9) b,
         (SELECT 0 AS N UNION SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4) c
    WHERE a.N + b.N * 10 + c.N * 100 < 487
) seq;