"""
Thin Python client for the local OSM API.

Usage:
    from osmforge.client import OSMClient

    client = OSMClient()  # defaults to http://localhost:8000

    # By bounding box
    gdf = client.propagation_bbox(min_lon=-1.6, min_lat=50.55, max_lon=-1.0, max_lat=50.85)

    # By arbitrary polygon / multipolygon (shapely or GeoJSON dict)
    gdf = client.propagation_geometry(my_polygon)

    # Filter to specific layers
    gdf = client.propagation_geometry(my_polygon, layers=["buildings", "terrain"])

    # Raw OSM tags (no classification)
    gdf = client.features_bbox(min_lon=-1.6, min_lat=50.55, max_lon=-1.0, max_lat=50.85)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

import geopandas as gpd
import requests

try:
    from shapely.geometry import mapping
    from shapely.geometry.base import BaseGeometry
    _SHAPELY = True
except ImportError:
    _SHAPELY = False

_GeoJSON = Dict[str, Any]
_Geometry = Union[_GeoJSON, "BaseGeometry"]

ALL_LAYERS = [
    "buildings", "roads", "water",
    "vegetation", "landuse", "structures", "terrain",
]


def _to_geojson(geometry: _Geometry) -> _GeoJSON:
    if isinstance(geometry, dict):
        return geometry
    if _SHAPELY and isinstance(geometry, BaseGeometry):
        return mapping(geometry)
    raise TypeError(
        f"geometry must be a GeoJSON dict or a Shapely geometry, got {type(geometry)}"
    )


class OSMClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")

    def _get(self, path: str, params: dict) -> dict:
        r = requests.get(f"{self.base_url}{path}", params=params, timeout=120)
        r.raise_for_status()
        return r.json()

    def _post(self, path: str, body: dict) -> dict:
        r = requests.post(f"{self.base_url}{path}", json=body, timeout=120)
        r.raise_for_status()
        return r.json()

    @staticmethod
    def _to_gdf(fc: dict) -> gpd.GeoDataFrame:
        features = fc.get("features", [])
        if not features:
            return gpd.GeoDataFrame()
        return gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def propagation_bbox(
        self,
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float,
        layers: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> gpd.GeoDataFrame:
        """
        Return propagation-classified features within a bounding box.

        Parameters
        ----------
        min_lon, min_lat, max_lon, max_lat : float
            Bounding box in WGS-84 degrees.
        layers : list of str, optional
            Subset of ALL_LAYERS to include. Defaults to all.
        limit : int, optional
            Maximum number of features to return.
        """
        params: dict = {
            "min_lon": min_lon, "min_lat": min_lat,
            "max_lon": max_lon, "max_lat": max_lat,
        }
        for layer in (layers or ALL_LAYERS):
            params.setdefault("layers", [])
            params["layers"].append(layer)
        if limit is not None:
            params["limit"] = limit
        return self._to_gdf(self._get("/propagation/bbox", params))

    def propagation_geometry(
        self,
        geometry: _Geometry,
        layers: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> gpd.GeoDataFrame:
        """
        Return propagation-classified features intersecting a polygon or multipolygon.

        Parameters
        ----------
        geometry : GeoJSON dict or Shapely geometry
            The area of interest (Polygon or MultiPolygon).
        layers : list of str, optional
            Subset of ALL_LAYERS to include. Defaults to all.
        limit : int, optional
            Maximum number of features to return.
        """
        body: dict = {"geometry": _to_geojson(geometry), "layers": layers or ALL_LAYERS}
        if limit is not None:
            body["limit"] = limit
        return self._to_gdf(self._post("/propagation/geometry", body))

    def features_bbox(
        self,
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float,
        limit: Optional[int] = None,
    ) -> gpd.GeoDataFrame:
        """
        Return raw OSM features (all tags) within a bounding box.

        Useful for exploration; use propagation_bbox for modelling.
        """
        params: dict = {
            "min_lon": min_lon, "min_lat": min_lat,
            "max_lon": max_lon, "max_lat": max_lat,
        }
        if limit is not None:
            params["limit"] = limit
        return self._to_gdf(self._get("/features/bbox", params))
