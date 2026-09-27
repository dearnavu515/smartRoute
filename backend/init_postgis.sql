-- =============================================================
-- smartRoute: PostgreSQL + PostGIS Database Initialization Script
-- Enables PostGIS extension and creates spatial tables & indices
-- =============================================================

-- 1. Enable PostGIS Extension for Spatial/Geographic Features
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- 2. Create Stops Table with Geometry Support
CREATE TABLE IF NOT EXISTS stops (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    lat DOUBLE PRECISION NOT NULL,
    lon DOUBLE PRECISION NOT NULL,
    mode VARCHAR(50) NOT NULL,    -- 'metro', 'water_metro', 'bus', 'walk'
    agency VARCHAR(50) NOT NULL,  -- 'KMRL', 'KWML', 'FeederBus'
    zone_id VARCHAR(50),
    geom GEOMETRY(Point, 4326)   -- PostGIS WGS84 Spatial Point
);

-- Spatial Index for Fast Geographic Queries (Nearest Stops, Bounding Box)
CREATE INDEX IF NOT EXISTS idx_stops_geom ON stops USING GIST(geom);

-- Automatically update geom column from lat/lon on insert/update
CREATE OR REPLACE FUNCTION update_stop_geom()
RETURNS TRIGGER AS $$
BEGIN
    NEW.geom = ST_SetSRID(ST_MakePoint(NEW.lon, NEW.lat), 4326);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_update_stop_geom ON stops;
CREATE TRIGGER trg_update_stop_geom
BEFORE INSERT OR UPDATE ON stops
FOR EACH ROW EXECUTE FUNCTION update_stop_geom();

-- 3. Create Routes Table
CREATE TABLE IF NOT EXISTS routes (
    id VARCHAR(50) PRIMARY KEY,
    short_name VARCHAR(100) NOT NULL,
    long_name VARCHAR(255) NOT NULL,
    mode VARCHAR(50) NOT NULL,
    agency VARCHAR(50) NOT NULL,
    color VARCHAR(20) DEFAULT '#3B82F6'
);

-- 4. Create Multimodal Edges Table with LineString Geometry
CREATE TABLE IF NOT EXISTS edges (
    id SERIAL PRIMARY KEY,
    route_id VARCHAR(50) REFERENCES routes(id) ON DELETE SET NULL,
    from_stop_id VARCHAR(50) REFERENCES stops(id) ON DELETE CASCADE,
    to_stop_id VARCHAR(50) REFERENCES stops(id) ON DELETE CASCADE,
    mode VARCHAR(50) NOT NULL,
    distance_km DOUBLE PRECISION DEFAULT 0.0,
    duration_min DOUBLE PRECISION DEFAULT 0.0,
    fare DOUBLE PRECISION DEFAULT 0.0,
    geometry TEXT,              -- JSON coordinate sequence
    line_geom GEOMETRY(LineString, 4326) -- PostGIS LineString geometry
);

-- Spatial Index on Multimodal Edges
CREATE INDEX IF NOT EXISTS idx_edges_line_geom ON edges USING GIST(line_geom);

-- 5. Create Fare Rules Table
CREATE TABLE IF NOT EXISTS fare_rules (
    id SERIAL PRIMARY KEY,
    mode VARCHAR(50) NOT NULL,
    origin_id VARCHAR(50) NOT NULL,
    destination_id VARCHAR(50) NOT NULL,
    fare DOUBLE PRECISION NOT NULL
);

-- Verify PostGIS Installation
SELECT PostGIS_Full_Version();
