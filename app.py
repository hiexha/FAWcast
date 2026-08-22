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
# land area in sq km (used to size each region's marker proportionally)
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


def marker_size(area_km2):
    """Converts real land area into a reasonable on-screen marker size (px)."""
    return 14 + 2.2 * math.sqrt(area_km2 / 1000)


def base_map():
    """Draws the Philippines only, with all 6 regions as small labeled gray markers."""
    lats = [v["lat"] for v in REGIONS.values()]
    lons = [v["lon"] for v in REGIONS.values()]
    names = list(REGIONS.keys())
    sizes = [marker_size(v["area_km2"]) for v in REGIONS.values()]

    fig = go.Figure(go.Scattergeo(
        lat=lats, lon=lons,
        text=names,
        mode="markers+text",
        textposition="top center",
        textfont=dict(size=10, color="#4a4030"),
        marker=dict(size=sizes, color="#c9c2ab", opacity=0.7, line=dict(width=1.3, color="#6b5f4a")),
        hoverinfo="text",
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
        margin=dict(l=0, r=0, t=10, b=0),
        height=520,
        showlegend=False,
    )
    return fig


def add_region_marker(fig, region_name, size, color, opacity):
    r = REGIONS[region_name]
    fig.add_trace(go.Scattergeo(
        lat=[r["lat"]], lon=[r["lon"]],
        mode="markers",
        marker=dict(size=size, color=color, opacity=opacity, line=dict(width=2, color="#2b2418")),
        hoverinfo="skip",
        showlegend=False,
    ))
    return fig


def legend_row():
    cols = st.columns(4)
    for col, (tier, color) in zip(cols, TIER_COLORS.items()):
        col.markdown(
            f'<div style="display:flex;align-items:center;gap:6px;font-size:12px;">'
            f'<div style="width:12px;height:12px;border-radius:50%;background:{color};"></div>'
            f'{tier}</div>',
            unsafe_allow_html=True,
        )


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

col_a, col_b = st.columns(2)
calculate = col_a.button("Calculate Risk (selected region)", type="primary")
calculate_all = col_b.button("Show Risk for All Regions")

st.caption("Legend:")
legend_row()

map_slot = st.empty()
result_slot = st.empty()

map_slot.plotly_chart(base_map(), use_container_width=True)


def compute_p(region_name):
    u = REGIONS.get(region_name, {}).get("u", 0.0)
    log_odds = (
        BETA["intercept"] + BETA["tmax"] * tmax + BETA["tmin"] * tmin +
        BETA["rainfall"] * rainfall + BETA["humidity"] * humidity +
        BETA["prev_outbreak"] * (1 if prev_outbreak == "Yes" else 0) +
        BETA["prev_rainfall"] * prev_rainfall + BETA["prev_tmax"] * prev_tmax +
        BETA["prev_tmin"] * prev_tmin + BETA["rain_cum_2q"] * rain_cum_2q + u
    )
    return 1 / (1 + 2.718281828 ** -log_odds), u


if calculate:
    p, u = compute_p(region)
    tier = classify(p)
    color = TIER_COLORS[tier]
    base_size = marker_size(REGIONS.get(region, {}).get("area_km2", 18000))

    if region in REGIONS:
        steps = 15
        for i in range(1, steps + 1):
            progress = i / steps
            fig = base_map()
            add_region_marker(fig, region, size=base_size * (0.3 + 0.7 * progress), color=color, opacity=0.3 + 0.65 * progress)
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

elif calculate_all:
    fig = base_map()
    rows = []
    for name in REGIONS:
        p, u = compute_p(name)
        tier = classify(p)
        color = TIER_COLORS[tier]
        size = marker_size(REGIONS[name]["area_km2"])
        add_region_marker(fig, name, size=size, color=color, opacity=0.85)
        rows.append((name, p, tier))
    map_slot.plotly_chart(fig, use_container_width=True)

    with result_slot.container():
        st.divider()
        st.write("**Risk by region** (using the weather values entered above):")
        rows.sort(key=lambda x: x[1], reverse=True)
        for name, p, tier in rows:
            st.write(f"- {name}: {p*100:.1f}% ({tier})")
