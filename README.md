# M&A Analysis — DCF Valuation + Accretion/Dilution Model

> Comprehensive M&A analysis framework in Python: DCF valuation, synergy modelling, accretion/dilution analysis, and sensitivity tables — Microsoft / Activision Blizzard case study.

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=flat-square&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.50-red?style=flat-square&logo=streamlit)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)

---

## Project Overview

Recreates a **full investment banking M&A analysis** for the Microsoft-Activision deal (announced Jan 2022, closed Oct 2023 — one of the largest tech deals in history, ~$68.7B).

The project implements the **three pillars** of an M&A analyst's toolkit:

1. **Discounted Cash Flow (DCF)** valuation of the target
2. **Synergy modelling** with phase-in over 5 years
3. **Accretion/Dilution analysis** on the acquirer's EPS

---

## What It Does

| Module | Description |
|---|---|
| **DCF Valuation** | 5-year FCF projection, terminal value (Gordon Growth), NPV discounting |
| **Synergy Model** | Cost + revenue synergies with gradual phase-in |
| **Accretion/Dilution** | Impact on acquirer's EPS post-transaction |
| **Sensitivity Analysis** | Implied price matrix across WACC × Terminal Growth |
| **Deal Consideration** | Cash vs. stock mix optimisation |

---

## Deal Summary

| Parameter | Value |
|---|---|
| Acquirer | Microsoft Corporation (MSFT) |
| Target | Activision Blizzard (ATVI) |
| Offer Price | $95.00/share |
| Deal Value | ~$68.7B |
| Consideration | 100% Cash |
| Announced | January 18, 2022 |
| Closed | October 13, 2023 |

---

## Quickstart

### Static Dashboard
```bash
pip install -r requirements.txt
python ma_analysis.py
```

### Interactive Streamlit App
```bash
streamlit run ma_app.py
```

---

## Requirements

```
numpy>=1.24
pandas>=2.0
matplotlib>=3.7
streamlit>=1.30
```

---

## Key Concepts Demonstrated

- **Free Cash Flow to Firm (FCFF)** — unlevered cash flow calculation
- **WACC** as discount rate
- **Terminal Value** via Gordon Growth Model
- **Synergy realisation curves** (typical 3-year phase-in)
- **Accretion/Dilution** — core IB test for deal quality
- **Sensitivity analysis** on key value drivers

---

## Interactive Features (Streamlit)

Live adjustment of:
- Offer price & consideration mix (cash/stock)
- Target financials (revenue growth, EBITDA margin, tax rate)
- DCF assumptions (WACC, terminal growth)
- Synergy levels (cost + revenue)
- Acquirer capital structure & cost of debt

All metrics update in real time — implied price, accretion %, valuation bridge, and sensitivity heatmap.

---

## Disclaimer

This project is for **educational and portfolio demonstration** only. All figures are simplified estimates based on publicly available information and standard academic assumptions. This is **not** investment or M&A advice.

---

## References

- Rosenbaum & Pearl (2020). *Investment Banking: Valuation, LBOs, M&A, and IPOs.* Wiley.
- Damodaran, A. (2012). *Investment Valuation.* Wiley.
- Microsoft & Activision Blizzard SEC filings (10-K, 8-K).