import mysql.connector
import csv
import random
import os
from datetime import datetime, date

DB_HOST = os.environ.get('DB_HOST', 'banking-source-db')
DB_PORT = int(os.environ.get('DB_PORT', '3306'))
DB_NAME = os.environ.get('DB_NAME', 'banking_source')
DB_USER = os.environ.get('DB_USER', 'admin')
DB_PASS = os.environ.get('DB_PASS', 'admin')
REPORTS_DIR = '/home/monitor/reports'

today = date.today().isoformat()

def connect_db():
    return mysql.connector.connect(
        host=DB_HOST, port=DB_PORT, database=DB_NAME,
        user=DB_USER, password=DB_PASS
    )

def update_batch_log(conn):
    """Refresh today's batch_log rows with random status — drives the 'Daily Batch Sync' data check."""
    cur = conn.cursor()

    daily_sync_status = 'SUCCESS' if random.random() < 0.80 else 'FAILED'
    balance_status    = 'SUCCESS' if random.random() < 0.85 else 'FAILED'

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
    try:
        conn = connect_db()
        update_batch_log(conn)
        generate_csv(conn)
        generate_eod_report(conn)
        conn.close()
    except Exception as e:
        print(f"[ERROR] {e}")