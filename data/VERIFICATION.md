# Verification log — reference dataset v1.1 (6 Nov 2026)

Method: every value that had passed through an AI text-extraction step, or was typed into code by hand, was
re-checked **by script** against the raw source. Raw text came from pdf.js (PDFs) or the page DOM (web tables).
Where a site blocked automated access (cea.nic.in), an independent second extraction quoting rows verbatim was
compared value-by-value, plus within-row arithmetic (requirement − supplied = energy not supplied).

| Table | Source document | Method | Values checked | Result |
|---|---|---|---|---|
| State energy requirement FY21–FY24 | MoP RS USQ 1752 | pdf.js, value on the state's own row | 136 | ✅ all match (4 were on wrapped name lines; values correct) |
| State energy requirement FY20 | MoP RS SQ 5 | pdf.js, row-aware | 34 | ✅ |
| State energy requirement FY14–FY16 | MoP LS SQ 164 | pdf.js, row-aware | 100 | ✅ |
| State energy requirement FY18 + All-India | CEA LGBR 2018-19 (WRPC copy) | pdf.js, row-aware | 36 | ✅ |
| State energy requirement FY26 + FY27 forecast | CEA LGBR 2026-27 | 2nd verbatim extraction + row arithmetic | 70 | ✅ |
| State energy requirement FY25 | CEA LGBR 2025-26 | 2nd verbatim extraction + row arithmetic | 36 | ✅ |
| Regional conventional generation FY26 | CEA DGR 31-03-2026 | pdf.js | 17 | ✅ |
| Regional gas generation FY26 | CEA report 17, Mar-2026 | pdf.js + PLF recomputation | 9 | ✅ |
| Regional installed capacity | CEA capacity summary 31-03-2026 | pdf.js | 29 | ✅ |
| State RE generation FY26 (5 sources) | MNRE RE Statistics 2025-26, Table 9.2 | pdf.js, row-wise | 180 | ✅ |
| Wasteland + solar potential | NISE 2025, Table 5 | pdf.js, row-wise | 105 | ✅ |
| Coal & lignite resources | MoC Annual Report 2025-26 ch.2 | pdf.js | 23 | ✅ |
| Urbanisation 2011–2036 | NIUA Handbook 2022, Table 1.2 | pdf.js, row-wise | 152 | ✅ |
| State population 2011–2036 | MoHFW projections via statisticstimes | DOM re-scrape | 175 | ✅ |
| State GSDP FY12–FY25 | MoSPI via statisticstimes | DOM re-scrape | 453 | ✅ |
| National GDP FY10–FY26 | MoSPI via statisticstimes | DOM re-scrape | 17 | ✅ |
| Hydro potential & status | CEA, 31-05-2026 | 2nd verbatim extraction + subtotal arithmetic | 144 | ✅ |
| Wind 150 m potential | NIWE (LS AU542) | 2nd verbatim extraction + total arithmetic | 10 | ✅ |
| UN WPP 2024 population & urban % | Worldometer (UN WPP 2024) | 2nd verbatim extraction | 28 | ✅ |
| National generation FY10–FY26 | MoP *Power Sector at a Glance* | printed growth column reproduced | 16 | ⚠️ 15/16 — see finding 1 |

**Total: ~1,770 values checked; 1 correction, 3 outlier flags.**

## Findings and actions
1. **FY2009-10 national generation.** The source's value (808.498 BU) is inconsistent with its own printed FY11 growth (5.59%); all later years reproduce exactly. The file has since been withdrawn from the Ministry site. FY10 is set to the value implied by the printed growth (805.367 BU) and flagged. Impact on the 2047 base forecast: −0.2% (4,488 → 4,480 TWh).
2. **Tripura FY18** (2,600 MU, double adjacent years) includes export to Bangladesh, per the CEA note → flagged EXCLUDE for regression.
3. **Odisha FY22** step of +28% → flagged as a possible coverage change; the model must test robustness to it.
4. **Karnataka FY24** +24% → genuine drought-year pumping load; flagged so it is not read as trend.
5. **Notes, no action needed.** Population years are 1 July of the calendar year, while energy is by financial year; the panel aligns FY t-(t+1) with July of year t. Island grids (A&N, Lakshadweep) are inside state/region sums but outside CEA regional totals (≈0.5 TWh).

## Reproduce
`python data/validate_all.py` rebuilds every table and re-runs the 16 reconciliation checks against published totals.
