CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    reference VARCHAR(50) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_date DATE NOT NULL
);

-- 1487 rows → mismatch with source (1500)
INSERT INTO orders (reference, amount, status, created_date)
SELECT 'ORD-' || gs, (gs * 10)::DECIMAL, 'SUCCESS', CURRENT_DATE
FROM generate_series(1, 1487) gs;