import click
import geopandas as gpd

from .config import DEFAULT_PRESET, DEFAULT_REGIONS, FEATURE_PRESETS, REGION_GROUPS
from .db import ingest_parquet, init_db, list_regions, query_features
from .downloader import download_region
from .parser import extract_features, save_parquet


@click.group()
def cli() -> None:
    """OSMForge command line interface."""


@cli.command()
@click.option(
    "--region",
    "regions",
    multiple=True,
    help=(
        "Geofabrik path or group name to process. "
        f"Groups: {', '.join(sorted(REGION_GROUPS))}. "
        "Repeat to pass multiple values."
    ),
)
@click.option(
    "--preset",
    type=click.Choice(sorted(FEATURE_PRESETS.keys())),
    default=DEFAULT_PRESET,
    show_default=True,
    help="Feature preset to load.",
)
def run(regions, preset):
    """Download + parse selected regions for the chosen preset."""
    preset_cfg = FEATURE_PRESETS[preset]

    # Expand any group names into their constituent paths.
    resolved: list[str] = []
    for r in regions or DEFAULT_REGIONS:
        resolved.extend(REGION_GROUPS.get(r, [r]))

    init_db()
    for region in resolved:
        click.echo(f"↳ {preset_cfg.title} • {region}")
        pbf = download_region(region)
        gdf = extract_features(pbf, preset_cfg, source_region=region)
        pq = save_parquet(gdf, region, preset_cfg)
        ingest_parquet(pq, preset_cfg.key, region)
        click.echo(f"✅ {region} done ({len(gdf)} features)")


@cli.command("list-regions")
@click.option(
    "--preset",
    type=click.Choice(sorted(FEATURE_PRESETS.keys())),
    default=DEFAULT_PRESET,
    show_default=True,
    help="Feature preset to inspect.",
)
def list_regions_cmd(preset):
    """List regions that have already been ingested."""
    preset_cfg = FEATURE_PRESETS[preset]
    regions = list_regions(preset_cfg.key)
    if not regions:
        click.echo("No regions loaded yet.")
        return
    for region in regions:
        click.echo(region)


@cli.command()
@click.option("--region", help="Filter results to a specific region.")
@click.option(
    "--preset",
    type=click.Choice(sorted(FEATURE_PRESETS.keys())),
    default=DEFAULT_PRESET,
    show_default=True,
    help="Feature preset to query.",
)
@click.option("--limit", type=int, default=5, show_default=True, help="Preview row count.")
def query(region, preset, limit):
    """
    Preview feature rows from the local database.
    """

    preset_cfg = FEATURE_PRESETS[preset]
    df = query_features(preset_cfg.key, region=region, limit=limit)
    if df.empty:
        click.echo("No rows match your query.")
        return

    gdf = gpd.GeoDataFrame(
        df.drop(columns=["geometry_wkb"]),
        geometry=gpd.GeoSeries.from_wkb(df["geometry_wkb"], crs="EPSG:4326"),
    )
    click.echo(gdf)


@cli.command()
@click.option("--host", default="127.0.0.1", show_default=True, help="Bind address.")
@click.option("--port", default=8000, show_default=True, help="Port to listen on.")
def serve(host, port):
    """Start the OSMForge GeoJSON API server."""
    import uvicorn
    uvicorn.run("osmforge.api:app", host=host, port=port)


if __name__ == "__main__":
    cli()
