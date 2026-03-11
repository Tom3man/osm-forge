"""Smoke tests — verify the package imports cleanly."""
import osmforge


def test_import():
    assert osmforge is not None
