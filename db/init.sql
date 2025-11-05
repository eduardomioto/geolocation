CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS postal_lookup (
  id SERIAL PRIMARY KEY,
  postcode VARCHAR,
  lat DOUBLE PRECISION,
  lon DOUBLE PRECISION
);

CREATE INDEX IF NOT EXISTS idx_postal ON postal_lookup(postcode);

-- Other general-purpose tables to store remaining data
CREATE TABLE IF NOT EXISTS osm_nodes (
  id BIGINT PRIMARY KEY,
  lat DOUBLE PRECISION,
  lon DOUBLE PRECISION,
  tags JSONB
);

CREATE TABLE IF NOT EXISTS osm_ways (
  id BIGINT PRIMARY KEY,
  nodes BIGINT[],
  tags JSONB
);

CREATE TABLE IF NOT EXISTS osm_relations (
  id BIGINT PRIMARY KEY,
  members JSONB,
  tags JSONB
);
