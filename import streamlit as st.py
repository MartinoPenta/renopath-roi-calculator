import streamlit as st

st.set_page_config(
    page_title="Renopath — Renovation ROI Calculator",
    page_icon="🏠",
    layout="centered"
)

# ── Data ──────────────────────────────────────────────────────────────────────

LOCATIONS = {
    "Copenhagen inner city (Nørrebro, Vesterbro, Østerbro)": {"base": 1.00, "density": "high"},
    "Copenhagen suburbs (Frederiksberg, Gentofte, Lyngby)":  {"base": 0.88, "density": "high"},
    "Aarhus municipality":                                    {"base": 0.72, "density": "medium"},
    "Odense / Aalborg":                                       {"base": 0.55, "density": "medium"},
    "Regional / rural Jutland":                               {"base": 0.30, "density": "low"},
}

PROPERTY_TYPES = {
    "Detached house, built before 1979":  1.10,
    "Detached house, built 1979–2000":    0.90,
    "Apartment, pre-1940 stock":          1.05,
    "Apartment, post-1940":               0.85,
}

WORKS = {
    "energy":     {"label": "Energy envelope",        "base": 0.065, "synergy": ["systems"]},
    "kitchen":    {"label": "Kitchen",                "base": 0.055, "synergy": ["interior", "bath"]},
    "bath":       {"label": "Bathroom(s)",            "base": 0.045, "synergy": ["kitchen"]},
    "systems":    {"label": "Heat pump / systems",    "base": 0.040, "synergy": ["energy"]},
    "interior":   {"label": "Interior finishes",      "base": 0.025, "synergy": ["kitchen"]},
    "structural": {"label": "Structural / extension", "base": 0.085, "synergy": []},
}

CONFIDENCE = {
    "high":   {"ci": 0.10, "note": "High data density — estimate based on 200+ comparable renovation pairs in this postcode zone."},
    "medium": {"ci": 0.14, "note": "Medium data density — estimate based on 60–120 comparable renovation pairs. Wider confidence interval."},
    "low":    {"ci": 0.18, "note": "Low data density — fewer comparable sales in this area. Treat as indicative range only."},
}

# ── UI ────────────────────────────────────────────────────────────────────────

st.markdown("## Renopath — renovation ROI calculator")
st.caption("Powered by Danish renovation-adjusted repeat sales data · Not a formal valuation")

st.divider()

col1, col2 = st.columns(2)

with col1:
    location_key = st.selectbox("Property location", list(LOCATIONS.keys()))

with col2:
    proptype_key = st.selectbox("Property type", list(PROPERTY_TYPES.keys()))

prop_val = st.slider(
    "Current market value (DKK)",
    min_value=1_500_000,
    max_value=8_000_000,
    value=3_500_000,
    step=100_000,
    format="%d"
)

st.markdown(f"**{prop_val:,.0f} DKK**", help="Your estimate of the property's current market value before renovation.")

reno_cost = st.slider(
    "Estimated renovation cost (DKK)",
    min_value=100_000,
    max_value=1_500_000,
    value=400_000,
    step=25_000,
    format="%d"
)

st.markdown(f"**{reno_cost:,.0f} DKK**")

st.markdown("**Renovation works planned**")

work_cols = st.columns(3)
selected_works = {}
work_keys = list(WORKS.keys())

for i, key in enumerate(work_keys):
    with work_cols[i % 3]:
        selected_works[key] = st.checkbox(
            WORKS[key]["label"],
            value=key in ("energy", "kitchen")
        )

# ── Calculation ───────────────────────────────────────────────────────────────

loc = LOCATIONS[location_key]
prop_mult = PROPERTY_TYPES[proptype_key]
active = [k for k, v in selected_works.items() if v]

st.divider()

if not active:
    st.info("Select at least one renovation work category above to see the estimate.")
    st.stop()

breakdown = []
total_uplift_pct = 0.0

for key in active:
    w = WORKS[key]
    pct = w["base"] * loc["base"] * prop_mult
    has_synergy = any(s in active for s in w["synergy"])
    if has_synergy:
        pct *= 1.15
    breakdown.append({
        "key": key,
        "label": w["label"],
        "pct": pct,
        "synergy": has_synergy,
    })
    total_uplift_pct += pct

total_uplift_pct = min(total_uplift_pct, 0.45)

uplift_dkk = round(prop_val * total_uplift_pct)
post_val = prop_val + uplift_dkk
net_roi = uplift_dkk - reno_cost
ci = CONFIDENCE[loc["density"]]["ci"]
low = round(post_val * (1 - ci))
high = round(post_val * (1 + ci))

# ── Output metrics ────────────────────────────────────────────────────────────

m1, m2, m3 = st.columns(3)

with m1:
    st.metric(
        label="Post-renovation value",
        value=f"{post_val:,.0f} DKK",
        delta=f"+{uplift_pct:.0f}% on current value".replace("uplift_pct", str(round(total_uplift_pct * 100)))
    )
    st.caption(f"Range: {low:,.0f} – {high:,.0f} DKK")

with m2:
    st.metric(
        label="Value uplift",
        value=f"+{uplift_dkk:,.0f} DKK",
        delta=f"+{round(total_uplift_pct * 100)}%"
    )

with m3:
    roi_sign = "+" if net_roi >= 0 else ""
    st.metric(
        label="Net ROI",
        value=f"{roi_sign}{net_roi:,.0f} DKK",
        delta="uplift minus renovation cost",
        delta_color="off"
    )

# ── Breakdown ─────────────────────────────────────────────────────────────────

st.divider()
st.markdown("**Uplift by work category**")

max_pct = max(b["pct"] for b in breakdown)

for b in breakdown:
    bar_w = b["pct"] / max(max_pct, 0.001)
    synergy_tag = " · synergy +15%" if b["synergy"] else ""
    col_a, col_b = st.columns([3, 1])
    with col_a:
        st.markdown(f"{b['label']}{synergy_tag}")
        st.progress(bar_w)
    with col_b:
        st.markdown(f"**+{round(b['pct']*100)}%**")
        st.caption(f"+{round(prop_val * b['pct']):,.0f} DKK")

# ── Confidence note ───────────────────────────────────────────────────────────

st.divider()
conf = CONFIDENCE[loc["density"]]
if loc["density"] == "high":
    st.success(f"Data confidence: {conf['note']}")
elif loc["density"] == "medium":
    st.warning(f"Data confidence: {conf['note']}")
else:
    st.error(f"Data confidence: {conf['note']}")

st.caption(
    "Estimates based on renovation-adjusted repeat sales, Danish transaction data 2010–2024. "
    "Confidence intervals ±10–18% depending on postcode data density. "
    "Not a formal valuation — for indicative purposes only."
)