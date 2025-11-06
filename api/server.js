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
      "SELECT lon, lat, cep FROM cep_to_coords($1)",
      [postal]
    );
    if (!rows.length) return res.status(404).json({ message: "Postal code not found" });
    res.json(rows);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: "Database error" });
  }
});

app.get("/", (_, res) => {
  res.json({
    message: "OSM Geocoder API",
    endpoints: ["/lookup?postal=XXXXX"],
  });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`🌍 API listening on port ${PORT}`));
