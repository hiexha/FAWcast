import time
import math
import streamlit as st
import plotly.graph_objects as go

BETA = {
    "intercept": -32.6401, "tmax": 0.2790, "tmin": -0.3650,
    "rainfall": -0.0048, "humidity": -0.0284, "prev_outbreak": 2.7233,
    "prev_rainfall": -0.0639, "prev_tmax": 0.5805, "prev_tmin": 0.5923,
    "rain_cum_2q": 0.0643,
}

# Region random intercepts (Table V), centroid coordinates, and approximate
# land area in sq km (used to size each region's filled circle proportionally)
REGIONS = {
    "Bicol Region":          {"u": -0.2971, "lat": 13.42, "lon": 123.41, "area_km2": 18155},
    "Cagayan Valley":        {"u":  0.2989, "lat": 17.61, "lon": 121.73, "area_km2": 29836},
    "Ilocos Region":         {"u": -1.6065, "lat": 16.08, "lon": 120.62, "area_km2": 13012},
    "Northern Mindanao":     {"u":  0.1275, "lat":  8.15, "lon": 124.24, "area_km2": 20496},
    "SOCCSKSARGEN":          {"u":  0.9616, "lat":  6.30, "lon": 124.85, "area_km2": 22513},
    "Zamboanga Peninsula":   {"u":  0.5156, "lat":  7.84, "lon": 122.27, "area_km2": 17056},
}

TIER_COLORS = {
    "Low Risk": "#4a7c59",
    "Moderate Risk": "#b8862f",
    "High Risk": "#c96a2b",
    "Very High Risk": "#a1352d",
}

TIER_ACTION = {
    "Low Risk": "Continue routine monitoring at standard intervals.",
    "Moderate Risk": "Increase field scouting frequency in the area.",
    "High Risk": "Implement integrated pest management measures and coordinate with local extension offices.",
    "Very High Risk": "Issue an outbreak alert; recommend immediate response and intensive field surveillance.",
}


def classify(p):
    if p < 0.30: return "Low Risk"
    if p < 0.60: return "Moderate Risk"
    if p < 0.80: return "High Risk"
    return "Very High Risk"


def region_circle(lat, lon, area_km2, n_points=60):
    """Builds a circle polygon (lat/lon points) whose area approximates
    the region's real land area, centered on its centroid."""
    radius_km = math.sqrt(area_km2 / math.pi)
    lat_rad = math.radians(lat)
    km_per_deg_lat = 110.574
    km_per_deg_lon = 111.320 * math.cos(lat_rad)

    lats, lons = [], []
    for i in range(n_points + 1):
        angle = 2 * math.pi * i / n_points
        dlat = (radius_km * math.sin(angle)) / km_per_deg_lat
        dlon = (radius_km * math.cos(angle)) / km_per_deg_lon
        lats.append(lat + dlat)
        lons.append(lon + dlon)
    return lats, lons


def base_map():
    """Draws the Philippines only, with all 6 regions as faint outlined circles."""
    fig = go.Figure()
    for name, r in REGIONS.items():
        lats, lons = region_circle(r["lat"], r["lon"], r["area_km2"])
        fig.add_trace(go.Scattergeo(
            lat=lats, lon=lons,
            mode="lines",
            line=dict(width=1.2, color="#9a9a9a"),
            fill="toself",
            fillcolor="rgba(154,154,154,0.15)",
            hoverinfo="skip",
            showlegend=False,
        ))
        fig.add_trace(go.Scattergeo(
            lat=[r["lat"]], lon=[r["lon"]],
            mode="text",
            text=[name],
            textposition="middle center",
            textfont=dict(size=9, color="#4a4030"),
            hoverinfo="skip",
            showlegend=False,
        ))

    fig.update_geos(
        scope="asia",
        lataxis_range=[4, 21],
        lonaxis_range=[116, 128],
        showland=True, landcolor="#f0ead9",
        showocean=True, oceancolor="#dce8ec",
        showcountries=True, countrycolor="#b5aa8f",
        showcoastlines=True, coastlinecolor="#b5aa8f",
        showsubunits=False,
        resolution=50,
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=520,
        showlegend=False,
    )
    return fig


def fill_region(fig, region_name, color, opacity):
    r = REGIONS[region_name]
    lats, lons = region_circle(r["lat"], r["lon"], r["area_km2"])
    fig.add_trace(go.Scattergeo(
        lat=lats, lon=lons,
        mode="lines",
        line=dict(width=1.5, color="#2b2418"),
        fill="toself",
        fillcolor=color,
        opacity=opacity,
        hoverinfo="skip",
        showlegend=False,
    ))
    return fig


st.set_page_config(page_title="FAWcast Risk Calculator", layout="wide")
st.title("FAWcast Outbreak-Risk Calculator")
st.caption("Hierarchical logistic regression model - Table IV & V")

region = st.selectbox("Region", list(REGIONS.keys()) + ["Untrained (population average)"])

st.subheader("Same-quarter weather")
c1, c2 = st.columns(2)
tmax = c1.number_input("Max Temp (C)", value=31.5)
tmin = c2.number_input("Min Temp (C)", value=23.2)
rainfall = c1.number_input("Rainfall (mm/day)", value=21.6)
humidity = c2.number_input("Relative Humidity (%)", value=82.8)

st.subheader("Previous quarter")
prev_outbreak = st.radio("Outbreak occurred?", ["No", "Yes"], index=1)
c3, c4 = st.columns(2)
prev_tmax = c3.number_input("Prev. Max Temp (C)", value=31.5)
prev_tmin = c4.number_input("Prev. Min Temp (C)", value=23.2)
prev_rainfall = c3.number_input("Prev. Rainfall (mm/day)", value=21.6)
rain_cum_2q = c4.number_input("2-Qtr Cumulative Rain (mm)", value=43.2)

calculate = st.button("Calculate Risk", type="primary")

map_slot = st.empty()
result_slot = st.empty()

map_slot.plotly_chart(base_map(), use_container_width=True)

if calculate:
    u = REGIONS.get(region, {}).get("u", 0.0)
    log_odds = (
        BETA["intercept"] + BETA["tmax"] * tmax + BETA["tmin"] * tmin +
        BETA["rainfall"] * rainfall + BETA["humidity"] * humidity +
        BETA["prev_outbreak"] * (1 if prev_outbreak == "Yes" else 0) +
        BETA["prev_rainfall"] * prev_rainfall + BETA["prev_tmax"] * prev_tmax +
        BETA["prev_tmin"] * prev_tmin + BETA["rain_cum_2q"] * rain_cum_2q + u
    )
    p = 1 / (1 + 2.718281828 ** -log_odds)
    tier = classify(p)
    color = TIER_COLORS[tier]

    if region in REGIONS:
        steps = 15
        for i in range(1, steps + 1):
            progress = i / steps
            fig = base_map()
            fill_region(fig, region, color, opacity=0.15 + 0.65 * progress)
            map_slot.plotly_chart(fig, use_container_width=True, key=f"frame_{i}")
            time.sleep(0.03)
    else:
        map_slot.plotly_chart(base_map(), use_container_width=True)

    with result_slot.container():
        st.divider()
        st.metric("P(Outbreak)", f"{p*100:.1f}%")
        st.markdown(f"**Risk Tier:** {tier}")
        st.caption(TIER_ACTION[tier])
        if region in REGIONS:
            st.caption(f"Region used: {region} (u = {u:.4f})")
        else:
            st.caption("Region used: untrained, population average")
