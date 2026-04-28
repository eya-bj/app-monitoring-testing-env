import psycopg2
import csv
import random
import os
from datetime import datetime, date, timedelta

DB_HOST = os.environ.get('DB_HOST', 'stable-source-db')
DB_PORT = int(os.environ.get('DB_PORT', '5432'))
DB_NAME = os.environ.get('DB_NAME', 'stable_source')
DB_USER = os.environ.get('DB_USER', 'admin')
DB_PASS = os.environ.get('DB_PASS', 'admin')

REPORTS_DIR = '/home/monitor/reports'

# Realistic catalog used to produce believable audit logs
USERS = [
    'admin@bank.tn', 'sysop@bank.tn', 'auditor@bank.tn',
    'ops.lead@bank.tn', 'release.mgr@bank.tn', 'security@bank.tn'
]
ACTIONS = [
    'LOGIN_SUCCESS', 'LOGIN_FAILURE', 'CONFIG_CHANGE',
    'DEPLOYMENT_TRIGGERED', 'PASSWORD_RESET', 'ROLE_CHANGE',
    'ACCESS_GRANTED', 'ACCESS_REVOKED'
]
TARGETS = [
    'client_bank.STB', 'client_bank.BIAT', 'deployment.staging',
    'deployment.prod', 'user.account', 'role.admin', 'config.security'
]


def connect_db():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, database=DB_NAME,
        user=DB_USER, password=DB_PASS
    )


def refresh_batch_log(conn):
    """Always insert today's NIGHTLY_DEPLOYMENT_SYNC = SUCCESS row.
       Admin Console is the deterministic-healthy app — no randomness here."""
    cur = conn.cursor()
    cur.execute("DELETE FROM batch_log WHERE run_date = CURRENT_DATE")
    cur.execute("""
        INSERT INTO batch_log
            (job_name, run_date, status, records_processed,
             started_at, finished_at, error_message)
        VALUES
            ('NIGHTLY_DEPLOYMENT_SYNC', CURRENT_DATE, 'SUCCESS', 180,
             NOW() - INTERVAL '4 hours', NOW() - INTERVAL '3 hours 50 minutes', NULL)
    """)
    conn.commit()
    cur.close()
    print("[BATCH] NIGHTLY_DEPLOYMENT_SYNC=SUCCESS")


def refresh_audit_logs(conn):
    """Keep audit_logs healthy in the last-24h window.
       Strategy: insert 60 fresh logs each tick, delete rows older than 25h
       to bound table growth. With cron firing every 2 min, the table stays
       at ~1500-2000 rows in steady state."""
    cur = conn.cursor()

    # Cleanup — discard rows older than 25h (keeps table from growing forever)
    cur.execute("DELETE FROM audit_logs WHERE event_time < NOW() - INTERVAL '25 hours'")
    deleted = cur.rowcount

    # Insert 60 fresh rows spread over the last 5 minutes (so they all
    # appear in the 24h window and the CSV always has plenty of recent data)
    rows = []
    for i in range(60):
        rows.append((
            datetime.now() - timedelta(seconds=random.randint(0, 300)),
            random.choice(USERS),
            random.choice(ACTIONS),
            random.choice(TARGETS),
            f"10.0.{random.randint(1, 254)}.{random.randint(1, 254)}"
        ))
    cur.executemany("""
        INSERT INTO audit_logs (event_time, user_email, action, target_resource, ip_address)
        VALUES (%s, %s, %s, %s, %s)
    """, rows)
    conn.commit()
    cur.close()
    print(f"[AUDIT] inserted 60 logs, cleaned up {deleted} old rows")


def generate_audit_csv(conn):
    """Generate today's audit CSV.
       95% valid (the demo's stable scenario), 5% missing header to keep
       a tiny bit of variety so the file check produces some FAILED outcomes
       once in a while — demonstrates the check actually works."""
    cur = conn.cursor()
    cur.execute("""
        SELECT event_time, user_email, action, target_resource, ip_address
        FROM audit_logs
        WHERE event_time > NOW() - INTERVAL '24 hours'
        ORDER BY event_time DESC
    """)
    rows = cur.fetchall()
    cur.close()

    today = date.today().isoformat()
    filepath = f"{REPORTS_DIR}/audit_export_{today}.csv"

    if random.random() < 0.05:
        # Rare corrupt-file path — wrong header, no rows
        with open(filepath, 'w') as f:
            f.write("BAD_HEADER,nope,nope,nope,nope\n")
        print(f"[CORRUPT] {filepath}")
        return

    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['event_time', 'user_email', 'action', 'target_resource', 'ip_address'])
        for row in rows:
            writer.writerow(row)

    print(f"[OK] {filepath} ({len(rows)} rows)")


if __name__ == '__main__':
    conn = None
    try:
        conn = connect_db()
        refresh_batch_log(conn)
        refresh_audit_logs(conn)
        generate_audit_csv(conn)
    except Exception as e:
        print(f"[ERROR] {e}")
    finally:
        if conn:
            conn.close()