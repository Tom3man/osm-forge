# Python Client

The `OSMClient` class is the main interface for querying your local OSM stack.
It returns results as [GeoPandas](https://geopandas.org/) `GeoDataFrame` objects in **EPSG:4326**.

## Setup

```python
from osmforge import OSMClient

# Default — connects to http://localhost:8000
client = OSMClient()

# Custom host / port
client = OSMClient(base_url="http://192.168.1.10:8000")
```

---

## Bounding-box queries

### Propagation features — `propagation_bbox`

Returns features classified into propagation layers within a lat/lon bounding box.

```python
gdf = client.propagation_bbox(
    min_lon=-1.6, min_lat=50.55,
    max_lon=-1.0, max_lat=50.85,
)
print(gdf.columns.tolist())
# ['geometry', 'layer', 'osm_id', ...]
print(gdf["layer"].value_counts())
```

**Filter to specific layers:**

```python
gdf = client.propagation_bbox(
    min_lon=-1.6, min_lat=50.55,
    max_lon=-1.0, max_lat=50.85,
    layers=["buildings", "vegetation"],
)
```

**Cap the number of features returned:**

```python
gdf = client.propagation_bbox(
    min_lon=-0.13, min_lat=51.49,
    max_lon=-0.11, max_lat=51.51,
    limit=500,
)
```

### Raw OSM features — `features_bbox`

Returns all OSM tags without propagation classification. Useful for exploration.

```python
gdf = client.features_bbox(
    min_lon=-0.13, min_lat=51.49,
    max_lon=-0.11, max_lat=51.51,
)
# All raw OSM tag columns are present
print(gdf.columns.tolist())
```

---

## Geometry queries

### Propagation features — `propagation_geometry`

Accepts a **Shapely geometry** or a **GeoJSON dict** (Polygon or MultiPolygon).

**With a Shapely polygon:**

```python
from shapely.geometry import box

aoi = box(-1.6, 50.55, -1.0, 50.85)  # (min_lon, min_lat, max_lon, max_lat)

gdf = client.propagation_geometry(aoi)
print(len(gdf), "features")
```

**With a GeoJSON dict:**

```python
geojson_polygon = {
    "type": "Polygon",
    "coordinates": [[
        [-1.6, 50.55],
        [-1.0, 50.55],
        [-1.0, 50.85],
        [-1.6, 50.85],
        [-1.6, 50.55],
    ]],
}

gdf = client.propagation_geometry(geojson_polygon)
```

**Filter layers and cap results:**

```python
gdf = client.propagation_geometry(
    aoi,
    layers=["buildings", "roads", "water"],
    limit=1000,
)
```

---

## Working with results

Results are standard `GeoDataFrame` objects — use any GeoPandas or Shapely operation:

```python
import geopandas as gpd

gdf = client.propagation_bbox(
    min_lon=-1.6, min_lat=50.55,
    max_lon=-1.0, max_lat=50.85,
)

# Filter to buildings only
buildings = gdf[gdf["layer"] == "buildings"]

# Reproject for metric calculations (e.g. area in m²)
buildings_bng = buildings.to_crs("EPSG:27700")
buildings_bng["area_m2"] = buildings_bng.geometry.area

# Save to file
gdf.to_file("isle_of_wight.gpkg", driver="GPKG")

# Plot
gdf.plot(column="layer", legend=True, figsize=(12, 8))
```

---

## API Reference

::: osmforge.client.OSMClient
