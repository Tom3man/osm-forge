# OSMForge

A self-hosted OpenStreetMap stack that downloads regional OSM extracts, ingests
them into a local PostGIS database, and serves a GeoJSON API optimised for
spatial analysis — particularly **radio-frequency propagation modelling**.

Public OSM APIs (Overpass, Nominatim) have strict rate limits and aren't suited
to bulk or repeated spatial queries. OSMForge gives you unlimited local access
to the same data.

## Installation

```bash
pip install osmforge
```

## Quick Start

```python
from osmforge import OsmForgeClient

client = OsmForgeClient(base_url="http://localhost:8000")
buildings = client.get_buildings(lat=51.5, lon=-0.12, radius_m=500)
```

## Links

- [GitHub Repository](https://github.com/Tom3man/osm-forge)
- [PyPI Package](https://pypi.org/project/osmforge/)
