#!/bin/bash

mkdir -p data

curl 'https://data.sfgov.org/api/geospatial/xvjh-uu28?method=export&format=GeoJSON' > data/zoning.geojson
curl 'https://data.sfgov.org/api/geospatial/iddb-5nzh?method=export&format=GeoJSON' > data/height.geojson
curl 'https://data.sfgov.org/api/geospatial/us3s-fp9q?method=export&format=GeoJSON' > data/lots.geojson
curl 'https://data.sfgov.org/api/geospatial/ynuv-fyni?method=export&format=GeoJSON' > data/buildings.geojson
curl 'https://data.sfgov.org/api/geospatial/vzu4-cjy3?method=export&format=GeoJSON' > data/historic.geojson
curl 'https://data.sfgov.org/api/geospatial/7pzz-zhis?method=export&format=GeoJSON' > data/historic_state.geojson
curl 'https://data.sfgov.org/api/geospatial/65x7-fi3w?method=export&format=GeoJSON' > data/historic_national.geojson
curl 'https://data.sfgov.org/api/geospatial/vnrd-fpg7?method=export&format=GeoJSON' > data/historic_local.geojson
curl 'https://data.sfgov.org/api/geospatial/ejy7-efgv?method=export&format=GeoJSON' > data/historic_local_landmarks.geojson
curl 'https://data.sfgov.org/api/geospatial/8nkz-x4ny?method=export&format=GeoJSON' > data/supervisors.geojson
