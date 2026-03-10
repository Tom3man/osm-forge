-- Run this AFTER osm2pgsql has loaded data into the osm schema.
-- e.g.  make ingest && make layers

DROP TABLE IF EXISTS app.osm_buildings;

CREATE TABLE app.osm_buildings AS
SELECT
    osm_id,
    name,
    building AS building_type,
    COALESCE(tags->>'building:levels', tags->>'levels') AS building_levels,
    tags->>'height' AS height,
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
