import psycopg2
import csv
import random
import os
from datetime import datetime, date

DB_HOST = os.environ.get('DB_HOST', 'stable-source-db')
DB_PORT = int(os.environ.get('DB_PORT', '5432'))
DB_NAME = os.environ.get('DB_NAME', 'stable_source')
DB_USER = os.environ.get('DB_USER', 'admin')
DB_PASS = os.environ.get('DB_PASS', 'admin')
REPORTS_DIR = '/home/monitor/reports'

today = date.today().isoformat()

def connect_db():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASS
    )

def update_batch_log(conn):
    """Refresh today's nightly deployment sync job — stable app is mostly healthy (95% success)."""
    cur = conn.cursor()

    status = 'SUCCESS' if random.random() < 0.95 else 'FAILED'
    err_msg = None if status == 'SUCCESS' else 'Sync failed: timeout connecting to deployment registry'

    cur.execute("DELETE FROM batch_log WHERE run_date = CURRENT_DATE")
    cur.execute("""
        INSERT INTO batch_log (job_name, status, run_date, records_processed, started_at, finished_at, error_message)
        VALUES (%s, %s, CURRENT_DATE, %s, NOW(), NOW(), %s)
    """, ('NIGHTLY_DEPLOYMENT_SYNC', status, 180, err_msg))

    conn.commit()
    cur.close()
    print(f"[BATCH] NIGHTLY_DEPLOYMENT_SYNC={status}")

def generate_audit_export(conn):
    """Export last 24h of audit logs to CSV."""
    cur = conn.cursor()
    cur.execute("""
        SELECT event_time, user_email, action, target_resource, ip_address
        FROM audit_logs
        WHERE event_time >= NOW() - INTERVAL '24 hours'
        ORDER BY event_time DESC
    """)
    rows = cur.fetchall()
    cur.close()

    filepath = f"{REPORTS_DIR}/audit_export_{today}.csv"

    # Stable app: 95% valid, 5% corrupt header
    if random.random() < 0.05:
        with open(filepath, 'w') as f:
            f.write("BROKEN,header,format,error\n")
            f.write("no,valid,data,here\n")
        print(f"[CORRUPT] Generated corrupt {filepath}")
        return

    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['event_time', 'user_email', 'action', 'target_resource', 'ip_address'])
        for row in rows:
            writer.writerow(row)

    print(f"[OK] Generated {filepath} with {len(rows)} rows")

if __name__ == '__main__':
    try:
        conn = connect_db()
        update_batch_log(conn)
        generate_audit_export(conn)
        conn.close()
    except Exception as e:
        print(f"[ERROR] {e}")