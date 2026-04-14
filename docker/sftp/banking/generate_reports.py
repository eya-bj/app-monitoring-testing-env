import oracledb
import csv
import random
import os
from datetime import datetime, date

DB_HOST = os.environ.get('DB_HOST', 'banking-source-db')
DB_PORT = os.environ.get('DB_PORT', '1521')
DB_NAME = os.environ.get('DB_NAME', 'FREEPDB1')
DB_USER = os.environ.get('DB_USER', 'admin')
DB_PASS = os.environ.get('DB_PASS', 'admin')
REPORTS_DIR = '/home/monitor/reports'

today = date.today().isoformat()

def connect_db():
    return oracledb.connect(
        user=DB_USER, password=DB_PASS,
        dsn=f"{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

def generate_csv(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT TO_CHAR(created_at, 'YYYY-MM-DD'), source_account, target_account,
               amount, currency, status
        FROM transactions
        WHERE TRUNC(created_at) = TRUNC(SYSDATE)
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
        WHERE run_date = TRUNC(SYSDATE)
        ORDER BY started_at
    """)
    jobs = cur.fetchall()

    cur.execute("SELECT COUNT(*) FROM transactions WHERE TRUNC(created_at) = TRUNC(SYSDATE)")
    tx_count = cur.fetchone()[0]

    cur.execute("SELECT NVL(SUM(amount), 0) FROM transactions WHERE TRUNC(created_at) = TRUNC(SYSDATE) AND status = 'SUCCESS'")
    tx_total = cur.fetchone()[0]
    cur.close()

    filepath = f"{REPORTS_DIR}/eod_report_{today}.txt"

    if random.random() < 0.17:
        print(f"[SKIP] Not generating {filepath}")
        return

    all_success = all(j[1] == 'SUCCESS' for j in jobs)

    with open(filepath, 'w') as f:
        f.write(f"=== END OF DAY REPORT — {today} ===\n\n")
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
        generate_csv(conn)
        generate_eod_report(conn)
        conn.close()
    except Exception as e:
        print(f"[ERROR] {e}")