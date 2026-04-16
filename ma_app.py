"""
M&A Analysis — Interactive Streamlit Dashboard
===============================================
Run with: streamlit run ma_app.py
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="M&A Analysis",
    page_icon="🤝",
    layout="wide",
)

st.markdown("""
<style>
    .main { background-color: #0d1117; }
    .block-container { padding-top: 2rem; }
    h1, h2, h3 { color: #e6edf3; }
    .metric-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 1rem 1.5rem;
        text-align: center;
    }
    .metric-value { font-size: 1.8rem; font-weight: bold; }
    .metric-label { font-size: 0.8rem; color: #8b949e; margin-top: 4px; }
    .stSlider label, .stNumberInput label, .stSelectbox label { color: #e6edf3 !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# COLORS
# ─────────────────────────────────────────────
COLORS = {
    "bg":       "#0d1117",
    "panel":    "#161b22",
    "accent1":  "#58a6ff",
    "accent2":  "#3fb950",
    "accent3":  "#f0883e",
    "negative": "#f85149",
    "scatter":  "#30363d",
    "text":     "#e6edf3",
    "subtext":  "#8b949e",
}

# ─────────────────────────────────────────────
# SIDEBAR INPUTS
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("##  Deal Parameters")
    st.markdown("---")

    with st.expander(" Deal Terms", expanded=True):
        offer_per_share = st.number_input("Offer Price ($/share)",
                                          value=95.0, min_value=50.0, max_value=200.0, step=1.0)
        target_shares   = st.number_input("Target Shares Outstanding (M)",
                                          value=784.0, min_value=100.0, step=10.0)
        cash_pct        = st.slider("Cash Consideration (%)", 0, 100, 100) / 100
        acquirer_price  = st.number_input("Acquirer Share Price ($)",
                                          value=380.0, min_value=50.0, step=5.0)

    with st.expander(" Target Financials", expanded=False):
        revenue_y0     = st.number_input("Revenue Y0 ($M)",
                                         value=8800.0, min_value=100.0, step=100.0)
        rev_growth     = st.slider("Avg Revenue Growth (%)", 0, 25, 9) / 100
        ebitda_margin  = st.slider("EBITDA Margin (%)", 10, 60, 38) / 100
        tax_rate       = st.slider("Tax Rate (%)", 15, 35, 21) / 100
        net_debt       = st.number_input("Net Debt ($M, negative = net cash)",
                                         value=-5500.0, step=100.0)

    with st.expander(" DCF Assumptions", expanded=False):
        wacc            = st.slider("WACC (%)", 5.0, 15.0, 8.5, 0.1) / 100
        terminal_growth = st.slider("Terminal Growth (%)", 0.0, 5.0, 2.5, 0.1) / 100

    with st.expander(" Synergies", expanded=False):
        cost_syn = st.number_input("Cost Synergies ($M/yr)",
                                   value=1200.0, min_value=0.0, step=100.0)
        rev_syn  = st.number_input("Revenue Synergies ($M/yr)",
                                   value=800.0, min_value=0.0, step=100.0)

    with st.expander(" Acquirer", expanded=False):
        acq_ni    = st.number_input("Net Income ($M)", value=72000.0, step=1000.0)
        acq_shares = st.number_input("Shares Outstanding (M)", value=7430.0, step=100.0)
        interest_rate = st.slider("Cost of Debt (%)", 2.0, 10.0, 4.5, 0.1) / 100

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.markdown("# M&A Dashboard")
st.markdown("**DCF Valuation + Accretion/Dilution Model** — Microsoft / Activision Blizzard")
st.markdown("---")

# ─────────────────────────────────────────────
# CALCULATIONS
# ─────────────────────────────────────────────
stock_pct = 1 - cash_pct

# Build DCF
years         = list(range(1, 6))
growth_curve  = [rev_growth * (1 + i*0.02) for i in range(5)]   # slight ramp
revenues      = []
rev = revenue_y0
for g in growth_curve:
    rev = rev * (1 + g)
    revenues.append(rev)

phase_in      = [0.30, 0.60, 1.00, 1.00, 1.00]
syn_total_at  = [(cost_syn + rev_syn) * p * (1 - tax_rate) for p in phase_in]

df = pd.DataFrame(index=years)
df["Revenue"]   = revenues
df["EBITDA"]    = df["Revenue"] * ebitda_margin
df["D&A"]       = df["Revenue"] * 0.06
df["EBIT"]      = df["EBITDA"] - df["D&A"]
df["Taxes"]     = df["EBIT"] * tax_rate
df["NOPAT"]     = df["EBIT"] - df["Taxes"]
df["CapEx"]     = df["Revenue"] * 0.05
df["ΔNWC"]      = df["Revenue"].diff().fillna(df["Revenue"].iloc[0]) * 0.02
df["FCF"]       = df["NOPAT"] + df["D&A"] - df["CapEx"] - df["ΔNWC"]
df["Synergies"] = syn_total_at
df["FCF (incl. Syn)"] = df["FCF"] + df["Synergies"]
df["DF"]        = [(1/(1+wacc))**y for y in years]
df["PV"]        = df["FCF (incl. Syn)"] * df["DF"]

terminal_value = df["FCF (incl. Syn)"].iloc[-1] * (1 + terminal_growth) / (wacc - terminal_growth)
pv_tv          = terminal_value * df["DF"].iloc[-1]
enterprise_value = df["PV"].sum() + pv_tv
equity_value   = enterprise_value - net_debt
implied_price  = equity_value * 1e6 / (target_shares * 1e6)

# Accretion / Dilution
offer_value   = offer_per_share * target_shares           # $M
cash_portion  = offer_value * cash_pct
stock_portion = offer_value * stock_pct
new_shares    = stock_portion / acquirer_price            # millions
total_shares  = acq_shares + new_shares

target_rev_y1 = revenue_y0 * (1 + rev_growth)
target_ebitda = target_rev_y1 * ebitda_margin
target_ebit   = target_ebitda - target_rev_y1 * 0.06
target_ni     = target_ebit * (1 - tax_rate)

syn_y1_at     = (cost_syn + rev_syn) * 0.30 * (1 - tax_rate)
interest_at   = cash_portion * interest_rate * (1 - tax_rate)
combined_ni   = acq_ni + target_ni + syn_y1_at - interest_at

standalone_eps = acq_ni / acq_shares
proforma_eps   = combined_ni / total_shares
accretion_pct  = (proforma_eps / standalone_eps - 1) * 100

premium_vs_dcf = (offer_per_share / implied_price - 1) * 100

# ─────────────────────────────────────────────
# KEY METRICS
# ─────────────────────────────────────────────
st.markdown("### Key Metrics")
c1, c2, c3, c4, c5 = st.columns(5)

def metric_card(col, label, value, color):
    col.markdown(f"""
    <div class="metric-card">
        <div class="metric-value" style="color:{color}">{value}</div>
        <div class="metric-label">{label}</div>
    </div>""", unsafe_allow_html=True)

metric_card(c1, "Deal Value", f"${offer_value/1000:.1f}B", COLORS["accent1"])
metric_card(c2, "DCF Implied Price", f"${implied_price:.2f}", COLORS["accent3"])
metric_card(c3, "Offer Price", f"${offer_per_share:.2f}", COLORS["accent1"])
color_prem = COLORS["negative"] if premium_vs_dcf > 0 else COLORS["accent2"]
metric_card(c4, "Premium vs DCF", f"{premium_vs_dcf:+.1f}%", color_prem)
color_acc = COLORS["accent2"] if accretion_pct >= 0 else COLORS["negative"]
metric_card(c5, "EPS Accretion", f"{accretion_pct:+.2f}%", color_acc)

st.markdown("---")

# ─────────────────────────────────────────────
# PLOTS
# ─────────────────────────────────────────────
def style_ax(ax):
    ax.set_facecolor(COLORS["panel"])
    for spine in ax.spines.values():
        spine.set_edgecolor(COLORS["scatter"])
    ax.tick_params(colors=COLORS["subtext"])
    ax.grid(axis="y", color=COLORS["scatter"], alpha=0.4, linewidth=0.5)

col1, col2 = st.columns(2)

with col1:
    st.markdown("####  Free Cash Flow Projection")
    fig, ax = plt.subplots(figsize=(6, 4), facecolor=COLORS["bg"])
    style_ax(ax)
    ax.bar(years, df["FCF"], color=COLORS["accent1"], edgecolor="none",
           width=0.55, label="Base FCF")
    ax.bar(years, df["Synergies"], bottom=df["FCF"],
           color=COLORS["accent2"], edgecolor="none",
           width=0.55, label="Synergies (AT)")
    for y, v in zip(years, df["FCF (incl. Syn)"]):
        ax.text(y, v + 80, f"${v/1000:.1f}B", ha="center",
                color=COLORS["text"], fontsize=8)
    ax.set_xlabel("Year", color=COLORS["subtext"], fontsize=9)
    ax.set_ylabel("FCF ($M)", color=COLORS["subtext"], fontsize=9)
    ax.legend(facecolor=COLORS["bg"], edgecolor=COLORS["scatter"],
              labelcolor=COLORS["text"], fontsize=8)
    plt.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close()

with col2:
    st.markdown("####  EPS Impact — Accretion/Dilution")
    fig, ax = plt.subplots(figsize=(6, 4), facecolor=COLORS["bg"])
    style_ax(ax)
    is_acc = accretion_pct >= 0
    color_eps = COLORS["accent2"] if is_acc else COLORS["negative"]
    bars = ax.bar(["Standalone EPS", "Pro-Forma EPS"],
                  [standalone_eps, proforma_eps],
                  color=[COLORS["accent1"], color_eps],
                  edgecolor="none", width=0.55)
    for bar, val in zip(bars, [standalone_eps, proforma_eps]):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.15,
                f"${val:.2f}", ha="center", color=COLORS["text"],
                fontsize=11, fontweight="bold")
    tag = "ACCRETIVE" if is_acc else "DILUTIVE"
    ax.text(0.5, max(standalone_eps, proforma_eps) * 1.18,
            f"{tag}  {accretion_pct:+.2f}%",
            ha="center", color=color_eps, fontsize=13, fontweight="bold",
            transform=ax.transData)
    ax.set_ylim(0, max(standalone_eps, proforma_eps) * 1.35)
    ax.set_ylabel("EPS ($)", color=COLORS["subtext"], fontsize=9)
    plt.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close()

st.markdown("---")

col3, col4 = st.columns(2)

with col3:
    st.markdown("####  Valuation Bridge")
    fig, ax = plt.subplots(figsize=(6, 4), facecolor=COLORS["bg"])
    style_ax(ax)
    labels = ["PV of\nFCF", "PV of\nTerminal", "Enterprise\nValue", "(–) Net\nDebt", "Equity\nValue"]
    values = [df["PV"].sum(), pv_tv, enterprise_value, -net_debt, equity_value]
    bar_cols = [COLORS["accent1"], COLORS["accent1"], COLORS["accent3"],
                COLORS["accent2"], COLORS["accent3"]]
    bars = ax.bar(range(len(labels)), [v/1000 for v in values],
                  color=bar_cols, edgecolor="none", width=0.6)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                f"${val/1000:.1f}B", ha="center",
                color=COLORS["text"], fontsize=9)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, color=COLORS["subtext"], fontsize=8)
    ax.set_ylabel("Value ($B)", color=COLORS["subtext"], fontsize=9)
    ax.axhline(y=offer_value/1000, color=COLORS["negative"], linestyle="--",
               linewidth=1.2, alpha=0.8)
    ax.text(len(labels) - 0.5, offer_value/1000 + 2,
            f"Offer: ${offer_value/1000:.1f}B",
            color=COLORS["negative"], fontsize=8, ha="right")
    plt.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close()

