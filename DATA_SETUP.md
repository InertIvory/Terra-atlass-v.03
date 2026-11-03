# Data setup quick guide

Download official HydroRIVERS and HydroBASINS shapefile ZIPs from the links in README.md.
Extract them into `source_data/` without separating the .shp, .shx, .dbf, .prj and other sidecar files.

Recommended first test:
- HydroRIVERS: Africa
- HydroBASINS: Africa (standard)

Then run:
```bash
pip install -r requirements.txt
python prepare_hydrology.py --source-dir source_data --output data/terra_atlas_hydrology.gpkg
streamlit run app.py
```

For global coverage, add all continental regional packages before running the preparation script.
