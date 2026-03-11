# Download

OSMForge downloads PBF extracts from [Geofabrik](https://download.geofabrik.de).
Region paths mirror the Geofabrik URL structure.

## CLI

The `osmforge-download` command is installed automatically with the package.

```bash
# Single region
osmforge-download europe/united-kingdom/england/isle-of-wight

# Multiple regions in one call
osmforge-download \
    europe/united-kingdom/england/greater-london \
    europe/united-kingdom/england/west-midlands

# Force re-download (overwrite existing file)
osmforge-download --force europe/united-kingdom/england/isle-of-wight
```

Files are saved to the OS user-data directory by default:

| OS | Default path |
|---|---|
| Linux | `~/.local/share/osmforge/` |
| macOS | `~/Library/Application Support/osmforge/` |
| Windows | `%LOCALAPPDATA%\osmforge\` |

Override the destination with an environment variable:

```bash
export OSMFORGE_DATA_DIR=/data/osm
osmforge-download europe/united-kingdom/england/isle-of-wight
```

---

## Example region paths

```
europe/united-kingdom/england/isle-of-wight
europe/united-kingdom/england/greater-london
europe/united-kingdom/england/west-midlands
europe/united-kingdom/scotland
europe/germany/berlin
north-america/us/california
```

Full index: <https://download.geofabrik.de/>

---

## Python API

You can also call the download functions directly from Python:

```python
from osmforge.download import download, get_data_dir

# Show where files will be saved
print(get_data_dir())
# /home/user/.local/share/osmforge

# Download a region (skips if already present)
path = download("europe/united-kingdom/england/isle-of-wight")
print(path)
# /home/user/.local/share/osmforge/isle-of-wight-latest.osm.pbf

# Force re-download
path = download("europe/united-kingdom/england/isle-of-wight", force=True)
```

---

## API Reference

::: osmforge.download
    options:
      members:
        - get_data_dir
        - download
