# OSMForge

A self-hosted OpenStreetMap stack that downloads regional OSM extracts, ingests
them into a local PostGIS database, and serves a GeoJSON API optimised for
spatial analysis — particularly **radio-frequency propagation modelling**.

Public OSM APIs (Overpass, Nominatim) have strict rate limits and aren't suited
to bulk or repeated spatial queries. OSMForge gives you unlimited local access
to the same data.

---

## Installation

```bash
pip install osmforge
```

---

## Architecture

```
Geofabrik  ──download──▶  *.osm.pbf
                               │
                          osm2pgsql
                               │
                          PostGIS DB
                               │
                          FastAPI  ◀──  OSMClient (Python)
```

---

## Quick start

### 1 — Download a region

```bash
osmforge-download europe/united-kingdom/england/isle-of-wight
```

Or download multiple regions in one call:

```bash
osmforge-download \
    europe/united-kingdom/england/west-midlands \
    europe/united-kingdom/england/staffordshire
```

Re-download (overwrite existing file):

```bash
osmforge-download --force europe/united-kingdom/england/isle-of-wight
```

### 2 — Start the stack

```bash
make up
```

### 3 — Query with the Python client

```python
from osmforge import OSMClient

client = OSMClient()  # defaults to http://localhost:8000

# All propagation-classified features in a bounding box
gdf = client.propagation_bbox(
    min_lon=-1.6, min_lat=50.55,
    max_lon=-1.0, max_lat=50.85,
)
print(gdf.head())
```

---

## Available data layers

| Layer | Description |
|---|---|
| `buildings` | All building footprints |
| `roads` | Highways, paths, tracks |
| `water` | Rivers, lakes, sea areas |
| `vegetation` | Woods, forests, scrub |
| `landuse` | Farmland, industrial, residential |
| `structures` | Bridges, walls, barriers |
| `terrain` | Cliffs, embankments, peaks |

```python
from osmforge import ALL_LAYERS
print(ALL_LAYERS)
# ['buildings', 'roads', 'water', 'vegetation', 'landuse', 'structures', 'terrain']
```
