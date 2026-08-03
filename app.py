import math
import streamlit as st

BETA_0 = -6.0
BETA_1 = 0.15
BETA_2 = 0.05
BETA_3 = 0.02
BETA_4 = 0.03

RISK_TIERS = [
    (0.00, 0.30, "Low Risk", "#2e7d32", ["Continue routine field monitoring.", "Maintain standard pest management practices.", "Educate farmers on Fall Armyworm identification and reporting."]),
    (0.30, 0.60, "Moderate Risk", "#f9a825", ["Increase field inspections.", "Deploy pheromone traps for early detection.", "Prepare pest control materials and coordinate with local agricultural offices."]),
    (0.60, 0.80, "High Risk", "#ef6c00", ["Implement immediate monitoring in affected areas.", "Recommend timely Integrated Pest Management (IPM) measures.", "Advise farmers to apply appropriate control methods once infestation is confirmed."]),
    (0.80, 1.001, "Very High Risk", "#c62828", ["Issue an outbreak advisory.", "Intensify surveillance across nearby farms."]),
]

def compute_z(tmax, tmin, rainfall, humidity):
    return BETA_0 + BETA_1 * tmax + BETA_2 * tmin + BETA_3 * rainfall + BETA_4 * humidity

def compute_probability(z):
    return 1 / (1 + math.exp(-z))

def classify_risk(p):
    for low, high, label, color, actions in RISK_TIERS:
        if low <= p < high:
            return label, color, actions
    return RISK_TIERS[-1][2], RISK_TIERS[-1][3], RISK_TIERS[-1][4]

st.set_page_config(page_title="FAWcast", page_icon="corn", layout="centered")
st.title("FAWcast")
st.caption("Weather-Based Fall Armyworm Outbreak Risk Predictor for Philippine Corn")

st.warning("This app is currently running on placeholder coefficients for demonstration purposes. Predictions will not be accurate until the real fitted model coefficients are entered.")

st.subheader("Enter Weather Conditions")

col1, col2 = st.columns(2)
with col1:
    tmax = st.number_input("Maximum Temperature (C)", min_value=15.0, max_value=45.0, value=30.0, step=0.1)
    rainfall = st.number_input("Rainfall (mm/day)", min_value=0.0, max_value=500.0, value=5.0, step=0.1)
with col2:
    tmin = st.number_input("Minimum Temperature (C)", min_value=10.0, max_value=35.0, value=24.0, step=0.1)
    humidity = st.number_input("Relative Humidity (%)", min_value=0.0, max_value=100.0, value=80.0, step=0.1)

if st.button("Predict Outbreak Risk", type="primary", use_container_width=True):
    z = compute_z(tmax, tmin, rainfall, humidity)
    p = compute_probability(z)
    label, color, actions = classify_risk(p)

    st.divider()
    st.subheader("Prediction Result")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Predicted Outbreak Probability", str(round(p * 100, 1)) + "%")
    with col2:
        st.markdown("Risk Level: " + label)

    st.progress(min(max(p, 0.0), 1.0))

    st.markdown("Recommended Actions:")
    for a in actions:
        st.markdown("- " + a)

st.divider()
st.caption("Model: Logistic Regression. Data sources: NASA POWER (weather), Bureau of Plant Industry (outbreak records)")
