import time
import streamlit as st
import plotly.graph_objects as go

BETA = {
    "intercept": -32.6401, "tmax": 0.2790, "tmin": -0.3650,
    "rainfall": -0.0048, "humidity": -0.0284, "prev_outbreak": 2.7233,
    "prev_rainfall": -0.0639, "prev_tmax": 0.5805, "prev_tmin": 0.5923,
    "rain_cum_2q": 0.0643,
}

# Region random intercepts (Table V) + approximate centroid coordinates
REGIONS = {
    "Bicol Region":          {"u": -0.2971, "lat": 13.42, "lon": 123.41},
    "Cagayan Valley":        {"u":  0.2989, "lat": 17.61, "lon": 121.73},
    "Ilocos Region":         {"u": -1.6065, "lat": 16.08, "lon": 120.62},
    "Northern Mindanao":     {"u":  0.1275, "lat":  8.15, "lon": 124.24},
    "SOCCSKSARGEN":          {"u":  0.9616, "lat":  6.30, "lon": 124.85},
    "Zamboanga Peninsula":   {"u":  0.5156, "lat":  7.84, "lon": 122.27},
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


def base_map():
    """Draws all 6 regions as small, dim gray markers for context."""
    lats = [v["lat"] for v in REGIONS.values()]
    lons = [v["lon"] for v in REGIONS.values()]
    names = list(REGIONS.keys())

    fig = go.Figure(go.Scattergeo(
        lat=lats, lon=lons, text=names,
        mode="markers",
        marker=dict(size=8, color="#9a9a9a", opacity=0.5),
        hoverinfo="text",
    ))
    fig.update_geos(
        scope="asia",
        center=dict(lat=12.5, lon=122.5),
        projection_scale=6,
        showland=True, landcolor="#f0ead9",
        showocean=True, oceancolor="#dce8ec",
        showcountries=True, countrycolor="#b5aa8f",
        showcoastlines=True, coastlinecolor="#b5aa8f",
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        height=420,
        showlegend=False,
    )
    return fig


def add_region_marker(fig, region_name, size, color, opacity):
    r = REGIONS[region_name]
    fig.add_trace(go.Scattergeo(
        lat=[r["lat"]], lon=[r["lon"]],
        mode="markers",
        marker=dict(size=size, color=color, opacity=opacity, line=dict(width=1, color="#2b2418")),
        hoverinfo="skip",
        showlegend=False,
    ))
    return fig


st.set_page_config(page_title="FAWcast Risk Calculator", layout="wide")
st.title("FAWcast Outbreak-Risk Calculator")
st.caption("Hierarchical logistic regression model — Table IV & V")

region = st.selectbox("Region", list(REGIONS.keys()) + ["Untrained (population average)"])

st.subheader("Same-quarter weather")
c1, c2 = st.columns(2)
tmax = c1.number_input("Max Temp (°C)", value=31.5)
tmin = c2.number_input("Min Temp (°C)", value=23.2)
rainfall = c1.number_input("Rainfall (mm/day)", value=21.6)
humidity = c2.number_input("Relative Humidity (%)", value=82.8)

st.subheader("Previous quarter")
prev_outbreak = st.radio("Outbreak occurred?", ["No", "Yes"], index=1)
c3, c4 = st.columns(2)
prev_tmax = c3.number_input("Prev. Max Temp (°C)", value=31.5)
prev_tmin = c4.number_input("Prev. Min Temp (°C)", value=23.2)
prev_rainfall = c3.number_input("Prev. Rainfall (mm/day)", value=21.6)
rain_cum_2q = c4.number_input("2-Qtr Cumulative Rain (mm)", value=43.2)

calculate = st.button("Calculate Risk", type="primary")

map_slot = st.empty()
result_slot = st.empty()

# Show a plain, unfilled map before the first calculation
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
    target_size = 14 + 46 * p  # bigger marker = higher risk

    if region in REGIONS:
        # Animate: marker grows and darkens from empty to full risk color
        steps = 18
        for i in range(1, steps + 1):
            progress = i / steps
            fig = base_map()
            add_region_marker(
                fig, region,
                size=6 + (target_size - 6) * progress,
                color=color,
                opacity=0.25 + 0.65 * progress,
            )
            map_slot.plotly_chart(fig, use_container_width=True, key=f"frame_{i}")
            time.sleep(0.03)
    else:
        map_slot.plotly_chart(base_map(), use_container_width=True)

    with result_slot.container():
        st.divider()
        st.metric("P(Outbreak)", f"{p*100:.1f}%")
        st.markdown(f"**Risk Tier:** :orange[{tier}]" if tier in ("Moderate Risk", "High Risk") else f"**Risk Tier:** {tier}")
        st.caption(TIER_ACTION[tier])
        st.caption(f"Region used: {region} (u = {u:.4f})") if region in REGIONS else None