with col4:
    st.markdown("####  Deal Consideration Mix")
    fig, ax = plt.subplots(figsize=(6, 4), facecolor=COLORS["bg"])
    ax.set_facecolor(COLORS["panel"])
    mix = [(cash_pct, "Cash", COLORS["accent2"]),
           (stock_pct, "Stock", COLORS["accent1"])]
    mix = [m for m in mix if m[0] > 0]
    vals, lbls, cols = zip(*mix)
    wedges, texts, autotexts = ax.pie(
        vals, labels=lbls, colors=cols, autopct="%.0f%%",
        startangle=90,
        textprops={"color": COLORS["text"], "fontsize": 11},
        wedgeprops={"edgecolor": COLORS["bg"], "linewidth": 2})
    for t in autotexts:
        t.set_color("black")
        t.set_fontweight("bold")
    ax.set_title(f"${offer_value/1000:.1f}B Total Deal Value",
                 color=COLORS["text"], fontsize=11, pad=8)
    plt.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close()

st.markdown("---")

# ─────────────────────────────────────────────
# SENSITIVITY TABLE
# ─────────────────────────────────────────────
st.markdown("####  Sensitivity Analysis — Implied Price ($/share)")
waccs    = np.arange(0.065, 0.115, 0.005)
t_growths = np.arange(0.010, 0.045, 0.005)
sens = np.zeros((len(waccs), len(t_growths)))

