import streamlit as st

BETA = {
    "intercept": -32.6401, "tmax": 0.2790, "tmin": -0.3650,
    "rainfall": -0.0048, "humidity": -0.0284, "prev_outbreak": 2.7233,
    "prev_rainfall": -0.0639, "prev_tmax": 0.5805, "prev_tmin": 0.5923,
    "rain_cum_2q": 0.0643,
}

REGION_U = {
    "Bicol Region": -0.2971, "Cagayan Valley": 0.2989,
    "Ilocos Region": -1.6065, "Northern Mindanao": 0.1275,
    "SOCCSKSARGEN": 0.9616, "Zamboanga Peninsula": 0.5156,
}

def classify(p):
    if p < 0.30: return "Low Risk"
    if p < 0.60: return "Moderate Risk"
    if p < 0.80: return "High Risk"
    return "Very High Risk"

st.set_page_config(page_title="FAWcast Risk Calculator")
st.title("FAWcast Outbreak-Risk Calculator")
st.caption("Hierarchical logistic regression model — Table IV & V")

region = st.selectbox("Region", ["Untrained (population average)"] + list(REGION_U.keys()))

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

u = REGION_U.get(region, 0.0)
log_odds = (
    BETA["intercept"] + BETA["tmax"]*tmax + BETA["tmin"]*tmin +
    BETA["rainfall"]*rainfall + BETA["humidity"]*humidity +
    BETA["prev_outbreak"]*(1 if prev_outbreak == "Yes" else 0) +
    BETA["prev_rainfall"]*prev_rainfall + BETA["prev_tmax"]*prev_tmax +
    BETA["prev_tmin"]*prev_tmin + BETA["rain_cum_2q"]*rain_cum_2q + u
)
p = 1 / (1 + 2.718281828 ** -log_odds)
tier = classify(p)

st.divider()
st.metric("P(Outbreak)", f"{p*100:.1f}%")
st.write(f"**Risk Tier:** {tier}")
st.caption(f"Region used: {region} (u = {u:.4f})")
