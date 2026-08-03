"""
FAWcast — Fall Armyworm Outbreak Risk Predictor
=================================================
"""

import math
import streamlit as st

# ============================================================
# CONFIG — REPLACE THESE WITH YOUR REAL FITTED COEFFICIENTS
# ============================================================
BETA_0 = -6.0    # Intercept (β0)          <-- placeholder
BETA_1 = 0.15    # Maximum Temperature (β1) <-- placeholder
BETA_2 = 0.05    # Minimum Temperature (β2) <-- placeholder
BETA_3 = 0.02    # Rainfall (β3)            <-- placeholder
BETA_4 = 0.03    # Relative Humidity (β4)   <-- placeholder

RISK_TIERS = [
    (0.00, 0.30, "Low Risk", "#2e7d32",
        ["Continue routine field monitoring.",
         "Maintain standard pest management practices.",
         "Educate farmers on Fall Armyworm identification and reporting."]),
    (0.30, 0.60, "Moderate Risk", "#f9a825",
        ["Increase field inspections.",
         "Deploy pheromone traps for early detection.",
         "Prepare pest control materials and coordinate with local agricultural offices."]),
    (0.60, 0.80, "High Risk", "#ef6c00",
        ["Implement immediate monitoring in affected areas.",
         "Recommend timely Integrated Pest Management (IPM) measures.",
         "Advise farmers to apply appropriate control methods once infestation is confirmed."]),
    (0.80, 1.001, "Very High Risk", "#c62828",
        ["Issue an outbreak advisory.",
         "Intensify surveillance across nearby farms."]),
]


def compute_z(tmax, tmin, rainfall, humidity):
    return (BETA_0 + BETA_1*tmax + BETA_2*tmin + BETA_3*rainfall + BETA_4*humidity)


def compute_probability(z):
    return 1 / (1 + math.exp(-z))


def classify_risk(p):
    for low, high, label, color, actions in RISK_TIERS:
        if low <= p < high:
            return label, color, actions
    return RISK_TIERS[-1][2], RISK_TIERS[-1][3], RISK_TIERS[-1][4]


st.set_page_config(page_title="FAWcast", page_icon="🌽", layout="centered")
st.title("🌽 FAWcast")
st.caption("Weather-Based Fall Armyworm Outbreak Risk Predictor for Philippine Corn")

st.warning(
    "⚠️ This app is currently running on **placeholder coefficients** for "
    "demonstration purposes. Predictions will not be accurate until the "
    "real fitted model coefficients are entered in the CONFIG section.",
    icon="⚠️",
)

st.subheader("Enter Weather Conditions")

col1, col2 = st.columns(2)
with col1:
    tmax = st.number_input("Maximum Temperature (°C)", min_value=15.0, max_value=45.0, value=30.0, step=0.1)
    rainfall = st.number_input("Rainfall (mm/day)", min_value=0.0, max_value=500.0, value=5.0, step=0.1)
with col2:
    tmin = st.number_input("Minimum Temperature (°C)", min_value=10.0, max_value=35.0, value=24.0, step=0.1)
    humidity = st.number_input("Relative Humidity (%)", min_value=0.0, max_value=100.0, value=80.0, step=0.1)

if st.button("Predict Outbreak Risk", type="primary", use_container_width=True):
    z = compute_z(tmax, tmin, rainfall, humidity)
    p = compute_probability(z)
    label, color, actions = classify_risk(p)

    st.divider()
    st.subheader("Prediction Result")

    c1, c2 = st.columns(2)
    with c1:
        st.metric("Predicted Outbreak Probability", f"{p:.1%}")
    with c2:
        st.markdown(
            f"<div style='padding:0.6em;border-radius:8px;background-color:{color};"
            f"color:white;text-align:center;font-weight:bold;font-size:1.1em;'>{label}</div>",
            unsafe_allow_html=True,
        )

    st.progress(min(max(p, 0.0), 1.0))

    st.markdown("**Recommended Actions:**")
    for a in actions:
        st.markdown(f"- {a}")

    with st.expander("See calculation details"):
        st.code(
            f"z = {BETA_0} + ({BETA_1})({tmax}) + ({BETA_2})({tmin}) "
            f"+ ({BETA_3})({rainfall}) + ({BETA_4})({humidity})\n"
            f"z = {z:.4f}\n"
            f"P(Y=1) = 1 / (1 + e^-z) = {p:.4f}",
            language="text",
        )

st.divider()
st.caption(
    "Model: Logistic Regression | Variables: Max/Min Temperature, Rainfall, "
    "Relative Humidity | Data sources: NASA POWER (weather), Bureau of Plant "
    "Industry (outbreak records)"
