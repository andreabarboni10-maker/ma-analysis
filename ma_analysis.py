"""
M&A Analysis — DCF Valuation + Accretion/Dilution Model
========================================================
Deal: Microsoft Corporation (MSFT) acquires Activision Blizzard (ATVI)
Announced: January 2022 | Closed: October 2023 | Value: ~$68.7B
Author: Andrea Barboni
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.patches import FancyBboxPatch
import warnings
warnings.filterwarnings("ignore")

# ═════════════════════════════════════════════
# DEAL ASSUMPTIONS (based on public filings)
# ═════════════════════════════════════════════
DEAL = {
    "acquirer":         "Microsoft",
    "target":           "Activision Blizzard",
    "offer_per_share":  95.00,         # $ per share
    "target_shares":    784_000_000,   # diluted shares outstanding
    "cash_pct":         1.00,          # 100% cash deal
    "stock_pct":        0.00,
    "acquirer_price":   380.00,        # MSFT share price at closing
}

# ─── Target financials (Activision, in $M) ───
TARGET = {
    "revenue_y0":       8_800,
    "revenue_growth":   [0.08, 0.10, 0.12, 0.09, 0.07],   # 5-yr forecast
    "ebitda_margin":    0.38,
    "tax_rate":         0.21,
    "capex_pct":        0.05,   # % of revenue
    "nwc_pct":          0.02,   # % of revenue change
    "da_pct":           0.06,   # D&A as % of revenue
    "net_debt":         -5_500, # negative = net cash
    "terminal_growth":  0.025,
    "wacc":             0.085,
}

# ─── Acquirer financials (Microsoft, in $M) ──
ACQUIRER = {
    "net_income":       72_000,
    "shares_out":       7_430,  # millions
    "interest_rate":    0.045,  # cost of debt on deal financing
    "tax_rate":         0.21,
}

# ─── Synergies (annual, in $M) ───────────────
SYNERGIES = {
    "cost_synergies":   1_200,
    "revenue_synergies": 800,
    "phase_in":         [0.30, 0.60, 1.00, 1.00, 1.00],  # % realisation per year
}

# ═════════════════════════════════════════════
# 1. DCF VALUATION
# ═════════════════════════════════════════════
def build_dcf(target, synergies=None):
    years    = list(range(1, len(target["revenue_growth"]) + 1))
    revenue  = [target["revenue_y0"]]
    for g in target["revenue_growth"]:
        revenue.append(revenue[-1] * (1 + g))
    revenue = revenue[1:]                                   # drop Y0

    df = pd.DataFrame(index=years)
    df["Revenue"]   = revenue
    df["EBITDA"]    = df["Revenue"] * target["ebitda_margin"]
    df["D&A"]       = df["Revenue"] * target["da_pct"]
    df["EBIT"]      = df["EBITDA"] - df["D&A"]
    df["Taxes"]     = df["EBIT"] * target["tax_rate"]
    df["NOPAT"]     = df["EBIT"] - df["Taxes"]
    df["CapEx"]     = df["Revenue"] * target["capex_pct"]
    df["ΔNWC"]      = df["Revenue"].diff().fillna(df["Revenue"].iloc[0]) * target["nwc_pct"]
    df["FCF"]       = df["NOPAT"] + df["D&A"] - df["CapEx"] - df["ΔNWC"]

    # Synergies (optional)
    if synergies:
        syn = pd.Series(
            [(synergies["cost_synergies"] + synergies["revenue_synergies"]) * p
             * (1 - target["tax_rate"])
             for p in synergies["phase_in"]], index=years)
        df["Synergies (after-tax)"] = syn
        df["FCF"] += syn

    # Discount factors
    df["Discount Factor"] = [(1 / (1 + target["wacc"])) ** y for y in years]
    df["PV of FCF"]       = df["FCF"] * df["Discount Factor"]

    # Terminal value (Gordon Growth)
    tv = (df["FCF"].iloc[-1] * (1 + target["terminal_growth"])) / \
         (target["wacc"] - target["terminal_growth"])
    pv_tv = tv * df["Discount Factor"].iloc[-1]

    # Enterprise & Equity value
    enterprise_value = df["PV of FCF"].sum() + pv_tv
    equity_value     = enterprise_value - target["net_debt"]
    implied_price    = equity_value * 1e6 / DEAL["target_shares"]

    return df, {
        "PV of FCF":        df["PV of FCF"].sum(),
        "Terminal Value":   tv,
        "PV of TV":         pv_tv,
        "Enterprise Value": enterprise_value,
        "Equity Value":     equity_value,
        "Implied Price":    implied_price,
    }

# ═════════════════════════════════════════════
# 2. ACCRETION / DILUTION
# ═════════════════════════════════════════════
def accretion_dilution(deal, acquirer, target, synergies):
    offer_value = deal["offer_per_share"] * deal["target_shares"] / 1e6   # $M
    cash_portion  = offer_value * deal["cash_pct"]
    stock_portion = offer_value * deal["stock_pct"]

    # Shares issued for stock portion
    new_shares = stock_portion / deal["acquirer_price"]     # millions
    total_shares = acquirer["shares_out"] + new_shares

    # Target net income (Y1)
    target_revenue = target["revenue_y0"] * (1 + target["revenue_growth"][0])
    target_ebitda  = target_revenue * target["ebitda_margin"]
    target_ebit    = target_ebitda - target_revenue * target["da_pct"]
    target_ni      = target_ebit * (1 - target["tax_rate"])

    # Synergies (Y1, after-tax)
    syn_total   = (synergies["cost_synergies"] + synergies["revenue_synergies"]) \
                  * synergies["phase_in"][0]
    syn_aftertax = syn_total * (1 - acquirer["tax_rate"])

    # Interest expense on cash portion (after-tax)
    interest_expense = cash_portion * acquirer["interest_rate"]
    interest_aftertax = interest_expense * (1 - acquirer["tax_rate"])

    # Combined net income
    combined_ni = acquirer["net_income"] + target_ni + syn_aftertax - interest_aftertax

    # EPS
    standalone_eps = acquirer["net_income"] / acquirer["shares_out"]
    proforma_eps   = combined_ni / total_shares
    accretion_pct  = (proforma_eps / standalone_eps - 1) * 100

    return {
        "Offer Value ($M)":    offer_value,
        "Cash Portion ($M)":   cash_portion,
        "Stock Portion ($M)":  stock_portion,
        "New Shares Issued":   new_shares,
        "Total Shares":        total_shares,
        "Target NI ($M)":      target_ni,
        "Synergies AT ($M)":   syn_aftertax,
        "Interest AT ($M)":    interest_aftertax,
        "Combined NI ($M)":    combined_ni,
        "Standalone EPS":      standalone_eps,
        "Pro-Forma EPS":       proforma_eps,
        "Accretion (%)":       accretion_pct,
    }

# ═════════════════════════════════════════════
# 3. SENSITIVITY ANALYSIS
# ═════════════════════════════════════════════
def sensitivity_table(target):
    waccs  = np.arange(0.065, 0.115, 0.005)
    growths = np.arange(0.010, 0.045, 0.005)
    matrix = np.zeros((len(waccs), len(growths)))

    for i, w in enumerate(waccs):
        for j, g in enumerate(growths):
            t_copy = target.copy()
            t_copy["wacc"] = w
            t_copy["terminal_growth"] = g
            _, summary = build_dcf(t_copy, SYNERGIES)
            matrix[i, j] = summary["Implied Price"]

    return pd.DataFrame(matrix,
                        index=[f"{w*100:.1f}%" for w in waccs],
                        columns=[f"{g*100:.1f}%" for g in growths])

# ═════════════════════════════════════════════
# 4. PLOTTING
# ═════════════════════════════════════════════
COLORS = {
    "bg":       "#0d1117",
    "panel":    "#161b22",
    "accent1":  "#58a6ff",   # blue  — MSFT
    "accent2":  "#3fb950",   # green — accretion
    "accent3":  "#f0883e",   # orange
    "negative": "#f85149",   # red   — dilution
    "scatter":  "#30363d",
    "text":     "#e6edf3",
    "subtext":  "#8b949e",
}

def build_dashboard(dcf_df, dcf_summary, acc_dil, sens):

    fig = plt.figure(figsize=(20, 13), facecolor=COLORS["bg"])
    gs  = GridSpec(2, 3, figure=fig, hspace=0.42, wspace=0.32,
                   left=0.06, right=0.97, top=0.87, bottom=0.08)

    ax_fcf  = fig.add_subplot(gs[0, 0])   # FCF waterfall
    ax_val  = fig.add_subplot(gs[0, 1])   # Valuation bridge
    ax_eps  = fig.add_subplot(gs[0, 2])   # EPS accretion
    ax_syn  = fig.add_subplot(gs[1, 0])   # Synergies phase-in
    ax_sens = fig.add_subplot(gs[1, 1])   # Sensitivity heatmap
    ax_mix  = fig.add_subplot(gs[1, 2])   # Deal consideration

    for ax in [ax_fcf, ax_val, ax_eps, ax_syn, ax_sens, ax_mix]:
        ax.set_facecolor(COLORS["panel"])
        for spine in ax.spines.values():
            spine.set_edgecolor(COLORS["scatter"])
        ax.tick_params(colors=COLORS["subtext"])

    # ── Header ─────────────────────────────────
    fig.text(0.5, 0.975,
             "M&A Analysis — Microsoft / Activision Blizzard",
             ha="center", va="top", fontsize=18, fontweight="bold",
             color=COLORS["text"], fontfamily="monospace")
    fig.text(0.5, 0.950,
             f"DCF Valuation + Accretion/Dilution · Offer: ${DEAL['offer_per_share']:.0f}/share · "
             f"Deal Value: ${DEAL['offer_per_share']*DEAL['target_shares']/1e9:.1f}B",
             ha="center", va="top", fontsize=10,
             color=COLORS["subtext"], fontfamily="monospace")

    # ── 4a. FCF Projection ─────────────────────
    years = dcf_df.index
    ax_fcf.bar(years, dcf_df["FCF"], color=COLORS["accent1"], edgecolor="none",
               width=0.55, label="Free Cash Flow")
    if "Synergies (after-tax)" in dcf_df.columns:
        ax_fcf.bar(years, dcf_df["Synergies (after-tax)"],
                   color=COLORS["accent2"], edgecolor="none",
                   width=0.55, bottom=dcf_df["FCF"] - dcf_df["Synergies (after-tax)"],
                   label="Synergies (after-tax)", alpha=0.85)
    for y, v in zip(years, dcf_df["FCF"]):
        ax_fcf.text(y, v + 150, f"${v/1000:.1f}B", ha="center",
                    color=COLORS["text"], fontsize=8)
    ax_fcf.set_title("Projected Free Cash Flows", color=COLORS["text"], fontsize=11, pad=8)
    ax_fcf.set_xlabel("Year", color=COLORS["subtext"], fontsize=9)
    ax_fcf.set_ylabel("FCF ($M)", color=COLORS["subtext"], fontsize=9)
    ax_fcf.legend(facecolor=COLORS["bg"], edgecolor=COLORS["scatter"],
                  labelcolor=COLORS["text"], fontsize=8)
    ax_fcf.grid(axis="y", color=COLORS["scatter"], alpha=0.4, linewidth=0.5)

    # ── 4b. Valuation Bridge ───────────────────
    labels = ["PV of\nFCF", "PV of\nTerminal\nValue", "Enterprise\nValue",
              "(–) Net\nDebt", "Equity\nValue"]
    values = [dcf_summary["PV of FCF"], dcf_summary["PV of TV"],
              dcf_summary["Enterprise Value"], -TARGET["net_debt"],
              dcf_summary["Equity Value"]]
    bar_colors = [COLORS["accent1"], COLORS["accent1"], COLORS["accent3"],
                  COLORS["accent2"], COLORS["accent3"]]

    bars = ax_val.bar(range(len(labels)), [v/1000 for v in values],
                      color=bar_colors, edgecolor="none", width=0.6)
    for bar, val in zip(bars, values):
        ax_val.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                    f"${val/1000:.1f}B", ha="center", color=COLORS["text"], fontsize=9)
    ax_val.set_xticks(range(len(labels)))
    ax_val.set_xticklabels(labels, color=COLORS["subtext"], fontsize=8)
    ax_val.set_title(f"Valuation Bridge — Implied Price: ${dcf_summary['Implied Price']:.2f}",
                     color=COLORS["text"], fontsize=11, pad=8)
    ax_val.set_ylabel("Value ($B)", color=COLORS["subtext"], fontsize=9)
    ax_val.grid(axis="y", color=COLORS["scatter"], alpha=0.4, linewidth=0.5)

    # Offer price reference line
    offer_eq = DEAL["offer_per_share"] * DEAL["target_shares"] / 1e9
    ax_val.axhline(y=offer_eq, color=COLORS["negative"], linestyle="--",
                   linewidth=1.2, alpha=0.8)
    ax_val.text(len(labels) - 0.5, offer_eq + 1.5,
                f"Offer: ${offer_eq:.1f}B",
                color=COLORS["negative"], fontsize=8, ha="right")

    # ── 4c. EPS Accretion/Dilution ─────────────
    eps_labels = ["Standalone\nEPS", "Pro-Forma\nEPS"]
    eps_vals   = [acc_dil["Standalone EPS"], acc_dil["Pro-Forma EPS"]]
    is_accretive = acc_dil["Accretion (%)"] >= 0
    color_eps  = COLORS["accent2"] if is_accretive else COLORS["negative"]

    bars = ax_eps.bar(eps_labels, eps_vals,
                      color=[COLORS["accent1"], color_eps], edgecolor="none", width=0.55)
    for bar, val in zip(bars, eps_vals):
        ax_eps.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.2,
                    f"${val:.2f}", ha="center", color=COLORS["text"], fontsize=10,
                    fontweight="bold")

    tag = "ACCRETIVE" if is_accretive else "DILUTIVE"
    ax_eps.text(0.5, max(eps_vals) * 1.15,
                f"{tag}  {acc_dil['Accretion (%)']:+.2f}%",
                ha="center", color=color_eps, fontsize=14,
                fontweight="bold", transform=ax_eps.transData)
    ax_eps.set_title("EPS Impact on Acquirer",
                     color=COLORS["text"], fontsize=11, pad=8)
    ax_eps.set_ylabel("EPS ($)", color=COLORS["subtext"], fontsize=9)
    ax_eps.set_ylim(0, max(eps_vals) * 1.3)
    ax_eps.grid(axis="y", color=COLORS["scatter"], alpha=0.4, linewidth=0.5)

    # ── 4d. Synergies phase-in ─────────────────
    phase_years = list(range(1, len(SYNERGIES["phase_in"]) + 1))
    cost_syn = [SYNERGIES["cost_synergies"] * p for p in SYNERGIES["phase_in"]]
    rev_syn  = [SYNERGIES["revenue_synergies"] * p for p in SYNERGIES["phase_in"]]

    ax_syn.bar(phase_years, cost_syn, color=COLORS["accent1"],
               edgecolor="none", width=0.55, label="Cost Synergies")
    ax_syn.bar(phase_years, rev_syn, bottom=cost_syn, color=COLORS["accent2"],
               edgecolor="none", width=0.55, label="Revenue Synergies")

    totals = [c + r for c, r in zip(cost_syn, rev_syn)]
    for y, t in zip(phase_years, totals):
        ax_syn.text(y, t + 50, f"${t:.0f}M", ha="center",
                    color=COLORS["text"], fontsize=8)

    ax_syn.set_title("Synergies Phase-In (pre-tax)",
                     color=COLORS["text"], fontsize=11, pad=8)
    ax_syn.set_xlabel("Year", color=COLORS["subtext"], fontsize=9)
    ax_syn.set_ylabel("Synergies ($M)", color=COLORS["subtext"], fontsize=9)
    ax_syn.legend(facecolor=COLORS["bg"], edgecolor=COLORS["scatter"],
                  labelcolor=COLORS["text"], fontsize=8)
    ax_syn.grid(axis="y", color=COLORS["scatter"], alpha=0.4, linewidth=0.5)

    # ── 4e. Sensitivity Heatmap ────────────────
    im = ax_sens.imshow(sens.values, cmap="RdYlGn", aspect="auto",
                        vmin=sens.values.min(), vmax=sens.values.max())
    ax_sens.set_xticks(range(len(sens.columns)))
    ax_sens.set_xticklabels(sens.columns, rotation=0, color=COLORS["subtext"], fontsize=8)
    ax_sens.set_yticks(range(len(sens.index)))
    ax_sens.set_yticklabels(sens.index, color=COLORS["subtext"], fontsize=8)
    for i in range(len(sens.index)):
        for j in range(len(sens.columns)):
            ax_sens.text(j, i, f"${sens.values[i,j]:.0f}",
                         ha="center", va="center", fontsize=7, color="black")
    ax_sens.set_title("Implied Price — WACC × Terminal Growth",
                      color=COLORS["text"], fontsize=11, pad=8)
    ax_sens.set_xlabel("Terminal Growth", color=COLORS["subtext"], fontsize=9)
    ax_sens.set_ylabel("WACC",            color=COLORS["subtext"], fontsize=9)
    cb = plt.colorbar(im, ax=ax_sens, fraction=0.046, pad=0.04)
    cb.ax.tick_params(colors=COLORS["subtext"])

    # ── 4f. Deal Consideration Mix ─────────────
    offer_value = DEAL["offer_per_share"] * DEAL["target_shares"] / 1e9
    mix_labels  = ["Cash", "Stock"]
    mix_values  = [DEAL["cash_pct"], DEAL["stock_pct"]]
    mix_colors  = [COLORS["accent2"], COLORS["accent1"]]

    # Filter zero values
    non_zero = [(l, v, c) for l, v, c in zip(mix_labels, mix_values, mix_colors) if v > 0]
    labels_nz, values_nz, colors_nz = zip(*non_zero)

    wedges, texts, autotexts = ax_mix.pie(values_nz, labels=labels_nz, colors=colors_nz,
                                            autopct="%.0f%%", startangle=90,
                                            textprops={"color": COLORS["text"], "fontsize": 10},
                                            wedgeprops={"edgecolor": COLORS["bg"], "linewidth": 2})
    for t in autotexts:
        t.set_color("black")
        t.set_fontweight("bold")
    ax_mix.set_title(f"Deal Consideration — ${offer_value:.1f}B",
                      color=COLORS["text"], fontsize=11, pad=8)

    plt.savefig("ma_analysis_dashboard.png", dpi=180,
                bbox_inches="tight", facecolor=COLORS["bg"])
    print("  Dashboard saved → ma_analysis_dashboard.png")
    plt.show()

# ═════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════
if __name__ == "__main__":
    print("═" * 60)
    print(f"  M&A Analysis: {DEAL['acquirer']} acquires {DEAL['target']}")
    print("═" * 60)

    print("\n  Building DCF model …")
    dcf_df, dcf_summary = build_dcf(TARGET, SYNERGIES)
    print(f"    ✓ PV of FCF:        ${dcf_summary['PV of FCF']/1000:>7.1f}B")
    print(f"    ✓ PV of Terminal:   ${dcf_summary['PV of TV']/1000:>7.1f}B")
    print(f"    ✓ Enterprise Value: ${dcf_summary['Enterprise Value']/1000:>7.1f}B")
    print(f"    ✓ Equity Value:     ${dcf_summary['Equity Value']/1000:>7.1f}B")
    print(f"    ✓ Implied Price:    ${dcf_summary['Implied Price']:>7.2f}/share")
    print(f"    ✓ Offer Price:      ${DEAL['offer_per_share']:>7.2f}/share")
    premium = (DEAL['offer_per_share'] / dcf_summary['Implied Price'] - 1) * 100
    print(f"    ✓ Premium vs DCF:   {premium:>+7.1f}%")

    print("\n  Running Accretion/Dilution analysis …")
    acc_dil = accretion_dilution(DEAL, ACQUIRER, TARGET, SYNERGIES)
    print(f"    ✓ Standalone EPS:   ${acc_dil['Standalone EPS']:>7.2f}")
    print(f"    ✓ Pro-Forma EPS:    ${acc_dil['Pro-Forma EPS']:>7.2f}")
    sign = "ACCRETIVE" if acc_dil["Accretion (%)"] >= 0 else "DILUTIVE"
    print(f"    ✓ Result:           {sign} {acc_dil['Accretion (%)']:+.2f}%")

    print("\n  Computing sensitivity table …")
    sens = sensitivity_table(TARGET)

    print("\n  Generating dashboard …")
    build_dashboard(dcf_df, dcf_summary, acc_dil, sens)