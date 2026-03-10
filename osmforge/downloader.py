import hashlib
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter, Retry

from .config import BASE_URL, DATA_PATH

_session = requests.Session()
_session.mount("https://", HTTPAdapter(
    max_retries=Retry(total=5, backoff_factor=0.6,
                      status_forcelist=[429, 500, 502, 503, 504])
))


def md5_file(path: Path, chunk: int = 1024 * 1024) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def download_region(region: str) -> Path:
    """
    Download .pbf file for a region (resumable).

    ``region`` is a Geofabrik path such as
    ``europe/united-kingdom/england/greater-london``.
    The local filename is derived from the leaf component only.
    """
    leaf = region.split("/")[-1]
    fname = f"{leaf}-latest.osm.pbf"
    url = f"{BASE_URL}/{region}-latest.osm.pbf"
    dest = DATA_PATH / fname
    resume_pos = dest.stat().st_size if dest.exists() else 0
    headers = {"Range": f"bytes={resume_pos}-"} if resume_pos else {}
    mode = "ab" if resume_pos else "wb"

    with _session.get(url, stream=True, headers=headers, timeout=60) as r:
        r.raise_for_status()
        with open(dest, mode) as f:
            for chunk in r.iter_content(1024 * 1024):
                if chunk:
                    f.write(chunk)
    return dest
