from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

import duckdb
from duckdb import DuckDBPyConnection

from .config import DUCKDB_PATH


def connect(load_spatial: bool = True) -> DuckDBPyConnection:
    """
    Helper to open a DuckDB connection with the spatial extension loaded.
    """
    con = duckdb.connect(DUCKDB_PATH)
    if load_spatial:
        con.execute("INSTALL spatial;")
        con.execute("LOAD spatial;")
    return con


def init_db() -> None:
    con = connect()
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS features (
            feature_type VARCHAR,
            osm_id BIGINT,
            primary_value VARCHAR,
            geometry GEOMETRY,
            source_region VARCHAR,
            load_date TIMESTAMP
        );
        """
    )
    con.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_features_type_region
        ON features (feature_type, source_region);
        """
    )
    con.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_features_geom
        ON features USING RTREE (geometry);
        """
    )
    con.close()


def ingest_parquet(parquet_path: Path, feature_type: str, region: str) -> None:
    """
    Insert parquet rows into the main features table, replacing prior loads.
    """
    con = connect()
    con.execute(
        "DELETE FROM features WHERE feature_type = ? AND source_region = ?",
        [feature_type, region],
    )
    con.execute(
        """
        INSERT INTO features
        SELECT
            feature_type,
            osm_id,
            primary_value,
            ST_GeomFromWKB(geometry) AS geometry,
            source_region,
            load_date
        FROM read_parquet(?)
        """,
        [str(parquet_path)],
    )
    con.close()


def query_features(
    feature_type: str,
    region: Optional[str] = None,
    limit: Optional[int] = None,
    bbox: Optional[Tuple[float, float, float, float]] = None,
) -> "DataFrame":
    """
    Fetch features matching the supplied filters as a pandas DataFrame.
    """
    from pandas import DataFrame  # noqa: F401 — used in return type string

    con = connect()
    clauses = ["feature_type = ?"]
    params: list[object] = [feature_type]

    if region:
        clauses.append("source_region = ?")
        params.append(region)

    if bbox:
        west, south, east, north = bbox
        clauses.append(
            "ST_Intersects(geometry, ST_MakeEnvelope(?, ?, ?, ?, 4326))"
        )
        params.extend([west, south, east, north])

    sql = f"""
        SELECT
            osm_id,
            feature_type,
            primary_value,
            ST_AsWKB(geometry) AS geometry_wkb,
            source_region,
            load_date
        FROM features
        WHERE {' AND '.join(clauses)}
    """
    if limit:
        sql += " LIMIT ?"
        params.append(limit)

    df = con.execute(sql, params).df()
    con.close()
    return df


def list_regions(feature_type: str) -> List[str]:
    """
    Return the list of regions with data for the given feature type.
    """
    con = connect(load_spatial=False)
    rows = con.execute(
        "SELECT DISTINCT source_region FROM features "
        "WHERE feature_type = ? ORDER BY 1",
        [feature_type],
    ).fetchall()
    con.close()
    return [row[0] for row in rows]
