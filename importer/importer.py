import sys
import os
import json
import time
import logging
import psycopg2
import osmium

# ---------------------------------------------------
# Logging configuration
# ---------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# ---------------------------------------------------
# Database configuration
# ---------------------------------------------------
DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "osmuser")
DB_PASS = os.getenv("DB_PASS", "osmpass")
DB_NAME = os.getenv("DB_NAME", "osm")

def connect_db():
    logging.info(f"Connecting to PostgreSQL at {DB_HOST}:{DB_PORT}...")
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        dbname=DB_NAME
    )
    logging.info("Database connection established.")
    return conn

def insert_data(conn, table, columns, values):
    try:
        with conn.cursor() as cur:
            placeholders = ",".join(["%s"] * len(values))
            cur.execute(
                f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders}) ON CONFLICT DO NOTHING;",
                values,
            )
        conn.commit()
    except Exception as e:
        logging.error(f"Failed to insert into {table}: {e}")
        conn.rollback()

# ---------------------------------------------------
# OSM Handler
# ---------------------------------------------------
class OSMHandler(osmium.SimpleHandler):
    def __init__(self, conn):
        super().__init__()
        self.conn = conn
        self.count_nodes = 0
        self.count_ways = 0
        self.count_relations = 0
        self.count_postcodes = 0
        self.start_time = time.time()

    def node(self, n):
        tags = {k: v for k, v in n.tags}
        lat, lon = n.location.lat, n.location.lon

        insert_data(
            self.conn,
            "osm_nodes",
            ["id", "lat", "lon", "tags"],
            [n.id, lat, lon, json.dumps(tags)]
        )
        self.count_nodes += 1

        postcode = tags.get("addr:postcode")
        if postcode:
            insert_data(
                self.conn,
                "postal_lookup",
                ["postcode", "lat", "lon"],
                [postcode, lat, lon]
            )
            self.count_postcodes += 1

        if self.count_nodes % 10000 == 0:
            elapsed = time.time() - self.start_time
            logging.info(f"Processed {self.count_nodes} nodes ({self.count_postcodes} postal codes) in {elapsed:.1f}s")

    def way(self, w):
        tags = {k: v for k, v in w.tags}
        nodes = [n.ref for n in w.nodes]
        insert_data(
            self.conn,
            "osm_ways",
            ["id", "nodes", "tags"],
            [w.id, json.dumps(nodes), json.dumps(tags)]
        )
        self.count_ways += 1

        if self.count_ways % 5000 == 0:
            logging.info(f"Processed {self.count_ways} ways")

    def relation(self, r):
        tags = {k: v for k, v in r.tags}
        members = [{"ref": m.ref, "type": m.type, "role": m.role} for m in r.members]
        insert_data(
            self.conn,
            "osm_relations",
            ["id", "members", "tags"],
            [r.id, json.dumps(members), json.dumps(tags)]
        )
        self.count_relations += 1

        if self.count_relations % 1000 == 0:
            logging.info(f"Processed {self.count_relations} relations")

# ---------------------------------------------------
# Processing function
# ---------------------------------------------------
def process_osm(osm_file):
    conn = connect_db()
    handler = OSMHandler(conn)
    logging.info(f"Starting OSM import from {osm_file}...")
    start_time = time.time()
    try:
        handler.apply_file(osm_file, locations=True)
    except Exception as e:
        logging.error(f"Error while parsing OSM file: {e}")
    finally:
        conn.close()

    elapsed = time.time() - start_time
    logging.info("----------------------------------------------------")
    logging.info("OSM import completed.")
    logging.info(f"Nodes: {handler.count_nodes}")
    logging.info(f"Ways: {handler.count_ways}")
    logging.info(f"Relations: {handler.count_relations}")
    logging.info(f"Postal Codes: {handler.count_postcodes}")
    logging.info(f"Total time: {elapsed:.1f} seconds")
    logging.info("----------------------------------------------------")

# ---------------------------------------------------
# Main
# ---------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        logging.error("Usage: importer.py <osm.pbf file>")
        sys.exit(1)

    osm_file = sys.argv[1]
    if not os.path.exists(osm_file):
        logging.error(f"File not found: {osm_file}")
        sys.exit(1)

    process_osm(osm_file)
