# Resolve data directory: OSMFORGE_DATA_DIR env var, or OS user-data dir via platformdirs
DATA_DIR   := $(shell python3 -c \
  "import os,platformdirs; \
   print(os.environ.get('OSMFORGE_DATA_DIR') or platformdirs.user_data_dir('osmforge'))")

LUA        := osmforge/osm2pgsql/osm.lua
LAYERS_SQL := osmforge/db/layers.sql

DB_HOST    := localhost
DB_PORT    := 5432
DB_NAME    := osm
DB_USER    := osm
PSQL       := PGPASSWORD=osm psql -h $(DB_HOST) -p $(DB_PORT) -U $(DB_USER) -d $(DB_NAME)
OSM2PGSQL  := PGPASSWORD=osm osm2pgsql \
                --create \
                --output=flex \
                --style=$(LUA) \
                --schema=osm \
                -H $(DB_HOST) -P $(DB_PORT) -d $(DB_NAME) -U $(DB_USER)

REGION     ?= isle-of-wight

.PHONY: up down download ingest layers rebuild clean rebuild-api interface help

## Download PBF file(s) from Geofabrik (sequential, skips existing files).
## REGION must be a full Geofabrik path. Separate multiple with spaces.
## Examples: make download REGION=europe/united-kingdom/england/isle-of-wight
##           make download REGION="europe/united-kingdom/england/west-midlands europe/united-kingdom/england/staffordshire"
## Add --force to re-download: make download REGION=... FORCE=--force
download:
	python3 osmforge/download.py $(REGION) $(FORCE)

## Start PostGIS + API containers
up:
	docker compose -f osmforge/docker-compose.yaml up -d

## Stop and remove containers (keeps the data volume)
down:
	docker compose -f osmforge/docker-compose.yaml down

## Load all PBFs in DATA_DIR into osm.* raw tables via osm2pgsql
ingest:
	$(OSM2PGSQL) $(DATA_DIR)/*.osm.pbf

## Build app.* derived layers from osm.* raw tables
layers:
	$(PSQL) -f $(LAYERS_SQL)

## Full pipeline: ingest + build layers
rebuild: ingest layers

## Destroy containers AND the data volume (full reset)
clean:
	docker compose -f osmforge/docker-compose.yaml down -v

## Destroy containers AND the data volume (full reset), then rebuild the API container (useful if you change the API code)
rebuild-api:
	docker compose -f osmforge/docker-compose.yaml up -d --build api

## Allows a user to connect to the database via psql (useful for debugging)
interface:
	psql postgresql://osm:osm@localhost:5432/osm

## Show available targets
help:
	@grep -E '^##' Makefile | sed 's/## //'