for i, w in enumerate(waccs):
    for j, g in enumerate(t_growths):
        dfs = [(1/(1+w))**y for y in years]
        pv_ = sum(df["FCF (incl. Syn)"].values * dfs)
        tv_ = df["FCF (incl. Syn)"].iloc[-1] * (1+g) / (w - g)
        ev_ = pv_ + tv_ * dfs[-1]
        eq_ = ev_ - net_debt
        sens[i, j] = eq_ * 1e6 / (target_shares * 1e6)

sens_df = pd.DataFrame(sens,
                       index=[f"{w*100:.1f}%" for w in waccs],
                       columns=[f"{g*100:.1f}%" for g in t_growths])

st.dataframe(
    sens_df.style.background_gradient(cmap="RdYlGn", axis=None).format("${:.2f}"),
    use_container_width=True,
)
st.caption("Rows: WACC · Columns: Terminal Growth Rate")

# ─────────────────────────────────────────────
# DCF TABLE
# ─────────────────────────────────────────────
with st.expander(" Full DCF Table"):
    display_df = df[["Revenue", "EBITDA", "EBIT", "NOPAT", "CapEx",
                     "FCF", "Synergies", "FCF (incl. Syn)", "PV"]].round(1)
    st.dataframe(display_df, use_container_width=True)

# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<p style='text-align:center;color:#8b949e;font-size:0.8rem'>"
    "⚠️ Educational model based on public estimates. Not investment advice."
    "</p>", unsafe_allow_html=True
)