import express from "express";
import pkg from "pg";
import cors from "cors";
import morgan from "morgan";

const { Pool } = pkg;

const app = express();
app.use(cors());
app.use(express.json());
app.use(morgan("dev"));

const pool = new Pool({
  host: process.env.DB_HOST || "db",
  port: process.env.DB_PORT || 5432,
  user: process.env.DB_USER || "osmuser",
  password: process.env.DB_PASS || "osmpass",
  database: process.env.DB_NAME || "osm",
});

// Utility to handle queries
async function query(sql, params = []) {
  const client = await pool.connect();
  try {
    const res = await client.query(sql, params);
    return res.rows;
  } finally {
    client.release();
  }
}

// --- Routes ---

// Postal lookup by postcode
app.get("/lookup", async (req, res) => {
  const { postal } = req.query;
  if (!postal) return res.status(400).json({ error: "Missing ?postal parameter" });
  try {
    const rows = await query(
      "SELECT postcode, lat, lon FROM postal_lookup WHERE postcode = $1",
      [postal]
    );
    if (!rows.length) return res.status(404).json({ message: "Postal code not found" });
    res.json(rows);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: "Database error" });
  }
});

// Node info
app.get("/node/:id", async (req, res) => {
  try {
    const rows = await query("SELECT * FROM osm_nodes WHERE id = $1", [req.params.id]);
    if (!rows.length) return res.status(404).json({ message: "Node not found" });
    res.json(rows[0]);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Way info
app.get("/way/:id", async (req, res) => {
  try {
    const rows = await query("SELECT * FROM osm_ways WHERE id = $1", [req.params.id]);
    if (!rows.length) return res.status(404).json({ message: "Way not found" });
    res.json(rows[0]);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Relation info
app.get("/relation/:id", async (req, res) => {
  try {
    const rows = await query("SELECT * FROM osm_relations WHERE id = $1", [req.params.id]);
    if (!rows.length) return res.status(404).json({ message: "Relation not found" });
    res.json(rows[0]);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get("/", (_, res) => {
  res.json({
    message: "OSM Geocoder API",
    endpoints: ["/lookup?postal=XXXXX", "/node/:id", "/way/:id", "/relation/:id"],
  });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`🌍 API listening on port ${PORT}`));
