import time
import math
import csv
import io
import streamlit as st
import plotly.graph_objects as go

BETA = {
    "intercept": -32.6401, "tmax": 0.2790, "tmin": -0.3650,
    "rainfall": -0.0048, "humidity": -0.0284, "prev_outbreak": 2.7233,
    "prev_rainfall": -0.0639, "prev_tmax": 0.5805, "prev_tmin": 0.5923,
    "rain_cum_2q": 0.0643,
}

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

RANGES = {
    "Max Temp (C)": (26.0, 36.0),
    "Min Temp (C)": (19.0, 27.0),
    "Rainfall (mm/day)": (0.0, 45.0),
    "Relative Humidity (%)": (65.0, 95.0),
    "Prev. Max Temp (C)": (26.0, 36.0),
    "Prev. Min Temp (C)": (19.0, 27.0),
    "Prev. Rainfall (mm/day)": (0.0, 45.0),
    "2-Qtr Cumulative Rain (mm)": (0.0, 90.0),
}


def classify(p):
    if p < 0.30: return "Low Risk"
    if p < 0.60: return "Moderate Risk"
    if p < 0.80: return "High Risk"
    return "Very High Risk"


def marker_size(area_km2):
    return 14 + 2.2 * math.sqrt(area_km2 / 1000)


MAP_WIDTH = 460
MAP_HEIGHT = 667


def base_map():
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
        showland=True, landcolor="#eee4c9",
        showocean=True, oceancolor="#bcdcea",
        showcountries=True, countrycolor="#a89a72",
        showcoastlines=True, coastlinecolor="#8a7a52", coastlinewidth=1,
        showsubunits=False,
        showframe=False,
        bgcolor="rgba(0,0,0,0)",
        resolution=50,
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=0),
        width=MAP_WIDTH,
        height=MAP_HEIGHT,
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
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


def show_map(fig, key=None):
    with map_slot.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.plotly_chart(fig, use_container_width=False, config={"displayModeBar": False}, key=key)


def legend_row():
    cols = st.columns(4)
    for col, (tier, color) in zip(cols, TIER_COLORS.items()):
        col.markdown(
            f'<div style="display:flex;align-items:center;gap:6px;font-size:12px;">'
            f'<div style="width:12px;height:12px;border-radius:50%;background:{color};"></div>'
            f'{tier}</div>',
            unsafe_allow_html=True,
        )


def check_out_of_range(values_by_label):
    flags = []
    for label, value in values_by_label.items():
        if label in RANGES:
            lo, hi = RANGES[label]
            if value < lo or value > hi:
                flags.append(f"{label} = {value} (typical range: {lo}-{hi})")
    return flags


def make_csv(rows, fieldnames):
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()


st.set_page_config(page_title="FAWcast Risk Calculator", layout="wide")

