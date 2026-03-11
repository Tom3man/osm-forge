import json
import os
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Query
from pydantic import BaseModel
from sqlalchemy import create_engine, text

app = FastAPI(title="Local OSM API")

DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_engine(DATABASE_URL, future=True)

ALL_LAYERS = {
    "buildings", "roads", "water",
    "vegetation", "landuse", "structures", "terrain",
}


# ---------------------------------------------------------------------------
# Shared query builder
# ---------------------------------------------------------------------------

def _build_unions(geom_expr: str, requested: set) -> List[str]:
    """Return a list of UNION ALL fragments, each filtering by geom_expr."""
    unions = []

    if "buildings" in requested:
        unions.append(f"""
            SELECT b.osm_id, b.name,
                'buildings'       AS layer,
                b.building_type   AS feature_class,
                b.height_m        AS height_m,
                b.building_levels AS levels,
                b.material        AS material,
                ST_AsGeoJSON(b.geom)::json AS geometry
            FROM app.osm_buildings b
            WHERE ST_Intersects(b.geom, {geom_expr})
        """)

    if "vegetation" in requested:
        unions.append(f"""
            SELECT v.osm_id, v.name,
                'vegetation'       AS layer,
                v.vegetation_class AS feature_class,
                NULL AS height_m, NULL AS levels, NULL AS material,
                ST_AsGeoJSON(v.geom)::json AS geometry
            FROM app.osm_vegetation v
            WHERE ST_Intersects(v.geom, {geom_expr})
        """)

    if "water" in requested:
        unions.append(f"""
            SELECT w.osm_id, w.name,
                'water'       AS layer,
                w.water_class AS feature_class,
                NULL AS height_m, NULL AS levels, NULL AS material,
                ST_AsGeoJSON(w.geom)::json AS geometry
            FROM app.osm_water w
            WHERE ST_Intersects(w.geom, {geom_expr})
        """)

    if "roads" in requested:
        unions.append(f"""
            SELECT r.osm_id, r.name,
                'roads'           AS layer,
                r.transport_class AS feature_class,
                NULL AS height_m, NULL AS levels, NULL AS material,
                ST_AsGeoJSON(r.geom)::json AS geometry
            FROM app.osm_roads r
            WHERE ST_Intersects(r.geom, {geom_expr})
        """)

    if "landuse" in requested:
        unions.append(f"""
            SELECT lu.osm_id, lu.name,
                'landuse'        AS layer,
                lu.landuse_class AS feature_class,
                NULL AS height_m, NULL AS levels, NULL AS material,
                ST_AsGeoJSON(lu.geom)::json AS geometry
            FROM app.osm_landuse lu
            WHERE ST_Intersects(lu.geom, {geom_expr})
        """)

    if "structures" in requested:
        unions.append(f"""
            SELECT s.osm_id, s.name,
                'structures'      AS layer,
                s.structure_class AS feature_class,
                NULL AS height_m, NULL AS levels, NULL AS material,
                ST_AsGeoJSON(s.geom)::json AS geometry
            FROM app.osm_structures s
            WHERE ST_Intersects(s.geom, {geom_expr})
        """)

    if "terrain" in requested:
        unions.append(f"""
            SELECT t.osm_id, t.name,
                'terrain'       AS layer,
                t.terrain_class AS feature_class,
                t.height_m      AS height_m,
                NULL AS levels, NULL AS material,
                ST_AsGeoJSON(t.geom)::json AS geometry
            FROM app.osm_terrain t
            WHERE ST_Intersects(t.geom, {geom_expr})
        """)

    return unions


def _execute_propagation(unions: List[str], params: Dict[str, Any], limit: Optional[int]) -> dict:
    if not unions:
        return {"type": "FeatureCollection", "features": []}

    body = " UNION ALL ".join(unions)
    limit_clause = "LIMIT :limit" if limit else ""

    sql = text(f"""
        SELECT json_build_object(
            'type', 'FeatureCollection',
            'features', COALESCE(json_agg(
                json_build_object(
                    'type', 'Feature',
                    'geometry', f.geometry,
                    'properties', json_build_object(
                        'osm_id',        f.osm_id,
                        'name',          f.name,
                        'layer',         f.layer,
                        'feature_class', f.feature_class,
                        'height_m',      f.height_m,
                        'levels',        f.levels,
                        'material',      f.material
                    )
                )
            ), '[]'::json)
        )
        FROM (SELECT * FROM ({body}) q {limit_clause}) f
    """)

    with engine.connect() as conn:
        return conn.execute(sql, {**params, "limit": limit}).scalar_one()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/features/bbox")
