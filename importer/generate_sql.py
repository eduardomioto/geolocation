import sys
import os
import time
import ijson
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

def generate_sql(geojson_file, output_sql):
    log(f"Generating SQL inserts from {geojson_file}", "INFO", "📦")

    start_time = time.time()
    inserted = 0
    skipped = 0

    with open(output_sql, "w", encoding="utf-8") as sql_file:
        sql_file.write("""
CREATE TABLE IF NOT EXISTS postal_lookup (
    postcode TEXT PRIMARY KEY,
    lat DOUBLE PRECISION,
    lon DOUBLE PRECISION
);
BEGIN;
""")

        with open(geojson_file, "r", encoding="utf-8") as f:
            features = ijson.items(f, "features.item")

            for feature in features:
                try:
                    props = feature.get("properties", {})
                    geometry = feature.get("geometry", {})
                    if not geometry or geometry.get("type") != "Point":
                        skipped += 1
                        continue

                    lon, lat = geometry.get("coordinates", [None, None])
                    postcode = props.get("addr:postcode")

                    if not postcode or lat is None or lon is None:
                        skipped += 1
                        continue

                    safe_postcode = str(postcode).replace("'", "")
                    sql_file.write(
                        f"INSERT INTO postal_lookup (postcode, lat, lon) VALUES ('{safe_postcode}', {lat}, {lon}) ON CONFLICT DO NOTHING;\n"
                    )
                    inserted += 1

                    # lightweight progress feedback
                    if inserted % 50000 == 0:
                        log(f"🧾 Processed {inserted:,} records (skipped {skipped:,})", "INFO")
                        log_system_usage("sql_generation")
                except Exception as e:
                    skipped += 1
                    continue

        sql_file.write("COMMIT;\n")

    elapsed = round(time.time() - start_time, 2)
    log(f"✅ Generated SQL file with {inserted:,} inserts (skipped {skipped:,}) in {elapsed}s", "INFO", "✅")
    log_system_usage("after_sql_generation")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python generate_sql.py <input.geojson> <output_folder>")
        sys.exit(1)

    geojson_file = sys.argv[1]
    output_folder = sys.argv[2]
    os.makedirs(output_folder, exist_ok=True)
    sql_file = os.path.join(output_folder, os.path.basename(geojson_file).replace(".geojson", ".sql"))

    log("🚀 Starting SQL generation", "INFO")
    log_system_usage("startup")
    generate_sql(geojson_file, sql_file)
