-- Run this AFTER osm2pgsql has loaded data into the osm schema.
-- e.g.  make ingest && make layers

DROP TABLE IF EXISTS app.osm_buildings;

CREATE TABLE app.osm_buildings AS
SELECT
    osm_id,
    name,
    building AS building_type,
    COALESCE(tags->>'building:levels', tags->>'levels') AS building_levels,
    -- Numeric height: use tagged height first, fall back to levels * 3 m
    CASE
        WHEN tags->>'height' ~ '^[0-9]+(\.[0-9]+)?$'
            THEN (tags->>'height')::float
        WHEN COALESCE(tags->>'building:levels', tags->>'levels') ~ '^[0-9]+$'
            THEN COALESCE(tags->>'building:levels', tags->>'levels')::float * 3.0
        ELSE NULL
    END AS height_m,
    tags->>'building:material' AS material,
    tags,
    geom
FROM osm.osm_polygons
WHERE building IS NOT NULL
  AND geom IS NOT NULL;

CREATE INDEX IF NOT EXISTS osm_buildings_geom_gix
ON app.osm_buildings USING GIST (geom);

CREATE INDEX IF NOT EXISTS osm_buildings_type_idx
ON app.osm_buildings (building_type);

ANALYZE app.osm_buildings;


DROP TABLE IF EXISTS app.osm_roads;

CREATE TABLE app.osm_roads AS
SELECT
    osm_id,
    name,
    highway,
    railway,
    CASE
        WHEN highway IN ('motorway', 'trunk', 'primary') THEN 'major'
        WHEN highway IN ('secondary', 'tertiary') THEN 'secondary'
        WHEN highway IN ('residential', 'unclassified', 'service', 'living_street') THEN 'local'
        WHEN highway IN ('track', 'path', 'footway', 'cycleway', 'bridleway') THEN 'minor_path'
        WHEN railway IS NOT NULL THEN 'rail'
        ELSE 'other'
    END AS transport_class,
    tags,
    geom
FROM osm.osm_lines
WHERE geom IS NOT NULL
  AND (highway IS NOT NULL OR railway IS NOT NULL);

CREATE INDEX IF NOT EXISTS osm_roads_geom_gix
ON app.osm_roads USING GIST (geom);

CREATE INDEX IF NOT EXISTS osm_roads_class_idx
ON app.osm_roads (transport_class);

ANALYZE app.osm_roads;


DROP TABLE IF EXISTS app.osm_water;

CREATE TABLE app.osm_water AS
SELECT
    osm_id,
    name,
    'polygon' AS geom_type,
    COALESCE(tags->>'natural', tags->>'water', landuse) AS water_class,
    tags,
    geom
FROM osm.osm_polygons
WHERE geom IS NOT NULL
  AND (
      tags->>'natural' = 'water'
      OR tags->>'water' IS NOT NULL
      OR tags->>'waterway' = 'riverbank'
      OR landuse IN ('reservoir', 'basin')
  )

UNION ALL

SELECT
    osm_id,
    name,
    'line' AS geom_type,
    COALESCE(tags->>'waterway', 'waterway') AS water_class,
    tags,
    geom
FROM osm.osm_lines
WHERE geom IS NOT NULL
  AND tags->>'waterway' IS NOT NULL;

CREATE INDEX IF NOT EXISTS osm_water_geom_gix
ON app.osm_water USING GIST (geom);

CREATE INDEX IF NOT EXISTS osm_water_class_idx
ON app.osm_water (water_class);

ANALYZE app.osm_water;


DROP TABLE IF EXISTS app.osm_vegetation;

CREATE TABLE app.osm_vegetation AS
SELECT
    osm_id,
    name,
    CASE
        WHEN landuse = 'forest' THEN 'forest'
        WHEN tags->>'natural' = 'wood' THEN 'wood'
        WHEN tags->>'natural' = 'scrub' THEN 'scrub'
        WHEN tags->>'natural' = 'heath' THEN 'heath'
        WHEN tags->>'natural' = 'grassland' THEN 'grassland'
        WHEN leisure = 'park' THEN 'park'
        WHEN landuse = 'meadow' THEN 'meadow'
        WHEN landuse = 'grass' THEN 'grass'
        ELSE 'other_vegetation'
    END AS vegetation_class,
    tags,
    geom
FROM osm.osm_polygons
WHERE geom IS NOT NULL
  AND (
      landuse IN ('forest', 'meadow', 'grass')
      OR tags->>'natural' IN ('wood', 'scrub', 'heath', 'grassland')
      OR leisure = 'park'
  );

CREATE INDEX IF NOT EXISTS osm_vegetation_geom_gix
ON app.osm_vegetation USING GIST (geom);

CREATE INDEX IF NOT EXISTS osm_vegetation_class_idx
ON app.osm_vegetation (vegetation_class);

ANALYZE app.osm_vegetation;


DROP TABLE IF EXISTS app.osm_landuse;