def features_bbox(
    min_lon: float = Query(...),
    min_lat: float = Query(...),
    max_lon: float = Query(...),
    max_lat: float = Query(...),
    limit: int = Query(default=None),
) -> dict:
    """Return raw OSM features (points + lines + polygons) in a bounding box."""
    sql = text("""
        WITH bbox AS (
            SELECT ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326) AS geom
        ),
        features AS (
            SELECT 'point' AS source_layer, p.osm_id, p.name, p.tags,
                   ST_AsGeoJSON(p.geom)::json AS geometry
            FROM osm.osm_points p CROSS JOIN bbox
            WHERE ST_Intersects(p.geom, bbox.geom)
            UNION ALL
            SELECT 'line', l.osm_id, l.name, l.tags,
                   ST_AsGeoJSON(l.geom)::json
            FROM osm.osm_lines l CROSS JOIN bbox
            WHERE ST_Intersects(l.geom, bbox.geom)
            UNION ALL
            SELECT 'polygon', pg.osm_id, pg.name, pg.tags,
                   ST_AsGeoJSON(pg.geom)::json
            FROM osm.osm_polygons pg CROSS JOIN bbox
            WHERE ST_Intersects(pg.geom, bbox.geom)
        )
        SELECT json_build_object(
            'type', 'FeatureCollection',
            'features', COALESCE(json_agg(
                json_build_object(
                    'type', 'Feature',
                    'geometry', f.geometry,
                    'properties', json_build_object(
                        'osm_id', f.osm_id,
                        'name', f.name,
                        'source_layer', f.source_layer,
                        'tags', f.tags
                    )
                )
            ), '[]'::json)
        )
        FROM (SELECT * FROM features LIMIT :limit) f
    """)

    with engine.connect() as conn:
        return conn.execute(sql, {
            "min_lon": min_lon, "min_lat": min_lat,
            "max_lon": max_lon, "max_lat": max_lat,
            "limit": limit,
        }).scalar_one()


@app.get("/propagation/bbox")
def propagation_bbox(
    min_lon: float = Query(...),
    min_lat: float = Query(...),
    max_lon: float = Query(...),
    max_lat: float = Query(...),
    layers: List[str] = Query(default=sorted(ALL_LAYERS)),
    limit: int = Query(default=None),
) -> dict:
    """
    Return pre-classified OSM features in a bounding box for propagation modelling.
    Filter layers via: ?layers=buildings&layers=vegetation
    """
    requested = ALL_LAYERS & set(layers)
    geom_expr = "ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326)"
    unions = _build_unions(geom_expr, requested)
    params = {"min_lon": min_lon, "min_lat": min_lat, "max_lon": max_lon, "max_lat": max_lat}
    return _execute_propagation(unions, params, limit)


class GeometryQuery(BaseModel):
    geometry: Dict[str, Any]  # GeoJSON geometry object (Polygon or MultiPolygon)
    layers: List[str] = sorted(ALL_LAYERS)
    limit: Optional[int] = None


@app.post("/propagation/geometry")
def propagation_geometry(body: GeometryQuery) -> dict:
    """
    Return pre-classified OSM features intersecting an arbitrary Polygon or
    MultiPolygon supplied as a GeoJSON geometry object.

    Example body:
        {
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[...]]]
            },
            "layers": ["buildings", "vegetation"],
            "limit": 5000
        }
    """
    requested = ALL_LAYERS & set(body.layers)
    geom_expr = "ST_GeomFromGeoJSON(:geojson)"
    unions = _build_unions(geom_expr, requested)
    params = {"geojson": json.dumps(body.geometry)}
    return _execute_propagation(unions, params, body.limit)
