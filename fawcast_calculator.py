"""
FAWcast Outbreak-Risk Calculator
--------------------------------
Implements Equation (1) of the FAWcast study: a hierarchical (mixed-effects)
logistic regression predicting Fall Armyworm outbreak probability from
same-quarter weather, previous-quarter weather, previous-quarter outbreak
status, and a region-level random intercept.

Coefficients are the fixed effects fitted via PQL, as reported in Table IV.
Region random intercepts are as reported in Table V. A region with no
training data uses u = 0 (the population-level average), per the paper's
own stated convention for untrained regions.

Usage (CLI):
    python fawcast_calculator.py

Usage (as a module):
    from fawcast_calculator import predict_outbreak_probability
    result = predict_outbreak_probability(
        tmax=31.5, tmin=23.2, rainfall=21.6, humidity=82.8,
        prev_outbreak=1, prev_rainfall=21.6, prev_tmax=31.5, prev_tmin=23.2,
        rain_cum_2q=43.2, region="SOCCSKSARGEN",
    )
"""

import math

# ---------------------------------------------------------------------------
# Fixed-effect coefficients (Table IV)
# ---------------------------------------------------------------------------
BETA = {
    "intercept": -32.6401,       # beta_0
    "tmax": 0.2790,               # beta_1  Maximum Temperature
    "tmin": -0.3650,              # beta_2  Minimum Temperature
    "rainfall": -0.0048,          # beta_3  Rainfall
    "humidity": -0.0284,          # beta_4  Relative Humidity
    "prev_outbreak": 2.7233,      # beta_5  Previous-Quarter Outbreak Status
    "prev_rainfall": -0.0639,     # beta_6  Previous-Quarter Rainfall
    "prev_tmax": 0.5805,          # beta_7  Previous-Quarter Max. Temperature
    "prev_tmin": 0.5923,          # beta_8  Previous-Quarter Min. Temperature
    "rain_cum_2q": 0.0643,        # beta_9  Two-Quarter Cumulative Rainfall
}

# ---------------------------------------------------------------------------
# Region-level random intercepts (Table V)
# Regions not listed here (no training data) use u = 0, the population
# average, per the paper's stated handling of untrained regions.
# ---------------------------------------------------------------------------
REGION_RANDOM_INTERCEPT = {
    "Bicol Region": -0.2971,
    "Cagayan Valley": 0.2989,
    "Ilocos Region": -1.6065,
    "Northern Mindanao": 0.1275,
    "SOCCSKSARGEN": 0.9616,
    "Zamboanga Peninsula": 0.5156,
}

# ---------------------------------------------------------------------------
# Four-tier risk classification (Framework section)
# ---------------------------------------------------------------------------
RISK_TIERS = [
    (0.00, 0.30, "Low Risk"),
    (0.30, 0.60, "Moderate Risk"),
    (0.60, 0.80, "High Risk"),
    (0.80, 1.0001, "Very High Risk"),  # upper bound inclusive of 1.00
]


def classify_risk(p: float) -> str:
    for lower, upper, label in RISK_TIERS:
        if lower <= p < upper:
            return label
    return "Very High Risk"  # p == 1.00 edge case


def predict_outbreak_probability(
    tmax: float,
    tmin: float,
    rainfall: float,
    humidity: float,
    prev_outbreak: int,
    prev_rainfall: float,
    prev_tmax: float,
    prev_tmin: float,
    rain_cum_2q: float,
    region: str = None,
) -> dict:
    """
    Computes P(Y=1) for a given region-quarter using the fitted FAWcast
    hierarchical logistic regression model (Equation 1, Table IV).

    prev_outbreak must be 0 or 1.
    region: one of REGION_RANDOM_INTERCEPT's keys, or None/unrecognized for
    an untrained region (random intercept defaults to 0).
    """
    if prev_outbreak not in (0, 1):
        raise ValueError("prev_outbreak must be 0 or 1")

    u = REGION_RANDOM_INTERCEPT.get(region, 0.0)
    is_trained_region = region in REGION_RANDOM_INTERCEPT

    log_odds = (
        BETA["intercept"]
        + BETA["tmax"] * tmax
        + BETA["tmin"] * tmin
        + BETA["rainfall"] * rainfall
        + BETA["humidity"] * humidity
        + BETA["prev_outbreak"] * prev_outbreak
        + BETA["prev_rainfall"] * prev_rainfall
        + BETA["prev_tmax"] * prev_tmax
        + BETA["prev_tmin"] * prev_tmin
        + BETA["rain_cum_2q"] * rain_cum_2q
        + u
    )
    p = 1 / (1 + math.exp(-log_odds))

    return {
        "probability": p,
        "probability_pct": round(p * 100, 1),
        "risk_tier": classify_risk(p),
        "region": region if is_trained_region else (region or "Unspecified") + " (untrained — using population average)",
        "random_intercept_used": u,
    }


def _prompt_float(label: str) -> float:
    while True:
        try:
            return float(input(f"{label}: ").strip())
        except ValueError:
            print("  Please enter a number.")


def _prompt_binary(label: str) -> int:
    while True:
        raw = input(f"{label} (0 = No, 1 = Yes): ").strip()
        if raw in ("0", "1"):
            return int(raw)
        print("  Please enter 0 or 1.")


def run_cli():
    print("=" * 60)
    print("FAWcast Outbreak-Risk Calculator")
    print("=" * 60)
    print(f"Trained regions: {', '.join(REGION_RANDOM_INTERCEPT)}")
    region = input("Region (leave blank if untrained/unlisted): ").strip() or None

    tmax = _prompt_float("Maximum Temperature (°C)")
    tmin = _prompt_float("Minimum Temperature (°C)")
    rainfall = _prompt_float("Rainfall (mm/day)")
    humidity = _prompt_float("Relative Humidity (%)")
    prev_outbreak = _prompt_binary("Previous-Quarter Outbreak Status")
    prev_rainfall = _prompt_float("Previous-Quarter Rainfall (mm/day)")
    prev_tmax = _prompt_float("Previous-Quarter Maximum Temperature (°C)")
    prev_tmin = _prompt_float("Previous-Quarter Minimum Temperature (°C)")
    rain_cum_2q = _prompt_float("Two-Quarter Cumulative Rainfall (mm)")

    result = predict_outbreak_probability(
        tmax=tmax, tmin=tmin, rainfall=rainfall, humidity=humidity,
        prev_outbreak=prev_outbreak, prev_rainfall=prev_rainfall,
        prev_tmax=prev_tmax, prev_tmin=prev_tmin, rain_cum_2q=rain_cum_2q,
        region=region,
    )

    print("-" * 60)
    print(f"Region used:          {result['region']}")
    print(f"P(Outbreak) = {result['probability_pct']}%")
    print(f"Risk Tier:            {result['risk_tier']}")
    print("-" * 60)


if __name__ == "__main__":
    run_cli()
