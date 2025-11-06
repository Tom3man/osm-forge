import json
from typing import Dict, List, Optional, Tuple

import geopandas as gpd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from .config import DEFAULT_PRESET, FEATURE_PRESETS, FeaturePreset
from .db import list_regions as list_regions_db
from .db import query_features

app = FastAPI(title="OSMForge API")


def _get_preset(preset_key: str) -> FeaturePreset:
    try:
        return FEATURE_PRESETS[preset_key]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown preset '{preset_key}'") from exc


def _parse_bbox(raw: Optional[str]) -> Optional[Tuple[float, float, float, float]]:
    if not raw:
        return None
    try:
        parts = [float(p.strip()) for p in raw.split(",")]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="bbox must be comma separated floats") from exc
    if len(parts) != 4:
        raise HTTPException(status_code=400, detail="bbox must contain four values")
    west, south, east, north = parts
    if west >= east or south >= north:
        raise HTTPException(status_code=400, detail="bbox coordinates are invalid")
    return west, south, east, north


def _df_to_geojson(df) -> Dict[str, object]:
    gdf = gpd.GeoDataFrame(
        df.drop(columns=["geometry_wkb"]),
        geometry=gpd.GeoSeries.from_wkb(df["geometry_wkb"], crs="EPSG:4326"),
    )
    return json.loads(gdf.to_json())


@app.get("/presets")
def get_presets() -> List[Dict[str, object]]:
    """
    List supported feature presets.
    """
    return [
        {
            "key": preset.key,
            "title": preset.title,
            "primary_tag": preset.primary_tag,
        }
        for preset in FEATURE_PRESETS.values()
    ]


@app.get("/regions")
def get_regions(
    preset: str = Query(DEFAULT_PRESET, description="Feature preset key"),
) -> Dict[str, object]:
    """
    List regions with locally ingested data for the chosen preset.
    """
    preset_cfg = _get_preset(preset)
    regions = list_regions_db(preset_cfg.key)
    return {"preset": preset_cfg.key, "regions": regions}


@app.get("/features")
def get_features(
    preset: str = Query(DEFAULT_PRESET, description="Feature preset key"),
    region: Optional[str] = Query(None, description="Optional region filter"),
    bbox: Optional[str] = Query(
        None,
        description="Bounding box (west,south,east,north) in WGS84",
    ),
    limit: Optional[int] = Query(
        None,
        ge=1,
        le=10000,
        description="Limit the number of features returned",
    ),
):
    """
    Return features as a GeoJSON FeatureCollection.
    """
    preset_cfg = _get_preset(preset)
    bbox_tuple = _parse_bbox(bbox)
    df = query_features(
        preset_cfg.key,
        region=region,
        limit=limit,
        bbox=bbox_tuple,
    )
    if df.empty:
        return JSONResponse(
            {"type": "FeatureCollection", "features": []},
            media_type="application/geo+json",
        )

    geojson = _df_to_geojson(df)
    return JSONResponse(geojson, media_type="application/geo+json")