st.markdown(
    """
    <style>
    div[data-testid="stPlotlyChart"] {
        border-radius: 14px;
        overflow: hidden;
        box-shadow: 0 4px 18px rgba(43,36,24,0.18);
        border: 1px solid #d8cca3;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

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

if "history" not in st.session_state:
    st.session_state.history = []
if "last_result" not in st.session_state:
    st.session_state.last_result = None

with st.expander("About Fall Armyworm (Spodoptera frugiperda)", expanded=False):
    st.markdown(
        """
- **Identity:** *Spodoptera frugiperda*, commonly the Fall Armyworm (FAW), is a moth species (Lepidoptera: Noctuidae) native to the Americas.
- **Invasion history:** First reported outside the Americas in West Africa (2016), FAW spread rapidly across Asia. It was first validated in the Philippines in **June 2019**, initially detected in **Cagayan Valley**, one of the country's major corn-growing areas.
- **Host range:** Highly polyphagous - it can feed on many plant species - but shows a strong preference for **maize/corn**, and is also reported on rice, sorghum, and sugarcane.
- **Damage:** Larvae (caterpillars) cause the actual crop damage, feeding on leaves and the whorl, and can bore into developing ears. Adults are strong fliers capable of long-distance seasonal migration.
- **Why it spreads fast:** Short development time and high reproductive rate allow populations to build up and spread quickly once established in an area.

*Sources: Cabusas et al. (2024), Journal of Applied Entomology; Navasero & Navasero (2020), UPLB; CABI (2024).*
        """
    )

with st.expander("Preventive Measures & Integrated Pest Management (IPM)", expanded=False):
    st.markdown(
        """
Philippine agencies (DA, Bureau of Plant Industry) recommend an integrated approach - no single method is sufficient on its own:

- **Field monitoring:** Regular scouting for egg masses and early-stage larvae, and pheromone traps to track adult moth activity, so action can be taken before damage becomes severe.
- **Biological control:** Agents such as *Trichogramma* wasps (egg parasitoids), and the fungi *Metarhizium* and *Beauveria*, are produced and distributed by BPI Regional Crop Protection Centers for farmer use.
- **Cultural practices:** Early planting, proper weed management, adequate fertilization and irrigation, crop rotation, and avoiding adjacent sequential planting all reduce the conditions FAW thrives in.
- **Chemical control as a last resort:** IPM guidance treats insecticides as a final option, guided by field-assessed economic injury thresholds rather than routine spraying, to limit cost and harm to natural enemies of the pest.
- **Coordination:** Confirmed or suspected outbreaks should be reported to the local agricultural extension office or BPI Regional Crop Protection Center.

*Sources: Department of Agriculture (da.gov.ph); BPI Crop Pest Management Division; Philippine News Agency (2020).*
        """
    )

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
history_slot = st.empty()


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


def render_history():
    if not st.session_state.history:
        return
    with history_slot.container():
        st.divider()
        st.write("**Session history** (this session only, resets if the app restarts):")
        for h in reversed(st.session_state.history[-10:]):
            st.write(f"- {h['region']}: {h['probability_pct']}% ({h['tier']})")
        csv_text = make_csv(
            st.session_state.history,
            fieldnames=["region", "probability_pct", "tier", "tmax", "tmin", "rainfall",
                        "humidity", "prev_outbreak", "prev_tmax", "prev_tmin",
                        "prev_rainfall", "rain_cum_2q"],
        )
        st.download_button(
            "Download full history as CSV",
            data=csv_text,
            file_name="fawcast_history.csv",
            mime="text/csv",
        )


def run_single(region_name, animate=True):
    p, u = compute_p(region_name)
    tier = classify(p)
    color = TIER_COLORS[tier]
    base_size = marker_size(REGIONS.get(region_name, {}).get("area_km2", 18000))

    flags = check_out_of_range({
        "Max Temp (C)": tmax, "Min Temp (C)": tmin,
        "Rainfall (mm/day)": rainfall, "Relative Humidity (%)": humidity,
        "Prev. Max Temp (C)": prev_tmax, "Prev. Min Temp (C)": prev_tmin,
        "Prev. Rainfall (mm/day)": prev_rainfall, "2-Qtr Cumulative Rain (mm)": rain_cum_2q,
    })

    if region_name in REGIONS:
        if animate:
            steps = 15
            for i in range(1, steps + 1):
                progress = i / steps
                fig = base_map()
                add_region_marker(fig, region_name, size=base_size * (0.3 + 0.7 * progress), color=color, opacity=0.3 + 0.65 * progress)
                show_map(fig, key=f"frame_{i}_{time.time()}")
                time.sleep(0.03)
        else:
            fig = base_map()
            add_region_marker(fig, region_name, size=base_size, color=color, opacity=0.95)
            show_map(fig, key="single_static")
    else:
        show_map(base_map(), key="single_untrained")

    with result_slot.container():
        st.divider()
        if flags:
            st.warning(
                "Some inputs fall outside the typical range this baseline model was built on. "
                "Treat this prediction as an extrapolation, with lower confidence:\n\n"
                + "\n".join(f"- {f}" for f in flags)
            )
        st.metric("P(Outbreak)", f"{p*100:.1f}%")
        st.markdown(f"**Risk Tier:** {tier}")
        st.caption(TIER_ACTION[tier])
        if region_name in REGIONS:
            st.caption(f"Region used: {region_name} (u = {u:.4f})")
        else:
            st.caption("Region used: untrained, population average")
        record = {
            "region": region_name, "probability_pct": round(p * 100, 1), "tier": tier,
            "tmax": tmax, "tmin": tmin, "rainfall": rainfall, "humidity": humidity,
            "prev_outbreak": prev_outbreak, "prev_tmax": prev_tmax, "prev_tmin": prev_tmin,
            "prev_rainfall": prev_rainfall, "rain_cum_2q": rain_cum_2q,
        }
        csv_text = make_csv([record], fieldnames=list(record.keys()))
        st.download_button("Download this result as CSV", data=csv_text, file_name="fawcast_result.csv", mime="text/csv", key=f"dl_{time.time()}")
        return record


if calculate:
    record = run_single(region, animate=True)
    st.session_state.history.append(record)
    render_history()

elif calculate_all:
    fig = base_map()
    rows = []
    flags = check_out_of_range({
        "Max Temp (C)": tmax, "Min Temp (C)": tmin,
        "Rainfall (mm/day)": rainfall, "Relative Humidity (%)": humidity,
        "Prev. Max Temp (C)": prev_tmax, "Prev. Min Temp (C)": prev_tmin,
        "Prev. Rainfall (mm/day)": prev_rainfall, "2-Qtr Cumulative Rain (mm)": rain_cum_2q,
    })
    for name in REGIONS:
        p, u = compute_p(name)
        tier = classify(p)
        color = TIER_COLORS[tier]
        size = marker_size(REGIONS[name]["area_km2"])
        add_region_marker(fig, name, size=size, color=color, opacity=0.85)
        record = {
            "region": name, "probability_pct": round(p * 100, 1), "tier": tier,
            "tmax": tmax, "tmin": tmin, "rainfall": rainfall, "humidity": humidity,
            "prev_outbreak": prev_outbreak, "prev_tmax": prev_tmax, "prev_tmin": prev_tmin,
            "prev_rainfall": prev_rainfall, "rain_cum_2q": rain_cum_2q,
        }
        rows.append(record)
        st.session_state.history.append(record)
    show_map(fig, key="all_regions")

    with result_slot.container():
        st.divider()
        if flags:
            st.warning(
                "Some inputs fall outside the typical range this baseline model was built on. "
                "Treat these predictions as an extrapolation, with lower confidence:\n\n"
                + "\n".join(f"- {f}" for f in flags)
            )
        st.write("**Risk by region** (using the weather values entered above):")
        rows.sort(key=lambda x: x["probability_pct"], reverse=True)
        for r in rows:
            st.write(f"- {r['region']}: {r['probability_pct']}% ({r['tier']})")
        csv_text = make_csv(rows, fieldnames=list(rows[0].keys()))
        st.download_button("Download these results as CSV", data=csv_text, file_name="fawcast_all_regions.csv", mime="text/csv")

    render_history()

else:
    # Default view on first load: auto-show a colored result instead of a plain gray map
    run_single(region, animate=False)
    render_history()
