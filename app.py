import time
import streamlit as st
import plotly.graph_objects as go
import requests

BETA = {
    "intercept": -32.6401, "tmax": 0.2790, "tmin": -0.3650,
    "rainfall": -0.0048, "humidity": -0.0284, "prev_outbreak": 2.7233,
    "prev_rainfall": -0.0639, "prev_tmax": 0.5805, "prev_tmin": 0.5923,
    "rain_cum_2q": 0.0643,
}

# Region random intercepts (Table V). Real boundary shapes are fetched at
# runtime and matched to these names by substring match against the
# "adm1_en" property in the source data (e.g. "Region I (Ilocos Region)").
REGIONS = {
    "Bicol Region":          {"u": -0.2971},
    "Cagayan Valley":        {"u":  0.2989},
    "Ilocos Region":         {"u": -1.6065},
    "Northern Mindanao":     {"u":  0.1275},
    "SOCCSKSARGEN":          {"u":  0.9616},
    "Zamboanga Peninsula":   {"u":  0.5156},
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

GEOJSON_URL = "https://raw.githubusercontent.com/faeldon/philippines-json-maps/master/2023/geojson/country/lowres/country.0.001.json"


def classify(p):
    if p < 0.30: return "Low Risk"
    if p < 0.60: return "Moderate Risk"
    if p < 0.80: return "High Risk"
    return "Very High Risk"


@st.cache_data(ttl=86400)
def load_region_shapes():
    """Fetches the real Philippine region boundaries and matches each of
    our 6 study regions to its feature by name. Returns a dict:
    short_name -> (geojson_feature, feature_id)."""
    resp = requests.get(GEOJSON_URL, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    matches = {}
    for feature in data["features"]:
        name_en = feature.get("properties", {}).get("adm1_en", "")
        for short_name in REGIONS:
            if short_name.lower() in name_en.lower():
                matches[short_name] = (feature, feature.get("id"))
    return matches


def make_choropleth(shapes, highlighted=None, color=None, opacity=1.0):
    """Draws all 6 regions. Regions in `highlighted` (a list of names) are
    filled with `color`; all others are drawn in a neutral gray outline."""
    highlighted = highlighted or []
    fig = go.Figure()

    for name, (feature, fid) in shapes.items():
        is_highlighted = name in highlighted
        fig.add_trace(go.Choropleth(
            geojson={"type": "FeatureCollection", "features": [feature]},
            locations=[fid],
            z=[1],
            colorscale=[[0, color if is_highlighted else "#c9bb8a"], [1, color if is_highlighted else "#c9bb8a"]],
            showscale=False,
            marker_line_color="#2b2418" if is_highlighted else "#5c4f2f",
            marker_line_width=1.5 if is_highlighted else 1.0,
            marker_opacity=opacity if is_highlighted else 0.85,
            hoverinfo="skip",
        ))

    fig.update_geos(
        scope="asia",
        lataxis_range=[4, 21],
        lonaxis_range=[116, 128],
        showland=False,
        showocean=False,
        showcountries=False,
        showcoastlines=False,
        showframe=False,
        bgcolor="rgba(0,0,0,0)",
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=0),
        width=460,
        height=667,
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def show_map(fig, key=None):
    with map_slot.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.plotly_chart(fig, use_container_width=False, config={"displayModeBar": False}, key=key)


st.set_page_config(page_title="FAWcast Risk Calculator", layout="wide")

st.markdown(
    """
    <div style="background:linear-gradient(135deg,#2f4d3a,#1f3527);padding:28px 24px;border-radius:8px;margin-bottom:18px;">
        <div style="color:#c9dfc0;font-size:13px;letter-spacing:0.08em;text-transform:uppercase;">Fall Armyworm Early Warning</div>
        <div style="color:#ffffff;font-size:32px;font-weight:700;margin-top:4px;">FAWcast Outbreak-Risk Calculator</div>
        <div style="color:#d7e6d0;font-size:14px;margin-top:6px;">Hierarchical logistic regression model - Table IV & V</div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.expander("About Fall Armyworm (Spodoptera frugiperda)", expanded=False):
    st.markdown(
        """
- **Identity:** *Spodoptera frugiperda*, commonly the Fall Armyworm (FAW), is a moth species (Lepidoptera: Noctuidae) native to the Americas.
- **Invasion history:** First reported outside the Americas in West Africa (2016), FAW spread rapidly across Asia. It was first validated in the Philippines in **June 2019**, initially detected in **Cagayan Valley**, one of the country's major corn-growing areas.
- **Host range:** Highly polyphagous, but shows a strong preference for **maize/corn**, and is also reported on rice, sorghum, and sugarcane.
- **Damage:** Larvae cause the actual crop damage, feeding on leaves and the whorl, and can bore into developing ears.

*Sources: Cabusas et al. (2024); Navasero & Navasero (2020), UPLB; CABI (2024).*
        """
    )

with st.expander("Preventive Measures & Integrated Pest Management (IPM)", expanded=False):
    st.markdown(
        """
- **Field monitoring:** Regular scouting for egg masses and early-stage larvae, plus pheromone traps to track adult moth activity.
- **Biological control:** *Trichogramma* wasps and the fungi *Metarhizium* and *Beauveria*, distributed by BPI Regional Crop Protection Centers.
- **Cultural practices:** Early planting, weed management, adequate fertilization/irrigation, crop rotation.
- **Chemical control as a last resort:** guided by field-assessed economic injury thresholds, not routine spraying.
- **Coordination:** report confirmed or suspected outbreaks to the local agricultural extension office.

*Sources: Department of Agriculture (da.gov.ph); BPI Crop Pest Management Division.*
        """
    )

if "history" not in st.session_state:
    st.session_state.history = []

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

try:
    shapes = load_region_shapes()
    map_load_error = None
except Exception as e:
    shapes = {}
    map_load_error = str(e)

if map_load_error:
    st.error(f"Could not load region boundaries: {map_load_error}")
else:
    show_map(make_choropleth(shapes), key="initial")


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


if calculate and not map_load_error:
    p, u = compute_p(region)
    tier = classify(p)
    color = TIER_COLORS[tier]

    if region in shapes:
        steps = 12
        for i in range(1, steps + 1):
            progress = i / steps
            fig = make_choropleth(shapes, highlighted=[region], color=color, opacity=0.25 + 0.7 * progress)
            show_map(fig, key=f"frame_{i}_{time.time()}")
            time.sleep(0.04)
    else:
        show_map(make_choropleth(shapes), key="untrained")

    with result_slot.container():
        st.divider()
        st.metric("P(Outbreak)", f"{p*100:.1f}%")
        st.markdown(f"**Risk Tier:** {tier}")
        st.caption(TIER_ACTION[tier])
        if region in REGIONS:
            st.caption(f"Region used: {region} (u = {u:.4f})")
        else:
            st.caption("Region used: untrained, population average")

    st.session_state.history.append({"region": region, "probability_pct": round(p * 100, 1), "tier": tier})

if st.session_state.history:
    st.divider()
    st.write("**Session history:**")
    for h in reversed(st.session_state.history[-10:]):
        st.write(f"- {h['region']}: {h['probability_pct']}% ({h['tier']})")
