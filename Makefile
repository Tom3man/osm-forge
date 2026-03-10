.PHONY: install run serve query list-regions clean clean-db clean-pbf

# ── Setup ─────────────────────────────────────────────────────────────────────

install:
	poetry install

# ── Data pipeline ─────────────────────────────────────────────────────────────

## Download + ingest regions (uses DEFAULT_REGIONS when --region is omitted).
## REGION can be a group name (midlands, west-midlands, east-midlands, greater-london)
## or a full Geofabrik path: make run REGION=europe/united-kingdom/england/greater-manchester
run:
ifdef REGION
	poetry run osmforge run --region $(REGION) $(if $(PRESET),--preset $(PRESET),)
else
	poetry run osmforge run $(if $(PRESET),--preset $(PRESET),)
endif

# ── Query / inspect ───────────────────────────────────────────────────────────

list-regions:
	poetry run osmforge list-regions $(if $(PRESET),--preset $(PRESET),)

## Preview rows. Override with: make query REGION=... PRESET=buildings LIMIT=10
query:
	poetry run osmforge query \
		$(if $(REGION),--region $(REGION),) \
		$(if $(PRESET),--preset $(PRESET),) \
		$(if $(LIMIT),--limit $(LIMIT),)

# ── API server ────────────────────────────────────────────────────────────────

## Start API on 127.0.0.1:8000. Override with: make serve HOST=0.0.0.0 PORT=9000
serve:
	poetry run osmforge serve \
		--host $(or $(HOST),127.0.0.1) \
		--port $(or $(PORT),8000)

# ── Cleanup ───────────────────────────────────────────────────────────────────

clean: clean-db clean-pbf

clean-db:
	rm -f data/osm_local.duckdb

clean-pbf:
	rm -f data/*.osm.pbf

clean-parquet:
	rm -f data/*.parquet
