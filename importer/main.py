import os
import sys
import time
import logging
from datetime import timedelta
from convert_pbf import run_osmium_extract  # ✅ step 1 - uses your existing file
# step 2 and 3 will be created soon:
# from generate_sql import generate_sql_file
# from run_sql import run_sql_commands

# === Logging configuration ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-7s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("osm_importer")


def get_file_size_mb(path):
    return round(os.path.getsize(path) / (1024 * 1024), 2) if os.path.exists(path) else 0


def main():
    log.info("🚀 Starting OSM import pipeline")

    if len(sys.argv) < 2:
        print("Usage: python main.py <osm.pbf file>")
        sys.exit(1)

    osm_file = sys.argv[1]
    if not os.path.exists(osm_file):
        log.error(f"❌ File not found: {osm_file}")
        sys.exit(1)

    base_name = os.path.basename(osm_file).replace(".osm.pbf", "")
    geojson_dir = "/data/geojson"
    sql_dir = "/data/sql"
    geojson_file = os.path.join(geojson_dir, f"{base_name}.geojson")
    sql_file = os.path.join(sql_dir, f"{base_name}_postal_lookup.sql")

    os.makedirs(geojson_dir, exist_ok=True)
    os.makedirs(sql_dir, exist_ok=True)

    start_time = time.time()

    # === STEP 1: Convert OSM → GeoJSON ===
    file_size = get_file_size_mb(osm_file)
    log.info(f"🧩 Converting {osm_file} ({file_size} MB) to GeoJSON → {geojson_file}")

    try:
        convert_start = time.time()
        run_osmium_extract(osm_file, geojson_file)
        convert_duration = time.time() - convert_start
        log.info(f"✅ Conversion completed successfully in {convert_duration:.1f}s")
    except Exception as e:
        log.error(f"❌ Conversion failed: {e}")
        sys.exit(1)

    # === STEP 2: Create SQL file from GeoJSON ===
    try:
        import json
        log.info(f"🗃️ Generating SQL insert file → {sql_file}")

        with open(geojson_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        with open(sql_file, "w", encoding="utf-8") as sql_out:
            sql_out.write("BEGIN;\n")
            for feature in data.get("features", []):
                props = feature.get("properties", {})
                geom = feature.get("geometry", {})
                if geom.get("type") == "Point":
                    lon, lat = geom.get("coordinates", [None, None])
                    postcode = props.get("addr:postcode")
                    if postcode and lat and lon:
                        sql_out.write(
                            f"INSERT INTO postal_lookup (postcode, lat, lon) VALUES ('{postcode}', {lat}, {lon}) ON CONFLICT DO NOTHING;\n"
                        )
            sql_out.write("COMMIT;\n")

        log.info(f"✅ SQL file generated successfully: {sql_file}")
    except Exception as e:
        log.error(f"❌ SQL generation failed: {e}")
        sys.exit(1)

    # === STEP 3: Execute SQL into PostGIS ===
    try:
        log.info("🗄️ Executing SQL commands into PostGIS...")
        os.system(
            f"psql postgresql://osmuser:osmpass@db:5432/osm -f {sql_file}"
        )
        log.info("✅ SQL import completed successfully.")
    except Exception as e:
        log.error(f"❌ SQL import failed: {e}")
        sys.exit(1)

    total_time = time.time() - start_time
    log.info(f"🏁 OSM import pipeline finished in {timedelta(seconds=int(total_time))}")


if __name__ == "__main__":
    main()
