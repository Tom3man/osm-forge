from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

BASE_URL = "https://download.geofabrik.de"
DATA_PATH = Path(__file__).resolve().parent.parent / "data"
DATA_PATH.mkdir(parents=True, exist_ok=True)

_ENG = "europe/united-kingdom/england"

# Named region groups — pass any of these to `osmforge run --region <name>`
# or reference them directly in your own scripts.
REGION_GROUPS: Dict[str, List[str]] = {
    "greater-london": [
        f"{_ENG}/greater-london",
    ],
    "west-midlands": [
        f"{_ENG}/west-midlands",       # Birmingham, Coventry, Wolverhampton metro
        f"{_ENG}/staffordshire",
        f"{_ENG}/warwickshire",
        f"{_ENG}/worcestershire",
        f"{_ENG}/herefordshire",
        f"{_ENG}/shropshire",
    ],
    "east-midlands": [
        f"{_ENG}/derbyshire",
        f"{_ENG}/nottinghamshire",
        f"{_ENG}/leicestershire",
        f"{_ENG}/lincolnshire",
        f"{_ENG}/northamptonshire",
        f"{_ENG}/rutland",
    ],
    "midlands": [],  # populated below
}
REGION_GROUPS["midlands"] = (
    REGION_GROUPS["west-midlands"] + REGION_GROUPS["east-midlands"]
)

# Full Geofabrik paths, e.g. "europe/united-kingdom/england/greater-london"
DEFAULT_REGIONS = REGION_GROUPS["greater-london"]


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
