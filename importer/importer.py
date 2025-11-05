import sys
import os
import subprocess
import psycopg2
import structlog
from tqdm import tqdm

log = structlog.get_logger()

DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "osmuser")
DB_PASS = os.getenv("DB_PASS", "osmpass")
DB_NAME = os.getenv("DB_NAME", "osm")


def connect_db():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS, dbname=DB_NAME
    )


def run_osmium_extract(input_file, output_file):
    """
    Uses osmium-tool CLI to convert .pbf to .geojson
    """
    log.info("running_osmium_tool", input=input_file, output=output_file)
    cmd = ["osmium", "export", input_file, "-o", output_file, "-f", "geojson"]
    subprocess.run(cmd, check=True)
    log.info("osmium_export_done", output=output_file)


def process_geojson(geojson_file):
    """
    Reads converted GeoJSON and inserts into database.
    """
    import json

    log.info("processing_geojson", file=geojson_file)
    conn = connect_db()

    with open(geojson_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    for feature in tqdm(data.get("features", []), desc="Importing features"):
        props = feature.get("properties", {})
        geometry = feature.get("geometry", {})
        lat = None
        lon = None

        if geometry.get("type") == "Point":
            lon, lat = geometry["coordinates"]

        if lat and lon:
            postcode = props.get("addr:postcode")
            if postcode:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO postal_lookup (postcode, lat, lon)
                        VALUES (%s, %s, %s)
                        ON CONFLICT DO NOTHING;
                        """,
                        (postcode, lat, lon),
                    )
    conn.commit()
    conn.close()
    log.info("import_complete")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: import_osm.py <osm.pbf file>")
        sys.exit(1)

    osm_file = sys.argv[1]
    if not os.path.exists(osm_file):
        print(f"File not found: {osm_file}")
        sys.exit(1)

    geojson_file = "/tmp/output.geojson"
    log.info("start_processing", osm_file=osm_file)

    run_osmium_extract(osm_file, geojson_file)
    process_geojson(geojson_file)

    log.info("finished", osm_file=osm_file)
