import psycopg2
import csv
import random
import os
from datetime import datetime, date, timedelta

DB_HOST = os.environ.get('DB_HOST', 'unstable-source-db')
DB_PORT = int(os.environ.get('DB_PORT', '5432'))
DB_NAME = os.environ.get('DB_NAME', 'unstable_source')
DB_USER = os.environ.get('DB_USER', 'admin')
DB_PASS = os.environ.get('DB_PASS', 'admin')
REPORTS_DIR = '/home/monitor/reports'

today = date.today().isoformat()

# Realistic catalog for unmatched transactions
SOURCE_SYSTEMS = ['LEGACY_CORE', 'PAYMENT_GW', 'CARD_NETWORK', 'INTERNAL_BANK', 'PARTNER_BANK']
CURRENCIES = ['TND', 'EUR', 'USD']
REASONS = [
    'Amount mismatch with source ledger',
    'Reference not found in target system',
    'Duplicate transaction reported',
    'Currency conversion discrepancy',
    'Timestamp out of expected window',
    'Source system did not acknowledge'
]


def connect_db():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASS
    )


def refresh_todays_batch(conn):
    """Refresh today's reconciliation batch — mostly FAILED (this system is broken)."""
    cur = conn.cursor()

    # 80% chance FAILED, 15% PARTIAL, 5% SUCCESS (rare good night)
    roll = random.random()
    if roll < 0.80:
        status = 'FAILED'
        err = 'Nightly reconciliation aborted: connection to partner payment network lost'
    elif roll < 0.95:
        status = 'PARTIAL'
        err = 'Partial reconciliation: records could not be matched'
    else:
        status = 'SUCCESS'
        err = None

    cur.execute("DELETE FROM reconciliation_batches WHERE batch_date = CURRENT_DATE")
    cur.execute("""
        INSERT INTO reconciliation_batches
            (batch_date, source_count, target_count, mismatch_count, status,
             started_at, finished_at, error_message)
        VALUES (CURRENT_DATE, 1247, 1122, 125, %s,
                NOW() - INTERVAL '2 hours',
                NOW() - INTERVAL '1 hour 15 minutes', %s)
    """, (status, err))

    conn.commit()
    cur.close()
    print(f"[BATCH] RECONCILIATION_TODAY={status}")


def refresh_unmatched_transactions(conn):
    """Keep ~150 unmatched transactions in the last-24h window so the
       'Unmatched Transactions Threshold' check (>50) stays FAILED every day.
       Strategy: insert 25 fresh rows each tick, delete rows older than 25h
       so the table stays bounded but the 24h window always has 150+ entries."""
    cur = conn.cursor()

    # Cleanup — drop rows older than 25h
    cur.execute("DELETE FROM unmatched_transactions WHERE reported_at < NOW() - INTERVAL '25 hours'")
    deleted = cur.rowcount

    # Insert 25 fresh rows spread over the last 5 minutes
    rows = []
    for i in range(25):
        rows.append((
            f"TXN-{random.randint(100000, 999999)}",
            round(random.uniform(50, 5000), 2),
            random.choice(CURRENCIES),
            random.choice(SOURCE_SYSTEMS),
            datetime.now() - timedelta(seconds=random.randint(0, 300)),
            random.choice(REASONS)
        ))
    cur.executemany("""
        INSERT INTO unmatched_transactions
            (transaction_ref, amount, currency, source_system, reported_at, reason)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, rows)
    conn.commit()
    cur.close()
    print(f"[UNMATCHED] inserted 25 rows, cleaned up {deleted} old rows")


def generate_recon_report(conn):
    """Recon report generation is broken — file mostly missing, occasionally corrupt."""
    filepath = f"{REPORTS_DIR}/recon_report_{today}.csv"

    roll = random.random()

    # 70% skip (broken generator), 20% corrupt, 10% valid (by accident)
    if roll < 0.70:
        print(f"[SKIP] Generator failed — not producing {filepath}")
        # also delete existing file to simulate the generator being offline
        if os.path.exists(filepath):
            os.remove(filepath)
        return

    if roll < 0.90:
        with open(filepath, 'w') as f:
            f.write("CORRUPTED,legacy,format,error\n")
            f.write("system,cannot,produce,valid_output\n")
        print(f"[CORRUPT] Generated corrupt {filepath}")
        return

    # Rare valid output (10%)
    cur = conn.cursor()
    cur.execute("""
        SELECT transaction_ref, amount, currency, source_system, reported_at
        FROM unmatched_transactions
        ORDER BY reported_at DESC
        LIMIT 100
    """)
    rows = cur.fetchall()
    cur.close()

    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['transaction_ref', 'amount', 'currency', 'source_system', 'reported_at'])
        for row in rows:
            writer.writerow(row)

    print(f"[OK] Generated {filepath} with {len(rows)} rows")


if __name__ == '__main__':
    conn = None
    try:
        conn = connect_db()
        refresh_todays_batch(conn)
        refresh_unmatched_transactions(conn)
        generate_recon_report(conn)
    except Exception as e:
        print(f"[ERROR] {e}")
    finally:
        if conn:
            conn.close()