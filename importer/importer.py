import sys
import os
import subprocess
import psycopg2
import time
import json
import psutil
from tqdm import tqdm

# Simple console logger
def log(message, level="INFO", emoji=None):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    emoji_str = f"{emoji} " if emoji else ""
    print(f"{ts} [{level:<7}] {emoji_str}{message}", flush=True)


DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "osmuser")
DB_PASS = os.getenv("DB_PASS", "osmpass")
DB_NAME = os.getenv("DB_NAME", "osm")


def get_file_size_mb(file_path):
    """Return file size in MB, or None if not found."""
    if os.path.exists(file_path):
        return round(os.path.getsize(file_path) / (1024 * 1024), 2)
    return None


def log_system_usage(tag):
    """Log memory and CPU usage."""
    process = psutil.Process(os.getpid())
    memory = round(process.memory_info().rss / (1024 * 1024), 2)
    cpu = psutil.cpu_percent(interval=0.5)
    log(f"CPU {cpu}% | Memory {memory}MB ({tag})", "INFO", "🧠")


def connect_db():
    log("Connecting to PostGIS database…", "INFO", "🗄️")
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS, dbname=DB_NAME
    )
    log("Connected to PostGIS", "INFO", "✅")
    return conn


def run_osmium_extract(input_file, output_file):
    """Convert OSM PBF → GeoJSON using osmium-tool."""
    input_size = get_file_size_mb(input_file)
    log(
        f"Convert OSM PBF to GeoJSON → osmium export --progress --overwrite -o {output_file} {input_file} "
        f"(size: {input_size} MB)",
        "INFO",
        "🧩",
    )

    start_time = time.time()
    cmd = ["osmium", "export", "--progress", "--overwrite", "-o", output_file, input_file]

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    for line in iter(process.stdout.readline, ""):
        line = line.strip()
        if not line:
            continue
        if "%" in line or "Done" in line or "Writing" in line:
            print(line, flush=True)
        else:
            log(line)

    process.wait()
    if process.returncode != 0:
        log("Osmium export failed.", "ERROR", "❌")
        sys.exit(1)

    elapsed = round(time.time() - start_time, 1)
    output_size = get_file_size_mb(output_file)
    log(f"Convert OSM PBF to GeoJSON completed successfully in {elapsed}s (size: {output_size} MB)", "INFO", "✅")
    log_system_usage("after_osmium")


def process_geojson(geojson_file):
    """Read GeoJSON and insert features into PostGIS."""
    log("Processing GeoJSON data…", "INFO", "🧩")
    conn = connect_db()
    cur = conn.cursor()

    start_load = time.time()
    with open(geojson_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    features = data.get("features", [])
    load_time = round(time.time() - start_load, 2)
    log(f"Loaded {len(features):,} features from GeoJSON in {load_time}s", "INFO", "📦")

    inserted = 0
    skipped = 0
    batch_size = 1000
    batch = []

    log("Preparing table `postal_lookup`", "INFO", "📊")
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS postal_lookup (
            postcode TEXT PRIMARY KEY,
            lat DOUBLE PRECISION,
            lon DOUBLE PRECISION
        );
        """
    )
    conn.commit()
    log("Table ready", "INFO", "✅")

    start_time = time.time()

    for feature in tqdm(features, desc="Importing features"):
        props = feature.get("properties", {})
        geometry = feature.get("geometry", {})

        if not geometry or geometry.get("type") != "Point":
            skipped += 1
            continue

        lon, lat = geometry["coordinates"]
        postcode = props.get("addr:postcode")

        if not postcode:
            skipped += 1
            continue

        batch.append((postcode, lat, lon))

        if len(batch) >= batch_size:
            cur.executemany(
                """
                INSERT INTO postal_lookup (postcode, lat, lon)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING;
                """,
                batch,
            )
            inserted += len(batch)
            conn.commit()
            batch = []
            log(f"Inserted {inserted:,} features so far…", "INFO", "📈")
            log_system_usage("db_insert")

    # Final commit
    if batch:
        cur.executemany(
            """
            INSERT INTO postal_lookup (postcode, lat, lon)
            VALUES (%s, %s, %s)
            ON CONFLICT DO NOTHING;
            """,
            batch,
        )
        inserted += len(batch)
        conn.commit()

    elapsed = round(time.time() - start_time, 1)
    log(f"Imported {inserted:,} features into `postal_lookup` (skipped {skipped:,}) in {elapsed}s", "INFO", "📊")

    cur.close()
    conn.close()
    log("Database connection closed", "INFO", "✅")
    log_system_usage("after_db_load")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: importer.py <osm.pbf file>")
        sys.exit(1)

    osm_file = sys.argv[1]
    if not os.path.exists(osm_file):
        print(f"File not found: {osm_file}")
        sys.exit(1)

    geojson_file = "/tmp/output.geojson"

    log("🚀 Starting OSM import pipeline", "INFO")
    log_system_usage("startup")

    start_total = time.time()

    try:
        run_osmium_extract(osm_file, geojson_file)
        process_geojson(geojson_file)
        total_time = round((time.time() - start_total) / 60, 2)
        log(f"🏁 OSM import completed successfully in {total_time} minutes", "INFO", "✅")
    except Exception as e:
        log(f"Import failed: {e}", "ERROR", "❌")
        sys.exit(1)
