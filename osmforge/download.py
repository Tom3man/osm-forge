#!/usr/bin/env python3
"""
Download OSM PBF extracts from Geofabrik.

Usage:
    python3 osmforge/download.py <region-path> [region-path ...]
    python3 osmforge/download.py --force <region-path>

Examples:
    python3 osmforge/download.py europe/united-kingdom/england/isle-of-wight
    python3 osmforge/download.py europe/united-kingdom/england/greater-london
    python3 osmforge/download.py europe/united-kingdom/england/west-midlands \
                                  europe/united-kingdom/england/staffordshire

Or via make:
    make download REGION=europe/united-kingdom/england/isle-of-wight
    make download REGION="europe/united-kingdom/england/west-midlands europe/united-kingdom/england/staffordshire"
"""

import os
import sys
import time
from pathlib import Path

import requests
from platformdirs import user_data_dir

BASE_URL = "https://download.geofabrik.de"
INTER_FILE_DELAY = 2  # seconds between downloads


def get_data_dir() -> Path:
    """
    Resolve the directory where PBF files are stored.

    Priority:
      1. OSMFORGE_DATA_DIR environment variable
      2. OS user-data directory (~/.local/share/osmforge on Linux,
         ~/Library/Application Support/osmforge on macOS, etc.)
    """
    env = os.environ.get("OSMFORGE_DATA_DIR")
    path = Path(env) if env else Path(user_data_dir("osmforge"))
    path.mkdir(parents=True, exist_ok=True)
    return path


def dest_path(region_path: str, data_dir: Path) -> Path:
    leaf = region_path.rstrip("/").split("/")[-1]
    return data_dir / f"{leaf}-latest.osm.pbf"


def download(region_path: str, force: bool = False) -> Path:
    data_dir = get_data_dir()
    url = f"{BASE_URL}/{region_path}-latest.osm.pbf"
    dest = dest_path(region_path, data_dir)

    if dest.exists() and not force:
        size_mb = dest.stat().st_size / 1_048_576
        print(f"  [skip] {dest.name} already exists ({size_mb:.1f} MB)")
        return dest

    print(f"  -> {url}")
    print(f"  saving to {dest}")

    tmp = dest.with_suffix(".part")
    try:
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            downloaded = 0
            with tmp.open("wb") as f:
                for chunk in r.iter_content(chunk_size=1 << 20):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = downloaded / total * 100
                        mb = downloaded / 1_048_576
                        print(
                            f"\r    {mb:6.1f} / {total/1_048_576:.1f} MB"
                            f"  ({pct:.0f}%)",
                            end="",
                            flush=True,
                        )
        print()
        tmp.rename(dest)
        print(f"  saved -> {dest.name}")
    except Exception:
        tmp.unlink(missing_ok=True)
        raise

    return dest


def main() -> None:
    args = sys.argv[1:]
    force = "--force" in args
    regions = [a for a in args if not a.startswith("--")]

    if not regions:
        print(__doc__)
        sys.exit(1)

    print(f"Queued {len(regions)} region(s):\n")
    for i, region in enumerate(regions):
        print(f"[{i + 1}/{len(regions)}] {region}")
        download(region, force=force)
        if i < len(regions) - 1:
            time.sleep(INTER_FILE_DELAY)

    print("\nDone.")


if __name__ == "__main__":
    main()
