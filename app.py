import math
import time
import requests
import streamlit as st
import plotly.graph_objects as go
import numpy as np
from pathlib import Path

st.set_page_config(
    page_title="Terra Atlas | Explore Earth",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

COUNTRIES_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
    "master/geojson/ne_110m_admin_0_countries.geojson"
)
RIVERS_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
    "master/geojson/ne_110m_rivers_lake_centerlines.geojson"
)
ELEVATION_URL = "https://api.open-meteo.com/v1/elevation"

st.markdown("""
<style>
    .block-container {padding-top: 1.2rem; padding-bottom: 2rem;}
    .hero {padding: 1.15rem 1.35rem; border: 1px solid rgba(128,128,128,.25);
           border-radius: 14px; margin-bottom: 1rem;}
    .hero h1 {margin: 0 0 .25rem 0; letter-spacing: -.04em;}
    .muted {opacity: .72; font-size: .92rem;}
    div[data-testid="stMetric"] {border: 1px solid rgba(128,128,128,.22);
        padding: .75rem; border-radius: 12px;}
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=86400, show_spinner="Loading geographic datasets…")
def load_geojson(url: str):
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json()


def feature_name(feature):
    props = feature.get("properties", {})
    return (
        props.get("ADMIN") or props.get("NAME") or
        props.get("name") or props.get("NAME_EN") or "Unknown"
    )


def river_parts(geometry):
    if not geometry:
        return
    kind = geometry.get("type")
    coords = geometry.get("coordinates", [])
    if kind == "LineString":
        yield coords
    elif kind == "MultiLineString":
        yield from coords
    elif kind == "GeometryCollection":
        for item in geometry.get("geometries", []):
            yield from river_parts(item)


def river_name(feature):
    props = feature.get("properties", {})
    return props.get("name") or props.get("NAME") or props.get("name_en") or props.get("NAME_EN")


def make_river_map(feature, name):
    fig = go.Figure()
    lon_values, lat_values = [], []
    parts = list(river_parts(feature.get("geometry")))
    for part in parts:
        for point in part:
            if len(point) >= 2:
                lon_values.append(point[0])
                lat_values.append(point[1])
        lon_values.append(None)
        lat_values.append(None)

    fig.add_trace(go.Scattergeo(
        lon=lon_values, lat=lat_values, mode="lines",
        line=dict(width=3, color="#20b8e6"),
        name=name,
        hovertemplate=f"<b>{name}</b><extra>Generalized river geometry</extra>",
    ))
    fig.update_geos(
        projection_type="natural earth",
        showland=True, landcolor="#e5e1d5",
        showocean=True, oceancolor="#c7dce5",
        showcountries=True, countrycolor="#657782",
        showcoastlines=True, coastlinecolor="#657782",
        showframe=False,
    )
    fig.update_layout(height=560, margin=dict(l=0, r=0, t=5, b=0))
    return fig


def build_map(countries, rivers, selected_name, show_rivers, show_labels,
              projection, map_theme):
    features = countries.get("features", [])
    locations, names, regions, populations, gdp = [], [], [], [], []
    selected_iso = None

    for feature in features:
        p = feature.get("properties", {})
        iso = p.get("ADM0_A3") or p.get("SOV_A3") or p.get("ISO_A3")
        if not iso or iso == "-99":
            continue
        name = feature_name(feature)
        locations.append(iso)
        names.append(name)
        regions.append(p.get("REGION_UN", ""))
        populations.append(p.get("POP_EST"))
        gdp.append(p.get("GDP_MD"))
        if name == selected_name:
            selected_iso = iso

    if map_theme == "Dark":
        land, ocean, border, river_color, text_color = "#17232d", "#08131e", "#718391", "#48b9d6", "#edf5f8"
    elif map_theme == "Satellite-inspired":
        land, ocean, border, river_color, text_color = "#34483d", "#101e2c", "#8b9b87", "#63c9ed", "#f4f5e9"
    else:
        land, ocean, border, river_color, text_color = "#e5e1d5", "#c7dce5", "#657782", "#2688b7", "#1b2930"

    fig = go.Figure()
    fig.add_trace(go.Choropleth(
        geojson=countries, locations=locations, z=[1] * len(locations),
        featureidkey="properties.ADM0_A3",
        customdata=list(zip(names, regions, populations, gdp)),
        colorscale=[[0, "#789b83"], [1, "#789b83"]],
        showscale=False, marker_line_color=border, marker_line_width=0.45,
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>Region: %{customdata[1]}<br>"
            "Estimated population: %{customdata[2]:,.0f}<br>"
            "GDP (US$ millions): %{customdata[3]:,.0f}<extra></extra>"
        ), name="Countries",
    ))

    if selected_iso:
        fig.add_trace(go.Choropleth(
            geojson=countries, locations=[selected_iso], z=[1],
            featureidkey="properties.ADM0_A3",
            colorscale=[[0, "#f0b44d"], [1, "#f0b44d"]],
            showscale=False, marker_line_color="#fff2d4",
            marker_line_width=1.15, hoverinfo="skip",
            name="Selected country",
        ))

    if show_rivers:
        for feature in rivers.get("features", []):
            props = feature.get("properties", {})
            river_name = props.get("name") or props.get("NAME") or props.get("name_en") or "Unnamed river"
            lons, lats = [], []
            for part in river_parts(feature.get("geometry")):
                for point in part:
                    if len(point) >= 2:
                        lons.append(point[0])
                        lats.append(point[1])
                lons.append(None)
                lats.append(None)
            if lons:
                fig.add_trace(go.Scattergeo(
                    lon=lons, lat=lats, mode="lines",
                    line=dict(width=1.15, color=river_color),
                    text=[river_name] * len(lons),
                    hovertemplate="<b>%{text}</b><extra>River / drainage</extra>",
                    showlegend=False,
                ))

    if show_labels:
        label_lons, label_lats, label_names = [], [], []
        for feature in features:
            p = feature.get("properties", {})
            x, y = p.get("LABEL_X"), p.get("LABEL_Y")
            if x is not None and y is not None:
                label_lons.append(x)
                label_lats.append(y)
                label_names.append(feature_name(feature))
        fig.add_trace(go.Scattergeo(
            lon=label_lons, lat=label_lats, text=label_names,
            mode="text", textfont=dict(size=8, color=text_color),
            hoverinfo="skip", showlegend=False,
        ))

    fig.update_geos(
        projection_type=projection.lower(),
        showland=True, landcolor=land, showocean=True, oceancolor=ocean,
        showcountries=True, countrycolor=border,
        showcoastlines=True, coastlinecolor=border,
        showlakes=True, lakecolor=ocean, showrivers=False,
        showframe=False, bgcolor="rgba(0,0,0,0)",
        lataxis_showgrid=True, lataxis_gridcolor="rgba(130,150,160,.22)",
        lonaxis_showgrid=True, lonaxis_gridcolor="rgba(130,150,160,.22)",
    )
    fig.update_layout(
        height=660, margin=dict(l=0, r=0, t=5, b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=text_color), dragmode="pan",
        uirevision="terra-atlas-map",
    )
    return fig


@st.cache_data(ttl=604800, show_spinner="Sampling terrain elevation…")
def get_elevation_grid(lat_min, lat_max, lon_min, lon_max, resolution):
    """Fetch one <=100-point elevation grid; retry temporary rate limits."""
    latitudes = np.linspace(lat_min, lat_max, resolution)
    longitudes = np.linspace(lon_min, lon_max, resolution)
    lon_grid, lat_grid = np.meshgrid(longitudes, latitudes)
    flat_lats, flat_lons = lat_grid.ravel(), lon_grid.ravel()

    if len(flat_lats) > 100:
        raise ValueError("Choose terrain detail of 10 or lower (maximum 100 points).")

    params = {
        "latitude": ",".join(f"{v:.5f}" for v in flat_lats),
        "longitude": ",".join(f"{v:.5f}" for v in flat_lons),
    }
    with requests.Session() as session:
        for attempt in range(4):
            response = session.get(ELEVATION_URL, params=params, timeout=60)
            if response.status_code == 429 or response.status_code in (500, 502, 503, 504):
                if attempt == 3:
                    response.raise_for_status()
                retry = response.headers.get("Retry-After")
                try:
                    delay = float(retry) if retry else 3 * (2 ** attempt)
                except ValueError:
                    delay = 3 * (2 ** attempt)
                time.sleep(min(max(delay, 2), 30))
                continue
            response.raise_for_status()
            payload = response.json()
            if "elevation" not in payload:
                raise ValueError(payload.get("reason", "No elevation array returned."))
            values = payload["elevation"]
            if len(values) != len(flat_lats):
                raise ValueError(f"Expected {len(flat_lats)} values, received {len(values)}.")
            z = np.asarray(values, dtype=float).reshape(resolution, resolution)
            z[~np.isfinite(z)] = np.nan
            return longitudes, latitudes, z
    raise RuntimeError("Elevation API remained rate-limited after retries.")


PRESETS = {
    "Himalayas — Mount Everest": (27.9881, 86.9250, 1.8),
    "Drakensberg — Southern Africa": (-29.35, 29.35, 2.2),
    "Cape Fold Mountains — South Africa": (-33.65, 19.35, 1.0),
    "Andes — Aconcagua": (-32.6532, -70.0109, 2.0),
    "Alps — Mont Blanc": (45.8326, 6.8652, 1.1),
    "Grand Canyon — USA": (36.1069, -112.1129, 1.0),
    "East African Rift": (-2.5, 36.0, 3.0),
    "Custom coordinates": (-29.0, 25.0, 2.0),
}


def terrain_figure(lons, lats, elevations, exaggeration, palette):
    z_plot = elevations * exaggeration
    colors = {
        "Earth": "earth",
        "Viridis": "viridis",
        "Terrain": "terrain",
        "Hot": "hot",
    }
    fig = go.Figure(data=[go.Surface(
        x=lons, y=lats, z=z_plot,
        surfacecolor=elevations,
        colorscale=colors.get(palette, "earth"),
        colorbar=dict(title="Elevation<br>(m)", thickness=14),
        hovertemplate=(
            "Longitude: %{x:.3f}°<br>Latitude: %{y:.3f}°"
            "<br>Displayed height: %{z:,.0f} m"
            "<extra>Terrain grid</extra>"
        ),
        connectgaps=False,
    )])
    fig.update_layout(
        height=650,
        margin=dict(l=0, r=0, t=10, b=0),
        scene=dict(
            xaxis_title="Longitude (°)",
            yaxis_title="Latitude (°)",
            zaxis_title=f"Elevation × {exaggeration:.1f} (m)",
            aspectmode="manual",
            aspectratio=dict(x=1.25, y=1, z=0.55),
            camera=dict(eye=dict(x=1.55, y=1.55, z=1.15)),
        ),
    )
    return fig




# --- Terra Atlas v0.4: multiscale HydroSHEDS integration --------------------
DATA_DIR = Path(__file__).parent / "data"
HYDRO_GPKG = DATA_DIR / "terra_atlas_hydrology.gpkg"

# Bounds are ordered as (west longitude, south latitude, east longitude, north latitude).
HYDRO_REGIONS = {
    "Africa": (-18.0, -35.0, 52.0, 37.5),
    "Asia": (25.0, 5.0, 180.0, 80.0),
    "Australasia": (110.0, -50.0, 180.0, 0.0),
    "Europe and Middle East": (-25.0, 25.0, 65.0, 72.0),
    "North and Central America": (-170.0, 5.0, -50.0, 85.0),
    "South America": (-85.0, -60.0, -30.0, 15.0),
    "Siberia": (60.0, 45.0, 180.0, 82.0),
    "Arctic": (-180.0, 50.0, 180.0, 90.0),
    "Greenland": (-75.0, 58.0, -10.0, 84.0),
}

def load_hydro_layer(layer, bounds, max_features=18000):
    """Read only features intersecting a regional bounding box from the prepared GeoPackage."""
    if not HYDRO_GPKG.exists():
        return None, "HydroSHEDS data package is not installed."
    try:
        import geopandas as gpd
        minx, miny, maxx, maxy = bounds
        frame = gpd.read_file(
            HYDRO_GPKG, layer=layer,
            bbox=(minx, miny, maxx, maxy),
            engine="pyogrio",
            use_arrow=True
        )
        if len(frame) > max_features:
            frame = frame.sample(n=max_features, random_state=7)
        return frame, None
    except Exception as exc:
        return None, str(exc)

def hydro_layer_figure(rivers_frame, basins_frame=None):
    fig = go.Figure()
    if basins_frame is not None and not basins_frame.empty:
        # Basin polygons are optional and rendered with low opacity.
        for geom in basins_frame.geometry:
            if geom is None:
                continue
            geoms = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
            for polygon in geoms:
                x, y = polygon.exterior.xy
                fig.add_trace(go.Scattergeo(
                    lon=list(x), lat=list(y), mode="lines",
                    line=dict(width=0.45, color="rgba(120,160,180,.45)"),
                    fill="toself", fillcolor="rgba(80,140,170,.045)",
                    hoverinfo="skip", showlegend=False
                ))
    if rivers_frame is not None and not rivers_frame.empty:
        for _, row in rivers_frame.iterrows():
            geom = row.geometry
            if geom is None:
                continue
            lines = list(geom.geoms) if geom.geom_type == "MultiLineString" else [geom]
            for line in lines:
                x, y = line.xy
                props = row
                reach_id = props.get("HYRIV_ID", "Unknown")
                order = props.get("ORD_STRA", "n/a")
                discharge = props.get("DIS_AV_CMS", "n/a")
                fig.add_trace(go.Scattergeo(
                    lon=list(x), lat=list(y), mode="lines",
                    line=dict(width=1.15, color="#22b8e6"),
                    text=[f"Reach ID: {reach_id}<br>Stream order: {order}<br>Mean discharge: {discharge} m³/s"] * len(x),
                    hovertemplate="%{text}<extra>HydroRIVERS</extra>",
                    showlegend=False
                ))
    fig.update_geos(
        projection_type="natural earth", showland=True, landcolor="#e5e1d5",
        showocean=True, oceancolor="#c7dce5", showcountries=True,
        countrycolor="#657782", showcoastlines=True,
        coastlinecolor="#657782", showframe=False
    )
    fig.update_layout(height=590, margin=dict(l=0, r=0, t=5, b=0))
    return fig


st.markdown("""
<div class="hero">
  <h1>🌍 Terra Atlas</h1>
  <div class="muted">An interactive field guide to our planet — countries, rivers,
  topography and the systems that connect them.</div>
</div>
""", unsafe_allow_html=True)

tab_globe, tab_terrain, tab_hydrology = st.tabs(["🌐 World globe", "⛰️ Terrain explorer", "💧 Hydrology"])

with tab_globe:
    with st.sidebar:
        st.header("Globe controls")
        projection = st.selectbox(
            "Globe projection",
            ["Orthographic", "Natural Earth", "Equirectangular"],
            help="Drag to rotate; use the scroll wheel or map controls to zoom.",
        )
        map_theme = st.selectbox("Map appearance", ["Atlas", "Dark", "Satellite-inspired"])
        show_rivers = st.toggle("Show major rivers", value=True)
        show_labels = st.toggle("Show country labels", value=False)
        st.divider()
        st.subheader("Find a country")
        st.caption("Choose a country to highlight it and inspect available facts.")

    try:
        countries = load_geojson(COUNTRIES_URL)
        rivers = load_geojson(RIVERS_URL)
    except Exception as exc:
        st.error("The geographic datasets could not be loaded. Check your internet connection and refresh the app.")
        st.code(str(exc))
        st.stop()

    country_features = countries.get("features", [])
    country_names = sorted({feature_name(f) for f in country_features})
    default_index = country_names.index("South Africa") if "South Africa" in country_names else 0
    with st.sidebar:
        selected_name = st.selectbox("Country", country_names, index=default_index)

    selected_feature = next((f for f in country_features if feature_name(f) == selected_name), None)
    selected_props = selected_feature.get("properties", {}) if selected_feature else {}

    left, right = st.columns([3.25, 1], gap="large")
    with left:
        st.subheader("Explore the globe")
        st.caption("Drag to rotate • Scroll to zoom • Hover over countries and rivers for information")
        figure = build_map(
            countries, rivers, selected_name, show_rivers, show_labels,
            projection, map_theme
        )
        st.plotly_chart(
            figure, use_container_width=True,
            config={
                "scrollZoom": True, "displayModeBar": True,
                "modeBarButtonsToRemove": ["lasso2d", "select2d"],
                "displaylogo": False, "responsive": True,
            },
        )

    with right:
        st.subheader(selected_name)
        if selected_props:
            region = selected_props.get("REGION_UN") or "Not listed"
            subregion = selected_props.get("SUBREGION") or "Not listed"
            population = selected_props.get("POP_EST")
            area = selected_props.get("AREA")
            gdp = selected_props.get("GDP_MD")
            st.metric("World region", region)
            st.write(f"**Subregion:** {subregion}")
            if isinstance(population, (int, float)):
                st.metric("Estimated population", f"{population:,.0f}")
            if isinstance(area, (int, float)):
                st.metric("Land area", f"{area:,.0f} km²")
            if isinstance(gdp, (int, float)):
                st.metric("GDP estimate", f"${gdp:,.0f} million")
            st.caption("Country statistics are Natural Earth estimates and may be dated or generalized.")
        st.divider()
        st.markdown("**What am I looking at?**")
        st.write(
            "Country polygons show generalized national boundaries. Blue lines represent "
            "major mapped rivers and drainage centerlines. Small rivers and local waterways "
            "are not included at this global map scale."
        )

    st.divider()
    st.subheader("A planet to investigate")
    topic1, topic2, topic3 = st.columns(3)
    with topic1:
        st.markdown("#### 🌊 Hydrology")
        st.write("Trace river systems from source regions to deltas. Explore how water links mountains, farms, cities and oceans.")
    with topic2:
        st.markdown("#### 🏔️ Physical geography")
        st.write("Compare continents, coastlines, deserts, mountain systems and the major physical features of Earth.")
    with topic3:
        st.markdown("#### 🧭 Human geography")
        st.write("Use the map as a foundation for studying population, migration, borders, trade and urbanization.")

with tab_terrain:
    st.subheader("Explore Earth's surface in 3D")
    st.write(
        "Choose a mountain system or region to sample its terrain. Drag to orbit the surface, "
        "scroll to zoom, and hover over the grid to inspect coordinates and elevation."
    )
    preset_name = st.selectbox("Region", list(PRESETS.keys()))
    default_lat, default_lon, default_span = PRESETS[preset_name]
    custom = preset_name == "Custom coordinates"

    c1, c2, c3 = st.columns(3)
    with c1:
        center_lat = st.number_input(
            "Centre latitude", min_value=-85.0, max_value=85.0,
            value=float(default_lat), step=0.1, format="%.4f",
            disabled=not custom, key=f"lat_{preset_name}",
        )
    with c2:
        center_lon = st.number_input(
            "Centre longitude", min_value=-180.0, max_value=180.0,
            value=float(default_lon), step=0.1, format="%.4f",
            disabled=not custom, key=f"lon_{preset_name}",
        )
    with c3:
        span = st.slider(
            "Area width (approx. degrees)", 0.5, 5.0,
            float(default_span), 0.1,
            help="Larger areas show more terrain but less local detail.",
        )

    c4, c5, c6 = st.columns(3)
    with c4:
        resolution = st.select_slider("Terrain detail", options=[5, 7, 9, 10], value=9, help="Maximum 100 sample points per terrain request.")
    with c5:
        exaggeration = st.slider("Vertical exaggeration", 1.0, 5.0, 2.0, 0.5)
    with c6:
        palette = st.selectbox("Elevation palette", ["Earth", "Viridis", "Terrain", "Hot"])

    if st.button("Generate 3D terrain", type="primary", use_container_width=True):
        lat_min = max(-89.0, center_lat - span / 2)
        lat_max = min(89.0, center_lat + span / 2)
        lon_min = max(-179.0, center_lon - span / 2)
        lon_max = min(179.0, center_lon + span / 2)
        try:
            lons, lats, elevation_grid = get_elevation_grid(
                round(lat_min, 4), round(lat_max, 4),
                round(lon_min, 4), round(lon_max, 4),
                int(resolution),
            )
            st.session_state["terrain_result"] = {
                "lons": lons, "lats": lats, "z": elevation_grid,
                "region": preset_name, "lat": center_lat, "lon": center_lon,
                "span": span,
            }
        except Exception as exc:
            st.error("Terrain data could not be retrieved. Please try again.")
            st.code(str(exc))

    terrain = st.session_state.get("terrain_result")
    if terrain:
        st.markdown(f"### {terrain['region']}")
        grid = terrain["z"]
        valid = grid[np.isfinite(grid)]
        if valid.size:
            m1, m2, m3 = st.columns(3)
            m1.metric("Highest sampled point", f"{np.nanmax(grid):,.0f} m")
            m2.metric("Lowest sampled point", f"{np.nanmin(grid):,.0f} m")
            m3.metric("Relief in sampled area", f"{np.nanmax(grid)-np.nanmin(grid):,.0f} m")
            fig = terrain_figure(
                terrain["lons"], terrain["lats"], grid,
                exaggeration, palette,
            )
            st.plotly_chart(
                fig, use_container_width=True,
                config={"scrollZoom": True, "displaylogo": False, "responsive": True},
            )
            st.caption(
                "The vertical exaggeration changes the displayed shape, not the measured elevation. "
                "The summary statistics use sampled points only; they are not guaranteed regional maxima or minima."
            )
        else:
            st.warning("No valid elevation samples were returned for this area.")
    else:
        st.info("Choose a region and select **Generate 3D terrain** to load its elevation surface.")

    with st.expander("How the terrain layer works"):
        st.markdown("""
        - Elevation is sampled from the **Copernicus DEM GLO-90**, a global digital elevation model.
        - The source dataset has a nominal 90-metre grid, but this app samples a much coarser display grid to keep the interactive 3D surface responsive.
        - Each terrain grid uses up to 10 × 10 sample locations (100 points) in one request. Temporary rate limits are retried with backoff.
        - The 3D surface is a regional terrain view, not a full-resolution survey model. Fine ridges, cliffs and small valleys may be smoothed or missed.
        - Vertical exaggeration is a visual aid and must not be mistaken for true slope or height proportions.
        """)


with tab_hydrology:
    st.subheader("Global river-network explorer")
    st.write(
        "Explore the global river system at multiple scales. The Natural Earth layer "
        "provides the lightweight global overview; HydroRIVERS and HydroBASINS add "
        "regional reach and watershed detail when the prepared data package is installed."
    )

    overview_col, status_col = st.columns([2, 1])
    with overview_col:
        st.markdown("**Global overview**")
        st.caption("Major generalized rivers from Natural Earth. Use regional detail below for individual HydroRIVERS reaches.")
        st.plotly_chart(
            make_river_map(
                {"geometry": {"type": "MultiLineString", "coordinates": [
                    part for f in load_geojson(RIVERS_URL).get("features", [])
                    for part in river_parts(f.get("geometry"))
                ]}},
                "Global major rivers"
            ),
            use_container_width=True,
            config={"scrollZoom": True, "displaylogo": False, "responsive": True},
        )
    with status_col:
        st.markdown("**HydroSHEDS data status**")
        if HYDRO_GPKG.exists():
            st.success("Prepared global GeoPackage detected.")
            st.caption(f"Data file: {HYDRO_GPKG.name}")
        else:
            st.warning("HydroSHEDS package not installed yet.")
            st.caption("Follow DATA_SETUP.md and run prepare_hydrology.py. The global overview remains available without it.")

    st.divider()
    st.markdown("### Regional river-network detail")
    region = st.selectbox("Select geographic region", list(HYDRO_REGIONS.keys()), index=0)
    bounds = HYDRO_REGIONS[region]
    st.caption(f"Regional extent: longitude {bounds[0]}° to {bounds[2]}°, latitude {bounds[1]}° to {bounds[3]}°")
    if st.button("Load regional hydrology", type="primary", use_container_width=True):
        with st.spinner(f"Reading {region} HydroSHEDS features…"):
            river_frame, river_error = load_hydro_layer("hydrorivers", bounds)
            basin_frame, basin_error = load_hydro_layer("hydrobasins", bounds, max_features=2500)
            st.session_state["hydro_region_result"] = {
                "region": region,
                "rivers": river_frame,
                "basins": basin_frame,
                "river_error": river_error,
                "basin_error": basin_error,
            }

    result = st.session_state.get("hydro_region_result")
    if result and result["region"] == region:
        if result["river_error"]:
            st.error("HydroRIVERS could not be read.")
            st.code(result["river_error"])
        elif result["rivers"] is not None:
            rf = result["rivers"]
            bf = result["basins"]
            k1, k2, k3 = st.columns(3)
            k1.metric("River reaches in view", f"{len(rf):,}")
            if "ORD_STRA" in rf.columns:
                k2.metric("Highest stream order", str(rf["ORD_STRA"].max()))
            else:
                k2.metric("Stream-order field", "Unavailable")
            if "DIS_AV_CMS" in rf.columns:
                k3.metric("Reach records with discharge", f"{rf['DIS_AV_CMS'].notna().sum():,}")
            st.plotly_chart(
                hydro_layer_figure(rf, bf if result["basin_error"] is None else None),
                use_container_width=True,
                config={"scrollZoom": True, "displaylogo": False, "responsive": True},
            )
            st.markdown("#### Inspect individual river reaches")
            searchable = [c for c in ["HYRIV_ID", "NEXT_DOWN", "MAIN_RIV", "ORD_STRA", "ORD_CLAS", "LENGTH_KM", "DIS_AV_CMS", "CATCH_SKM", "DIST_DN_KM", "DIST_UP_KM", "PFAF_ID", "HYBAS_L12"] if c in rf.columns]
            if "HYRIV_ID" in rf.columns and len(rf):
                labels = rf["HYRIV_ID"].astype(str).tolist()
                chosen = st.selectbox("HydroRIVERS reach ID", labels)
                selected_row = rf.loc[rf["HYRIV_ID"].astype(str) == chosen].iloc[0]
                st.json({c: (None if selected_row[c] is None else str(selected_row[c])) for c in searchable}, expanded=True)
            if result["basin_error"]:
                st.info("HydroBASINS layer was not available for this region: " + result["basin_error"])
            elif bf is not None:
                st.metric("Basin polygons loaded", f"{len(bf):,}")
    else:
        st.info("Select a region and load its detailed river network. The global overview works without the optional HydroSHEDS package.")

    with st.expander("What the HydroSHEDS attributes mean"):
        st.markdown("""
        - **HYRIV_ID:** unique identifier for a mapped river reach.
        - **NEXT_DOWN:** identifier of the next downstream reach; zero or missing values may indicate an outlet or unavailable link.
        - **MAIN_RIV:** identifier for the associated main river.
        - **ORD_STRA / ORD_CLAS:** stream-order attributes supplied by HydroRIVERS.
        - **LENGTH_KM:** mapped reach length in kilometres, not necessarily the full named river length.
        - **DIS_AV_CMS:** estimated long-term average discharge in cubic metres per second; it is not a live measurement.
        - **CATCH_SKM:** upstream catchment area in square kilometres.
        - **DIST_DN_KM / DIST_UP_KM:** distances along the network in downstream/upstream directions.
        - **PFAF_ID / HYBAS_L12:** basin identifiers linking reaches to HydroBASINS hierarchy.

        HydroRIVERS reach records do not provide a universal, authoritative common river name for every segment. The first release therefore identifies reaches by dataset ID and network attributes, rather than inventing names or joining reaches based on proximity.
        """)

st.divider()
st.caption(
    "Terra Atlas • Version 0.4 • Streamlit + Plotly + Natural Earth + optional HydroSHEDS HydroRIVERS/HydroBASINS + Copernicus DEM via Open-Meteo."
)
