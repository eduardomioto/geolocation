import os
import sys
import time
import logging
from datetime import timedelta

# Import the streaming converter
from convert_geojson_to_sql import convert_geojson_to_sql

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-7s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("osm_importer")


def run_ogr2ogr_to_sql(geojson_file: str, sql_file: str, postal_key: str = "postal_code"):
    log.info(f"Converting GeoJSON → SQL dump (streaming) → {sql_file}")
    convert_geojson_to_sql(
        input_path=geojson_file,
        output_path=sql_file,
        postal_key=postal_key,
    )
    log.info("SQL export completed successfully")


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <osm.pbf file>")
        sys.exit(1)

    osm_file = sys.argv[1]
    base_name = os.path.basename(osm_file).replace(".osm.pbf", "")
    geojson_file = f"/data/geojson/{base_name}.geojson"
    sql_file = f"/data/sql/{base_name}_postal_lookup.sql"

    os.makedirs("/data/geojson", exist_ok=True)
    os.makedirs("/data/sql", exist_ok=True)

    start = time.time()

    from convert_pbf import run_osmium_extract
    run_osmium_extract(osm_file, geojson_file)
    run_ogr2ogr_to_sql(geojson_file, sql_file, postal_key="postal_code")

    log.info(f"Conversion completed in {timedelta(seconds=int(time.time() - start))}")


if __name__ == "__main__":
    main()