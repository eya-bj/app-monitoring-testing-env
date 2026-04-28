import mysql.connector
import csv
import random
import os
from datetime import datetime, date

# Source DB (used by data check Mode 1, file checks read from here, batch_log lives here)
SRC_HOST = os.environ.get('DB_HOST', 'banking-source-db')
SRC_PORT = int(os.environ.get('DB_PORT', '3306'))
SRC_NAME = os.environ.get('DB_NAME', 'banking_source')
SRC_USER = os.environ.get('DB_USER', 'admin')
SRC_PASS = os.environ.get('DB_PASS', 'admin')

# Target DB (used by data check Mode 3 secondary side)
TGT_HOST = os.environ.get('DB_HOST_TARGET', 'banking-target-db')
TGT_PORT = int(os.environ.get('DB_PORT_TARGET', '3306'))
TGT_NAME = os.environ.get('DB_NAME_TARGET', 'banking_target')
TGT_USER = os.environ.get('DB_USER_TARGET', 'admin')
TGT_PASS = os.environ.get('DB_PASS_TARGET', 'admin')

REPORTS_DIR = '/home/monitor/reports'
SOURCE_TX_COUNT = 500
TARGET_TX_COUNT = 487   # intentional mismatch — the 13-row gap drives the data check failure

today = date.today().isoformat()


def connect_db(host, port, dbname, user, password):
    return mysql.connector.connect(
        host=host, port=port, database=dbname,
        user=user, password=password
    )


def refresh_transactions(conn, db_label, target_count):
    """Wipe today's transactions and reseed exactly target_count rows.
       Keeps the source/target row count stable across days, so the
       Transaction Count Sync data check always sees 500 vs 487."""
    cur = conn.cursor()

    # Wipe today's existing rows
    cur.execute("DELETE FROM transactions WHERE DATE(created_at) = CURDATE()")

    # Reseed target_count rows for today
    insert_sql = """
        INSERT INTO transactions
            (source_account, target_account, amount, currency, status, tx_type, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    rows = []
    for i in range(1, target_count + 1):
        rows.append((
            f"ACC-{(i % 200 + 1):04d}",
            f"ACC-{((i * 7) % 200 + 1):04d}",
            round(random.uniform(10, 1000), 2),
            'TND' if i % 2 == 0 else 'EUR',
            'FAILED' if i % 10 == 0 else ('PENDING' if i % 15 == 0 else 'SUCCESS'),
            ['TRANSFER', 'PAYMENT', 'WITHDRAWAL'][i % 3],
            datetime.now()
        ))
    cur.executemany(insert_sql, rows)
    conn.commit()
    cur.close()
    print(f"[TX] {db_label}: refreshed {target_count} transactions for today")


def update_batch_log(conn):
    """Refresh today's batch_log rows with random status — drives the 'Daily Batch Sync' data check."""
    cur = conn.cursor()

    daily_sync_status = 'SUCCESS' if random.random() < 0.80 else 'FAILED'
    balance_status = 'SUCCESS' if random.random() < 0.85 else 'FAILED'

    cur.execute("DELETE FROM batch_log WHERE run_date = CURDATE()")
    cur.execute("""
        INSERT INTO batch_log (job_name, run_date, status, records_processed, started_at, finished_at, error_message)
        VALUES (%s, CURDATE(), %s, %s, NOW(), NOW(), %s)
    """, ('DAILY_SYNC', daily_sync_status, 500,
          'Sync failed: connection timeout' if daily_sync_status == 'FAILED' else None))

    cur.execute("""
        INSERT INTO batch_log (job_name, run_date, status, records_processed, started_at, finished_at, error_message)
        VALUES (%s, CURDATE(), %s, %s, NOW(), NOW(), %s)
    """, ('BALANCE_SNAPSHOT', balance_status, 200, None))

    conn.commit()
    cur.close()
    print(f"[BATCH] DAILY_SYNC={daily_sync_status}, BALANCE_SNAPSHOT={balance_status}")


def generate_csv(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT DATE_FORMAT(created_at, '%Y-%m-%d'), source_account, target_account,
               amount, currency, status
        FROM transactions
        WHERE DATE(created_at) = CURDATE()
        ORDER BY created_at
    """)
    rows = cur.fetchall()
    cur.close()

    filepath = f"{REPORTS_DIR}/transactions_{today}.csv"

    roll = random.random()
    if roll < 0.17:
        print(f"[SKIP] Not generating {filepath}")
        return
    elif roll < 0.34:
        with open(filepath, 'w') as f:
            f.write("CORRUPTED,bad,header,columns\n")
            f.write("no,real,data,here\n")
        print(f"[CORRUPT] Generated corrupt {filepath}")
        return

    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['date', 'source_account', 'target_account',
                         'amount', 'currency', 'status'])
        for row in rows:
            writer.writerow(row)

    print(f"[OK] Generated {filepath} with {len(rows)} rows")


def generate_eod_report(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT job_name, status, records_processed,
               started_at, finished_at, error_message
        FROM batch_log
        WHERE run_date = CURDATE()
        ORDER BY started_at
    """)
    jobs = cur.fetchall()

    cur.execute("SELECT COUNT(*) FROM transactions WHERE DATE(created_at) = CURDATE()")
    tx_count = cur.fetchone()[0]

    cur.execute("SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE DATE(created_at) = CURDATE() AND status = 'SUCCESS'")
    tx_total = cur.fetchone()[0]
    cur.close()

    filepath = f"{REPORTS_DIR}/eod_report_{today}.txt"

    if random.random() < 0.17:
        print(f"[SKIP] Not generating {filepath}")
        return

    all_success = all(j[1] == 'SUCCESS' for j in jobs)

    with open(filepath, 'w') as f:
        f.write(f"=== END OF DAY REPORT {today} ===\n\n")
        f.write(f"TOTAL_TRANSACTIONS: {tx_count}\n")
        f.write(f"TOTAL_AMOUNT: {tx_total}\n")
        f.write(f"BATCH_STATUS: {'SUCCESS' if all_success else 'FAILED'}\n\n")
        f.write("--- BATCH JOBS ---\n")
        for job in jobs:
            f.write(f"  {job[0]}: {job[1]} ({job[2]} records)\n")
            if job[5]:
                f.write(f"    ERROR: {job[5]}\n")
        f.write(f"\nGenerated at: {datetime.now().isoformat()}\n")

    print(f"[OK] Generated {filepath}")


if __name__ == '__main__':
    src_conn = None
    tgt_conn = None
    try:
        # Source DB — refresh transactions, refresh batch_log, generate files
        src_conn = connect_db(SRC_HOST, SRC_PORT, SRC_NAME, SRC_USER, SRC_PASS)
        refresh_transactions(src_conn, 'source', SOURCE_TX_COUNT)
        update_batch_log(src_conn)
        generate_csv(src_conn)
        generate_eod_report(src_conn)

        # Target DB — refresh transactions only (with the intentional mismatch)
        tgt_conn = connect_db(TGT_HOST, TGT_PORT, TGT_NAME, TGT_USER, TGT_PASS)
        refresh_transactions(tgt_conn, 'target', TARGET_TX_COUNT)

    except Exception as e:
        print(f"[ERROR] {e}")
    finally:
        if src_conn:
            src_conn.close()
        if tgt_conn:
            tgt_conn.close()