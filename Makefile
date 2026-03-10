PBF        ?= osmforge/data/isle-of-wight.osm.pbf
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

.PHONY: up down ingest layers rebuild clean help

## Start PostGIS + API containers
up:
	docker compose -f osmforge/docker-compose.yaml up -d

## Stop and remove containers (keeps the data volume)
down:
	docker compose -f osmforge/docker-compose.yaml down

## Load PBF into osm.* raw tables via osm2pgsql
## Override the file: make ingest PBF=osmforge/data/greater-london-latest.osm.pbf
ingest:
	$(OSM2PGSQL) $(PBF)

## Build app.* derived layers from osm.* raw tables
layers:
	$(PSQL) -f $(LAYERS_SQL)

## Full pipeline: ingest + build layers
rebuild: ingest layers

## Destroy containers AND the data volume (full reset)
clean:
	docker compose -f osmforge/docker-compose.yaml down -v

## Show available targets
help:
	@grep -E '^##' Makefile | sed 's/## //'
