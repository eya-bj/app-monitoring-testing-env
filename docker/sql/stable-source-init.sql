-- ============================================================
-- Core Banking Admin Console — Source DB (PostgreSQL)
-- Internal tool used by support engineers to manage client banks,
-- track deployments, and review audit logs.
-- ============================================================

CREATE TABLE IF NOT EXISTS client_banks (
    id              SERIAL PRIMARY KEY,
    bank_code       VARCHAR(10) UNIQUE NOT NULL,
    bank_name       VARCHAR(100) NOT NULL,
    country         VARCHAR(50) NOT NULL,
    environment     VARCHAR(20) NOT NULL,   -- PROD / UAT / DEV
    status          VARCHAR(20) NOT NULL,   -- ACTIVE / SUSPENDED
    contract_start  DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS deployments (
    id                SERIAL PRIMARY KEY,
    client_bank_id    INT NOT NULL REFERENCES client_banks(id),
    version           VARCHAR(20) NOT NULL,
    deployed_at       TIMESTAMP NOT NULL,
    deployed_by       VARCHAR(100) NOT NULL,
    status            VARCHAR(20) NOT NULL    -- SUCCESS / ROLLED_BACK
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id              SERIAL PRIMARY KEY,
    user_email      VARCHAR(100) NOT NULL,
    action          VARCHAR(50) NOT NULL,
    target_resource VARCHAR(100) NOT NULL,
    ip_address      VARCHAR(45),
    event_time      TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS batch_log (
    id                  SERIAL PRIMARY KEY,
    job_name            VARCHAR(100) NOT NULL,
    status              VARCHAR(20) NOT NULL,
    run_date            DATE NOT NULL,
    records_processed   INT,
    started_at          TIMESTAMP,
    finished_at         TIMESTAMP,
    error_message       VARCHAR(500)
);

-- ─── Seed client_banks (25 client banks across 3 environments) ───
INSERT INTO client_banks (bank_code, bank_name, country, environment, status, contract_start) VALUES
    ('BIAT',  'Banque Internationale Arabe de Tunisie', 'Tunisia', 'PROD', 'ACTIVE',    '2021-03-15'),
    ('ATB',   'Arab Tunisian Bank',                     'Tunisia', 'PROD', 'ACTIVE',    '2020-06-01'),
    ('UIB',   'Union Internationale de Banques',        'Tunisia', 'PROD', 'ACTIVE',    '2019-11-20'),
    ('BT',    'Banque de Tunisie',                      'Tunisia', 'PROD', 'ACTIVE',    '2018-01-10'),
    ('BH',    'Banque de l''Habitat',                   'Tunisia', 'PROD', 'ACTIVE',    '2022-02-28'),
    ('STB',   'Société Tunisienne de Banque',           'Tunisia', 'PROD', 'ACTIVE',    '2020-09-15'),
    ('BNA',   'Banque Nationale Agricole',              'Tunisia', 'PROD', 'ACTIVE',    '2017-05-22'),
    ('AMEN',  'Amen Bank',                              'Tunisia', 'PROD', 'ACTIVE',    '2021-08-14'),
    ('ATTIJ', 'Attijari Bank',                          'Tunisia', 'PROD', 'ACTIVE',    '2019-03-11'),
    ('QNB',   'Qatar National Bank Tunisia',            'Tunisia', 'PROD', 'SUSPENDED', '2018-12-05'),
    ('BCA',   'Banque Centrale d''Algérie',             'Algeria', 'PROD', 'ACTIVE',    '2022-01-20'),
    ('AGB',   'Algeria Gulf Bank',                      'Algeria', 'PROD', 'ACTIVE',    '2021-07-18'),
    ('BEA',   'Banque Extérieure d''Algérie',           'Algeria', 'PROD', 'ACTIVE',    '2020-10-09'),
    ('CPA',   'Crédit Populaire d''Algérie',            'Algeria', 'UAT',  'ACTIVE',    '2023-03-01'),
    ('BMCE',  'Banque Marocaine du Commerce Extérieur', 'Morocco', 'PROD', 'ACTIVE',    '2019-09-13'),
    ('BP',    'Banque Populaire Maroc',                 'Morocco', 'PROD', 'ACTIVE',    '2020-04-27'),
    ('AWB',   'Attijariwafa Bank',                      'Morocco', 'PROD', 'ACTIVE',    '2018-07-30'),
    ('CIH',   'CIH Bank',                               'Morocco', 'UAT',  'ACTIVE',    '2023-01-15'),
    ('BIAT2', 'BIAT Staging',                           'Tunisia', 'UAT',  'ACTIVE',    '2023-02-10'),
    ('ATB2',  'ATB Staging',                            'Tunisia', 'UAT',  'ACTIVE',    '2023-02-10'),
    ('BIAT3', 'BIAT Dev',                               'Tunisia', 'DEV',  'ACTIVE',    '2023-05-01'),
    ('ATB3',  'ATB Dev',                                'Tunisia', 'DEV',  'ACTIVE',    '2023-05-01'),
    ('UIB3',  'UIB Dev',                                'Tunisia', 'DEV',  'ACTIVE',    '2023-05-01'),
    ('BT3',   'BT Dev',                                 'Tunisia', 'DEV',  'ACTIVE',    '2023-05-01'),
    ('TEST',  'Test Sandbox',                           'Tunisia', 'DEV',  'ACTIVE',    '2023-06-12');

-- ─── Seed deployments (180 rows spread over last 60 days) ───
INSERT INTO deployments (client_bank_id, version, deployed_at, deployed_by, status)
SELECT
    1 + (gs % 25),
    '2.' || (1 + (gs % 8)) || '.' || (gs % 20),
    CURRENT_TIMESTAMP - (gs || ' hours')::INTERVAL,
    CASE (gs % 5)
        WHEN 0 THEN 'sami.ben@company.tn'
        WHEN 1 THEN 'eya.trabelsi@company.tn'
        WHEN 2 THEN 'ahmed.gharbi@company.tn'
        WHEN 3 THEN 'mariem.khaldi@company.tn'
        ELSE        'oussama.said@company.tn'
    END,
    CASE WHEN gs % 30 = 0 THEN 'ROLLED_BACK' ELSE 'SUCCESS' END
FROM generate_series(1, 180) gs;

-- ─── Seed audit_logs (1500 rows spread over last 30 days) ───
INSERT INTO audit_logs (user_email, action, target_resource, ip_address, event_time)
SELECT
    CASE (gs % 5)
        WHEN 0 THEN 'sami.ben@company.tn'
        WHEN 1 THEN 'eya.trabelsi@company.tn'
        WHEN 2 THEN 'ahmed.gharbi@company.tn'
        WHEN 3 THEN 'mariem.khaldi@company.tn'
        ELSE        'oussama.said@company.tn'
    END,
    CASE (gs % 6)
        WHEN 0 THEN 'LOGIN'
        WHEN 1 THEN 'VIEW_BANK_CONFIG'
        WHEN 2 THEN 'UPDATE_BANK_CONFIG'
        WHEN 3 THEN 'TRIGGER_DEPLOYMENT'
        WHEN 4 THEN 'VIEW_AUDIT_LOG'
        ELSE        'EXPORT_REPORT'
    END,
    'BANK-' || (1 + (gs % 25)),
    '10.0.' || (gs % 255) || '.' || ((gs * 7) % 255),
    CURRENT_TIMESTAMP - ((gs * 20) || ' minutes')::INTERVAL
FROM generate_series(1, 1500) gs;

-- ─── Seed batch_log for TODAY (Python script will refresh every 2 min) ───
INSERT INTO batch_log (job_name, status, run_date, records_processed, started_at, finished_at, error_message)
VALUES ('NIGHTLY_DEPLOYMENT_SYNC', 'SUCCESS', CURRENT_DATE, 180, NOW(), NOW(), NULL);