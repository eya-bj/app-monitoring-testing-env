CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    reference VARCHAR(50) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_date DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS batch_log (
    id SERIAL PRIMARY KEY,
    job_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL,
    run_date DATE NOT NULL
);

INSERT INTO orders (reference, amount, status, created_date)
SELECT 'ORD-' || gs, (gs * 10)::DECIMAL, 'SUCCESS', CURRENT_DATE
FROM generate_series(1, 1500) gs;

-- No batch_log entry → simulates batch job not running