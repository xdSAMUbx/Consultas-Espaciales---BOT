-- Corrige geometrías con auto-intersecciones que rompen ST_Union
UPDATE nyc_neighborhoods   SET geom = ST_MakeValid(geom) WHERE NOT ST_IsValid(geom);
UPDATE nyc_census_blocks   SET geom = ST_MakeValid(geom) WHERE NOT ST_IsValid(geom);
UPDATE nyc_streets         SET geom = ST_MakeValid(geom) WHERE NOT ST_IsValid(geom);
UPDATE nyc_homicides       SET geom = ST_MakeValid(geom) WHERE NOT ST_IsValid(geom);

-- Índices espaciales: sin esto los joins tardan segundos en vez de milisegundos
CREATE INDEX IF NOT EXISTS idx_neighborhoods_geom ON nyc_neighborhoods   USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_census_blocks_geom ON nyc_census_blocks   USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_streets_geom       ON nyc_streets         USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_subway_geom        ON nyc_subway_stations USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_homicides_geom     ON nyc_homicides       USING GIST (geom);

-- Índices de atributos que el bot filtra con frecuencia
CREATE INDEX IF NOT EXISTS idx_neighborhoods_boro ON nyc_neighborhoods   (boroname);
CREATE INDEX IF NOT EXISTS idx_neighborhoods_name ON nyc_neighborhoods   (name);
CREATE INDEX IF NOT EXISTS idx_subway_borough     ON nyc_subway_stations (borough);
CREATE INDEX IF NOT EXISTS idx_streets_type       ON nyc_streets         (type);
CREATE INDEX IF NOT EXISTS idx_homicides_year     ON nyc_homicides       (year);

ANALYZE;