CREATE TABLE app.osm_landuse AS
SELECT
    osm_id,
    name,
    landuse,
    CASE
        WHEN landuse IN ('residential') THEN 'residential'
        WHEN landuse IN ('industrial') THEN 'industrial'
        WHEN landuse IN ('commercial', 'retail') THEN 'commercial'
        WHEN landuse IN ('farmland', 'farmyard', 'orchard', 'vineyard') THEN 'agricultural'
        WHEN landuse IN ('forest') THEN 'forest'
        WHEN landuse IN ('quarry') THEN 'quarry'
        WHEN landuse IN ('military') THEN 'military'
        WHEN landuse IN ('cemetery') THEN 'cemetery'
        ELSE 'other'
    END AS landuse_class,
    tags,
    geom
FROM osm.osm_polygons
WHERE geom IS NOT NULL
  AND landuse IS NOT NULL;

CREATE INDEX IF NOT EXISTS osm_landuse_geom_gix
ON app.osm_landuse USING GIST (geom);

CREATE INDEX IF NOT EXISTS osm_landuse_class_idx
ON app.osm_landuse (landuse_class);

ANALYZE app.osm_landuse;


DROP TABLE IF EXISTS app.osm_structures;

CREATE TABLE app.osm_structures AS
SELECT
    osm_id,
    name,
    COALESCE(tags->>'man_made', tags->>'power') AS structure_class,
    tags,
    geom
FROM (
    SELECT osm_id, name, tags, geom
    FROM osm.osm_points
    WHERE tags->>'man_made' IN ('mast', 'tower', 'communications_tower')
       OR tags->>'power' IN ('tower', 'pole')

    UNION ALL

    SELECT osm_id, name, tags, geom
    FROM osm.osm_lines
    WHERE tags->>'man_made' IN ('bridge', 'embankment')
       OR tags->>'power' = 'line'

    UNION ALL

    SELECT osm_id, name, tags, geom
    FROM osm.osm_polygons
    WHERE tags->>'man_made' IN ('bridge', 'embankment', 'cutting')
) s;

CREATE INDEX IF NOT EXISTS osm_structures_geom_gix
ON app.osm_structures USING GIST (geom);

CREATE INDEX IF NOT EXISTS osm_structures_class_idx
ON app.osm_structures (structure_class);

ANALYZE app.osm_structures;


-- ---------------------------------------------------------------------------
-- Terrain obstacles — diffraction edges, coastline, elevation points.
-- These are the most important missing layer for RF propagation models.
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS app.osm_terrain;

CREATE TABLE app.osm_terrain AS

-- Linear terrain features: cliffs, ridges, coastline, walls, embankments
SELECT
    osm_id,
    name,
    CASE
        WHEN tags->>'natural' = 'cliff'                         THEN 'cliff'
        WHEN tags->>'natural' = 'ridge'                         THEN 'ridge'
        WHEN tags->>'natural' = 'coastline'                     THEN 'coastline'
        WHEN tags->>'barrier' IN ('wall', 'retaining_wall')     THEN 'barrier_wall'
        WHEN tags->>'man_made' = 'embankment'                   THEN 'embankment'
        WHEN tags->>'man_made' = 'cutting'                      THEN 'cutting'
        ELSE 'other'
    END AS terrain_class,
    -- height/ele as numeric where available
    CASE
        WHEN tags->>'height' ~ '^[0-9]+(\.[0-9]+)?$' THEN (tags->>'height')::float
        ELSE NULL
    END AS height_m,
    geom
FROM osm.osm_lines
WHERE geom IS NOT NULL
  AND (
      tags->>'natural'  IN ('cliff', 'ridge', 'coastline')
      OR tags->>'barrier'  IN ('wall', 'retaining_wall')
      OR tags->>'man_made' IN ('embankment', 'cutting')
  )

UNION ALL

-- Point terrain features: peaks, saddles, tall point structures
SELECT
    osm_id,
    name,
    CASE
        WHEN tags->>'natural'   = 'peak'                    THEN 'peak'
        WHEN tags->>'natural'   = 'saddle'                  THEN 'saddle'
        WHEN tags->>'man_made'  = 'chimney'                 THEN 'chimney'
        WHEN tags->>'man_made'  = 'storage_tank'            THEN 'storage_tank'
        WHEN tags->>'man_made'  = 'communications_tower'    THEN 'communications_tower'
        ELSE 'other'
    END AS terrain_class,
    CASE
        WHEN COALESCE(tags->>'height', tags->>'ele') ~ '^[0-9]+(\.[0-9]+)?$'
            THEN COALESCE(tags->>'height', tags->>'ele')::float
        ELSE NULL
    END AS height_m,
    geom
FROM osm.osm_points
WHERE geom IS NOT NULL
  AND (
      tags->>'natural'  IN ('peak', 'saddle')
      OR tags->>'man_made' IN ('chimney', 'storage_tank', 'communications_tower')
  );

CREATE INDEX IF NOT EXISTS osm_terrain_geom_gix
ON app.osm_terrain USING GIST (geom);

CREATE INDEX IF NOT EXISTS osm_terrain_class_idx
ON app.osm_terrain (terrain_class);

ANALYZE app.osm_terrain;
