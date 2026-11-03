#!/usr/bin/env python3
"""
Prepare HydroSHEDS vector downloads for Terra Atlas v0.4.

1. Download HydroRIVERS shapefile ZIP(s) from https://www.hydrosheds.org/products/hydrorivers
2. Download HydroBASINS standard shapefile ZIP(s) from https://www.hydrosheds.org/products/hydrobasins
3. Put the ZIP files in a folder, e.g. ./source_data/
4. Run: python prepare_hydrology.py --source-dir source_data --output data/terra_atlas_hydrology.gpkg

The script reads all ZIPs in source-dir, identifies river/basin shapefiles by filename,
reprojects to EPSG:4326, and writes two layers to one GeoPackage.
It does not fabricate river names or derive connectivity from geometric proximity.
"""
import argparse
from pathlib import Path
import geopandas as gpd
import pandas as pd

def find_shapefiles(folder, dataset):
    found = []
    for shp in Path(folder).rglob("*.shp"):
        name = shp.name.lower().replace("_", "")
        if dataset == "rivers" and ("hydroriv" in name or name.startswith("hyriv")):
            found.append(shp)
        elif dataset == "basins" and ("hydrobasin" in name or name.startswith("hybas")):
            found.append(shp)
    return found

def combine_layers(paths, layer_name):
    frames = []
    for path in paths:
        print(f"Reading {path}")
        frame = gpd.read_file(path, engine="pyogrio", use_arrow=True)
        if frame.crs is None:
            raise ValueError(f"Missing CRS in {path}")
        frame = frame.to_crs("EPSG:4326")
        frames.append(frame)
    if not frames:
        raise FileNotFoundError(f"No shapefiles found for {layer_name}. Extract official HydroSHEDS ZIPs first.")
    return gpd.GeoDataFrame(
        pd.concat(frames, ignore_index=True),
        geometry="geometry", crs="EPSG:4326"
    )

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", default="source_data")
    parser.add_argument("--output", default="data/terra_atlas_hydrology.gpkg")
    args = parser.parse_args()

    source = Path(args.source_dir)
    if not source.exists():
        raise FileNotFoundError(f"Source folder not found: {source}")
    river_files = find_shapefiles(source, "rivers")
    basin_files = find_shapefiles(source, "basins")
    if not river_files:
        raise FileNotFoundError("No HydroRIVERS .shp found. Extract official HydroRIVERS ZIP(s) into source_data.")
    if not basin_files:
        raise FileNotFoundError("No HydroBASINS .shp found. Extract official HydroBASINS ZIP(s) into source_data.")

    rivers = combine_layers(river_files, "HydroRIVERS")
    basins = combine_layers(basin_files, "HydroBASINS")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()

    print(f"Writing {len(rivers):,} river reaches…")
    rivers.to_file(output, layer="hydrorivers", driver="GPKG", engine="pyogrio", spatial_index=True)
    print(f"Writing {len(basins):,} basin polygons…")
    basins.to_file(output, layer="hydrobasins", driver="GPKG", engine="pyogrio", spatial_index=True)
    print(f"Finished: {output.resolve()} ({output.stat().st_size / 1_000_000:.1f} MB)")
    print("Copy the resulting data/ folder into the Terra Atlas app directory for local testing/deployment.")

if __name__ == "__main__":
    main()
