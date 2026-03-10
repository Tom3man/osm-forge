local tables = {}

tables.points = osm2pgsql.define_node_table('osm_points', {
    { column = 'osm_id', type = 'bigint' },
    { column = 'name', type = 'text' },
    { column = 'tags', type = 'jsonb' },
    { column = 'geom', type = 'point', projection = 4326 },
})

tables.lines = osm2pgsql.define_way_table('osm_lines', {
    { column = 'osm_id', type = 'bigint' },
    { column = 'name', type = 'text' },
    { column = 'highway', type = 'text' },
    { column = 'railway', type = 'text' },
    { column = 'tags', type = 'jsonb' },
    { column = 'geom', type = 'linestring', projection = 4326 },
})

tables.polygons = osm2pgsql.define_area_table('osm_polygons', {
    { column = 'osm_id', type = 'bigint' },
    { column = 'name', type = 'text' },
    { column = 'amenity', type = 'text' },
    { column = 'building', type = 'text' },
    { column = 'landuse', type = 'text' },
    { column = 'leisure', type = 'text' },
    { column = 'tags', type = 'jsonb' },
    { column = 'geom', type = 'multipolygon', projection = 4326 },
})

function osm2pgsql.process_node(object)
    tables.points:insert({
        osm_id = object.id,
        name = object.tags.name,
        tags = object.tags,
        geom = object:as_point()
    })
end

function osm2pgsql.process_way(object)
    local t = object.tags
    local is_polygon_feature = object.is_closed and (
        t.building or
        t.landuse or
        t.leisure or
        t.amenity or
        t['natural'] or   -- water, wood, scrub, heath, grassland, etc.
        t.man_made or     -- bridge, embankment, cutting
        t.waterway        -- riverbank polygons
    )

    if is_polygon_feature then
        tables.polygons:insert({
            osm_id  = object.id,
            name    = t.name,
            amenity = t.amenity,
            building = t.building,
            landuse = t.landuse,
            leisure = t.leisure,
            tags    = t,
            geom    = object:as_polygon(),
        })
    else
        tables.lines:insert({
            osm_id  = object.id,
            name    = t.name,
            highway = t.highway,
            railway = t.railway,
            tags    = t,
            geom    = object:as_linestring(),
        })
    end
end

function osm2pgsql.process_relation(object)
    -- keep v1 simple; relations can come later
end