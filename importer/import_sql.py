import sys
import os
import psycopg2
import time
import psutil

def log(message, level="INFO", emoji=None):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    emoji_str = f"{emoji} " if emoji else ""
    print(f"{ts} [{level:<7}] {emoji_str}{message}", flush=True)

def log_system_usage(tag):
    process = psutil.Process(os.getpid())
    memory = round(process.memory_info().rss / (1024 * 1024), 2)
    cpu = psutil.cpu_percent(interval=0.5)
    log(f"CPU {cpu}% | Memory {memory}MB ({tag})", "INFO", "🧠")

def connect_db():
    log("Connecting to PostGIS database…", "INFO", "🗄️")
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "db"),
        port=os.getenv("DB_PORT", "5432"),
        user=os.getenv("DB_USER", "osmuser"),
        password=os.getenv("DB_PASS", "osmpass"),
        dbname=os.getenv("DB_NAME", "osm")
    )
    log("✅ Connected to PostGIS", "INFO", "✅")
    return conn

def import_sql(sql_file):
    conn = connect_db()
    cur = conn.cursor()
    start_time = time.time()

    with open(sql_file, "r", encoding="utf-8") as f:
        sql_commands = f.read()

    log(f"Running SQL from {sql_file}", "INFO", "⚙️")
    cur.execute(sql_commands)
    conn.commit()

    elapsed = round(time.time() - start_time, 2)
    log(f"✅ SQL executed successfully in {elapsed}s", "INFO", "✅")

    cur.close()
    conn.close()
    log("Database connection closed", "INFO", "✅")
    log_system_usage("after_import")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python import_sql.py <sql_file>")
        sys.exit(1)

    sql_file = sys.argv[1]
    log("🚀 Starting database import", "INFO")
    log_system_usage("startup")
    import_sql(sql_file)
