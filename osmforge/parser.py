from pathlib import Path

import geopandas as gpd
import pandas as pd
from pyrosm import OSM

from .config import DATA_PATH, FeaturePreset, parquet_name


def _empty_result() -> gpd.GeoDataFrame:
    """
    Provide a consistent empty GeoDataFrame shape for downstream consumers.
    """
    return gpd.GeoDataFrame(
        columns=[
            "osm_id",
            "feature_type",
            "primary_value",
            "geometry",
            "source_region",
            "load_date",
        ],
        geometry="geometry",
    )


def extract_features(pbf_path: Path, preset: FeaturePreset) -> gpd.GeoDataFrame:
    """
    Extract features for a given preset from a .pbf file.
    """
    osm = OSM(pbf_path.as_posix())
    df = osm.get_data_by_custom_criteria(
        custom_filter=preset.custom_filter,
        filter_type="keep",
        keep_nodes=False,
        keep_ways=True,
        keep_relations=True,
    )
    if df is None or df.empty:
        return _empty_result()

    gdf = gpd.GeoDataFrame(df)
    gdf = gdf[gdf.geometry.notnull()]
    gdf = gdf[gdf.geometry.geom_type.isin(preset.geometry_types)]
    if gdf.empty:
        return _empty_result()

    gdf = gdf.rename(columns={"id": "osm_id"})
    if "osm_id" not in gdf.columns:
        gdf["osm_id"] = gdf.index.astype("int64")

    if preset.primary_tag in gdf.columns:
        primary_values = gdf[preset.primary_tag].fillna("unknown").astype(str)
    else:
        primary_values = pd.Series(["unknown"] * len(gdf), index=gdf.index)

    gdf["primary_value"] = primary_values
    gdf["feature_type"] = preset.key
    gdf["source_region"] = pbf_path.stem.replace("-latest", "")
    gdf["load_date"] = pd.Timestamp.utcnow()

    columns = [
        "osm_id",
        "feature_type",
        "primary_value",
        "geometry",
        "source_region",
        "load_date",
    ]
    return gdf[columns].set_geometry("geometry")


def save_parquet(gdf: gpd.GeoDataFrame, region: str, preset: FeaturePreset) -> Path:
    """
    Persist extracted features to parquet for optional offline inspection.
    """
    frame = gdf.copy()
    if not frame.empty:
        frame["geometry"] = frame.geometry.to_wkb()
    else:
        # Ensure parquet schema keeps the expected columns on empty writes.
        frame["geometry"] = frame.geometry.astype("object")

    out = DATA_PATH / parquet_name(preset.key, region)
    frame.to_parquet(out, index=False)
    return out
