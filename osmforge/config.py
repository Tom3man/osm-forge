from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple

BASE_URL = "https://download.geofabrik.de/europe/united-kingdom/england"
DATA_PATH = Path(__file__).resolve().parent.parent / "data"
DATA_PATH.mkdir(parents=True, exist_ok=True)

DEFAULT_REGIONS = [
    "greater-london", "lancashire", "greater-manchester",
    "merseyside", "devon", "cornwall"
]


@dataclass(frozen=True)
class FeaturePreset:
    """
    Describe a reusable OSM feature extraction preset.
    """
    key: str
    title: str
    custom_filter: Dict[str, object]
    geometry_types: Tuple[str, ...]
    primary_tag: str


FEATURE_PRESETS: Dict[str, FeaturePreset] = {
    "buildings": FeaturePreset(
        key="buildings",
        title="Building Footprints",
        custom_filter={"building": True},
        geometry_types=("Polygon", "MultiPolygon"),
        primary_tag="building",
    ),
}

DEFAULT_PRESET = "buildings"

# Defaults for local DB
DUCKDB_PATH = DATA_PATH / "osm_local.duckdb"


def parquet_name(preset: str, region: str) -> str:
    """
    Normalised parquet filename for a preset/region pair.
    """
    return f"{preset}_{region}.parquet"
