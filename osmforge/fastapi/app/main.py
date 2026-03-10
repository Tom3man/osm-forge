from fastapi import FastAPI, Query
from sqlalchemy import create_engine, text
import os

app = FastAPI(title="Local OSM API")

DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_engine(DATABASE_URL, future=True)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/features/bbox")
def features_bbox(
    min_lon: float = Query(...),
    min_lat: float = Query(...),
    max_lon: float = Query(...),
    max_lat: float = Query(...),
    limit: int = Query(1000, ge=1, le=10000),
) -> dict:
    """
    Return OSM polygon features intersecting the given bounding box as GeoJSON.
    """
    sql = text(
        """
        WITH bbox AS (
            SELECT ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326) AS geom
        ),
        features AS (
            SELECT
                p.osm_id,
                p.name,
                'polygon' AS feature_type,
                ST_AsGeoJSON(p.geom)::json AS geometry,
                json_build_object(
                    'osm_id', p.osm_id,
                    'name', p.name,
                    'feature_type', 'polygon',
                    'amenity', p.amenity,
                    'building', p.building,
                    'landuse', p.landuse,
                    'leisure', p.leisure
                ) AS properties
            FROM osm.osm_polygons p
            CROSS JOIN bbox
            WHERE ST_Intersects(p.geom, bbox.geom)

            UNION ALL

            SELECT
                l.osm_id,
                l.name,
                'line' AS feature_type,
                ST_AsGeoJSON(l.geom)::json AS geometry,
                json_build_object(
                    'osm_id', l.osm_id,
                    'name', l.name,
                    'feature_type', 'line',
                    'highway', l.highway,
                    'railway', l.railway
                ) AS properties
            FROM osm.osm_lines l
            CROSS JOIN bbox
            WHERE ST_Intersects(l.geom, bbox.geom)

            UNION ALL

            SELECT
                pt.osm_id,
                pt.name,
                'point' AS feature_type,
                ST_AsGeoJSON(pt.geom)::json AS geometry,
                json_build_object(
                    'osm_id', pt.osm_id,
                    'name', pt.name,
                    'feature_type', 'point'
                ) AS properties
            FROM osm.osm_points pt
            CROSS JOIN bbox
            WHERE ST_Intersects(pt.geom, bbox.geom)
        )
        SELECT json_build_object(
            'type', 'FeatureCollection',
            'features', COALESCE(json_agg(
                json_build_object(
                    'type', 'Feature',
                    'geometry', geometry,
                    'properties', properties
                )
            ), '[]'::json)
        ) AS geojson
        FROM (
            SELECT *
            FROM features
            LIMIT :limit
        ) q
        """
    )

    with engine.connect() as conn:
        result = conn.execute(
            sql,
            {
                "min_lon": min_lon,
                "min_lat": min_lat,
                "max_lon": max_lon,
                "max_lat": max_lat,
                "limit": limit,
            },
        ).scalar_one()

    return result
