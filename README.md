# OSMForge

A self-hosted OpenStreetMap stack that downloads regional OSM extracts, ingests
them into a local PostGIS database, and serves a GeoJSON API optimised for
spatial analysis — particularly **radio-frequency propagation modelling**.

Public OSM APIs (Overpass, Nominatim) have strict rate limits and aren't suited
to bulk or repeated spatial queries. OSMForge gives you unlimited local access
to the same data.

---

## Contents

- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick start](#quick-start)
- [Adding regions](#adding-regions)
- [Makefile reference](#makefile-reference)
- [API reference](#api-reference)
- [Python client](#python-client)
- [Data layers](#data-layers)

---

## Architecture

```
Geofabrik  ──download──▶  *.osm.pbf
                               │
                          osm2pgsql (Lua flex)
                               │
                        osm schema (raw)
                    osm_points / osm_lines / osm_polygons
                               │
                          make layers  (SQL)
                               │
                         app schema (classified)
              osm_buildings / osm_roads / osm_water /
              osm_vegetation / osm_landuse /
              osm_structures / osm_terrain
                               │
                          FastAPI  :8000
                               │
                        osmforge.client
```

The `osm` schema holds raw data exactly as loaded by osm2pgsql.
The `app` schema holds pre-classified, indexed tables ready for querying.

---

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Docker + Compose v2 | latest | `docker compose version` |
| osm2pgsql | ≥ 1.9 | `osm2pgsql --version` |
| Python | ≥ 3.12 | |
| Poetry | ≥ 1.8 | `pip install poetry` |

Install Python dependencies:

```bash
poetry install
```

---

## Quick start

### 1 — Start the database

```bash
make up
```

This starts a PostGIS 17 container on `localhost:5432` and the FastAPI container
on `localhost:8000`. On first run Docker will pull the images.

### 2 — Download an OSM extract

Extracts come from [Geofabrik](https://download.geofabrik.de). Pass the full
path from the Geofabrik URL:

```bash
make download REGION=europe/united-kingdom/england/isle-of-wight
```

The file lands in `osmforge/data/` and is skipped on subsequent runs unless you
pass `FORCE=--force`.

### 3 — Ingest + build layers

```bash
make ingest    # load every *.osm.pbf in osmforge/data/ into osm.*
make layers    # build classified app.* tables
```

Or in one step:

```bash
make rebuild
```

### 4 — Query the API

```bash
curl "http://localhost:8000/propagation/bbox?min_lon=-1.35&min_lat=50.65&max_lon=-1.1&max_lat=50.78"
```

---

## Adding regions

Download as many regions as you like before ingesting — `make ingest` loads
everything in `osmforge/data/` in a single pass.

```bash
# individual counties
make download REGION=europe/united-kingdom/england/west-midlands
make download REGION=europe/united-kingdom/england/staffordshire
make download REGION=europe/united-kingdom/england/warwickshire

# then ingest them all together
make rebuild
```

To see what Geofabrik has available, browse:
- England: https://download.geofabrik.de/europe/united-kingdom/england.html
- Full index: https://download.geofabrik.de

---

## Makefile reference

| Command | Description |
|---|---|
| `make up` | Start PostGIS + API containers |
| `make down` | Stop containers (data volume preserved) |
| `make download REGION=<path>` | Download a PBF from Geofabrik |
| `make ingest` | Load all PBFs in `osmforge/data/` via osm2pgsql |
| `make layers` | Build `app.*` tables from raw `osm.*` data |
| `make rebuild` | `ingest` + `layers` in one step |
| `make rebuild-api` | Rebuild the API Docker image after code changes |
| `make clean` | Destroy containers **and** data volume (full reset) |
| `make interface` | Open a psql shell to the database |
| `make help` | List all targets |

---

## API reference

The API runs at `http://localhost:8000`. Interactive docs at
`http://localhost:8000/docs`.

---

### `GET /health`

```
200 {"status": "ok"}
```

---

### `GET /propagation/bbox`

Return classified OSM features within a bounding box.

**Query parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `min_lon` | float | ✓ | West edge (WGS-84) |
| `min_lat` | float | ✓ | South edge |
| `max_lon` | float | ✓ | East edge |
| `max_lat` | float | ✓ | North edge |
| `layers` | string (repeat) | | Subset of layers (default: all) |
| `limit` | int | | Max features returned |

**Example**

```
GET /propagation/bbox?min_lon=-1.35&min_lat=50.65&max_lon=-1.1&max_lat=50.78&layers=buildings&layers=terrain
```

**Response** — GeoJSON FeatureCollection. Each feature's `properties`:

```json
{
  "osm_id": 123456,
  "name": "St Mary's Church",
  "layer": "buildings",
  "feature_class": "church",
  "height_m": 18.0,
  "levels": "3",
  "material": "stone"
}
```

---

### `POST /propagation/geometry`

Return classified OSM features intersecting an arbitrary polygon or
multipolygon. Useful when you already have a coverage or study-area polygon.

**Request body**

```json
{
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[<lon>, <lat>], ...]]
  },
  "layers": ["buildings", "vegetation", "terrain"],
  "limit": 5000
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `geometry` | GeoJSON geometry | ✓ | Polygon or MultiPolygon, WGS-84 |
| `layers` | array of strings | | Subset of layers (default: all) |
| `limit` | int | | Max features returned |

---

### `GET /features/bbox`

Return **raw** OSM features (all tags) within a bounding box. Useful for
exploration; use `/propagation/bbox` for modelling workflows.

**Query parameters** — same bbox params as above, plus optional `limit`.

---

## Python client

Install the package then import the client:

```python
from osmforge.client import OSMClient

client = OSMClient()  # default: http://localhost:8000
# or: OSMClient("http://my-server:8000")
```

All methods return a `geopandas.GeoDataFrame` (CRS EPSG:4326).

---

### `client.propagation_bbox`

```python
gdf = client.propagation_bbox(
    min_lon=-1.35,
    min_lat=50.65,
    max_lon=-1.1,
    max_lat=50.78,
)
```

Filter to specific layers:

```python
gdf = client.propagation_bbox(
    min_lon=-1.35, min_lat=50.65,
    max_lon=-1.1,  max_lat=50.78,
    layers=["buildings", "terrain"],
    limit=10000,
)
```

---

### `client.propagation_geometry`

Accepts a GeoJSON dict **or** a Shapely geometry:

```python
from shapely.geometry import Polygon

area = Polygon([
    (-1.35, 50.65), (-1.1, 50.65),
    (-1.1, 50.78),  (-1.35, 50.78),
    (-1.35, 50.65),
])

gdf = client.propagation_geometry(area)

# with options
gdf = client.propagation_geometry(
    area,
    layers=["buildings", "vegetation", "terrain"],
    limit=50000,
)
```

---

### `client.features_bbox`

```python
gdf = client.features_bbox(
    min_lon=-1.35,
    min_lat=50.65,
    max_lon=-1.1,
    max_lat=50.78,
)
# gdf.columns → geometry, osm_id, name, source_layer, tags
```

---

## Data layers

| Layer | Source OSM tags | Key properties |
|---|---|---|
| `buildings` | `building=*` | `building_type`, `height_m`, `levels`, `material` |
| `roads` | `highway=*`, `railway=*` | `transport_class` (major / secondary / local / rail / …) |
| `water` | `natural=water`, `waterway=*`, `landuse=reservoir` | `water_class` |
| `vegetation` | `landuse=forest`, `natural=wood/scrub/heath/grassland`, `leisure=park` | `vegetation_class` |
| `landuse` | `landuse=*` | `landuse_class` (residential / industrial / agricultural / …) |
| `structures` | `man_made=mast/tower`, `power=tower/line`, bridges, embankments | `structure_class` |
| `terrain` | `natural=cliff/ridge/coastline/peak/saddle`, barriers, chimneys | `terrain_class`, `height_m` |

### Height estimation

`height_m` on buildings is derived from OSM tags in order of preference:

1. `height=*` (metres, if numeric)
2. `building:levels=*` × 3 m per floor
3. `NULL` if neither is tagged

### Terrain classes

| `terrain_class` | Geometry | Propagation relevance |
|---|---|---|
| `cliff` | line | Hard diffraction edge |
| `ridge` | line | Diffraction / shadowing |
| `coastline` | line | Land/sea boundary — sea has near-zero attenuation |
| `barrier_wall` | line | Urban canyon obstruction |
| `embankment` / `cutting` | line | Signal blocking |
| `peak` / `saddle` | point | Elevation proxy |
| `chimney` / `storage_tank` | point | Tall point obstacles |
| `communications_tower` | point | Co-channel interference sources |
