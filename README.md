# Terra Atlas v0.4 — Global river-network foundation

This package preserves the v0.3 globe and terrain explorer and introduces a multiscale hydrology workflow.

## What's new
- Global overview using the existing Natural Earth river centerlines.
- Optional regional HydroRIVERS reach detail.
- Optional HydroBASINS watershed polygons.
- Reach attribute inspection, including identifiers, stream order, reach length, discharge estimates, catchment area and network distances where supplied.
- Spatial bounding-box reads from a GeoPackage instead of loading all global geometries into Plotly.

## Important data design
HydroRIVERS contains reach records, not a universally complete named-river catalogue. The app therefore identifies individual reaches by `HYRIV_ID` and uses the supplied network attributes. It does not infer a river name or flow path by connecting nearby lines.

The app's global overview remains available without HydroSHEDS data. Detailed regional analysis requires a locally prepared `data/terra_atlas_hydrology.gpkg`.

## Prepare the data
1. Download HydroRIVERS shapefile ZIP(s) from https://www.hydrosheds.org/products/hydrorivers
2. Download HydroBASINS standard shapefile ZIP(s) from https://www.hydrosheds.org/products/hydrobasins
3. Extract all downloaded ZIPs under `source_data/` (keep the original shapefile sidecar files together).
4. Install dependencies: `pip install -r requirements.txt`
5. Run:
   `python prepare_hydrology.py --source-dir source_data --output data/terra_atlas_hydrology.gpkg`
6. Run `streamlit run app.py`.

For a first end-to-end test, download Africa for both datasets. For global coverage, download all available regions. Keep the prepared GeoPackage outside GitHub if it becomes too large; use a persistent hosted data store or a release/object-storage URL for production deployment.

## Streamlit Community Cloud note
Do not commit the raw source ZIPs. The final GeoPackage may be large and can exceed practical repository or app memory limits. v0.4 is designed to keep the data preparation separate from the app. For a public deployment, host the GeoPackage on durable object storage or publish preprocessed regional packages and load only the selected region.

## Data limitations
- HydroRIVERS is a modeled/cartographic river network with a defined mapping threshold; it is not every stream.
- `DIS_AV_CMS` is an estimated long-term average, not live discharge.
- `LENGTH_KM` is reach length, not necessarily the total length of a named river.
- HydroBASINS polygons are hierarchical basin units, not a live flood forecast.
- Current release displays selected-region reaches and attributes. Full graph traversal, named river reconstruction, and basin-to-reach analytical joins are planned next.

## Source documentation
- HydroRIVERS: https://www.hydrosheds.org/products/hydrorivers
- HydroBASINS: https://www.hydrosheds.org/products/hydrobasins
- Natural Earth: https://www.naturalearthdata.com/
