# GraminSahay — IEEE Literature Review Paper

Literature review / research-proposal paper for **GraminSahay: An LLM-Powered RAG-Based Rural Welfare and Government Services Navigator** (SIH26088, Batch 26MP_TA22, Dept. of CSE, MLR Institute of Technology).

## Files

| File | Description |
|------|-------------|
| `GraminSahay_IEEE_Paper.html` | **Recommended for PDF.** Open in any browser → **Print → Save as PDF** (A4). All 5 figures render as inline SVG; two-column layout. |
| `GraminSahay.tex` | **LaTeX source** (two-column `IEEEtran`). Compiles on Overleaf or any TeX install to the final two-column IEEE PDF. |
| `GraminSahay_IEEE_Paper.doc` | Word version (Word-HTML with figures as native VML). Opens in Microsoft Word; use **File → Save As → PDF**. If Word refuses to open it, use the `.html` above instead. |
| `build_doc.py` | Generator script (pure Python stdlib). Run `python3 build_doc.py` to regenerate both the `.doc` and `.html`. |
| `GraminSahay_Architecture.drawio` / `.svg` | Editable draw.io source + SVG for the system-architecture figure (Fig. 3). |
| `fig_existing.svg` | Fig. 1 — Existing system flow. |
| `fig_proposed.svg` | Fig. 2 — Proposed system flow. |
| `fig_chart_bar.svg` | Fig. 4 — Expected accuracy by welfare category. |
| `fig_chart_line.svg` | Fig. 5 — Expected Recall@k vs. faithfulness. |
| `figures/` | PNG/SVG/drawio sources for Figs. 1–5. |

> **Generating the PDF:** no PDF is committed. Easiest route — open `GraminSahay_IEEE_Paper.html` in a browser and **Print → Save as PDF** (choose A4, margins Default). Alternatives: open the `.doc` in Word → Save As PDF, or compile `GraminSahay.tex` on Overleaf.

## Section outline

I. Introduction · II. Literature Review (prose, six strands) · III. Research Gaps (three) · IV. Problem Statement · V. Motivation · VI. Research Objectives · VII. Existing & Proposed System (Fig. 1, Fig. 2) · VIII. Proposed Methodology · IX. Proposed Solution & Architecture (Fig. 3) · X. Expected Results (Table I, Table II, Fig. 4, Fig. 5) · XI. Future Enhancements · XII. Conclusion · References [1]–[20].

## Changes in this revision

- References expanded from 11 to **20** (added DPR, Whisper, LegalBench, IndicTrans2, XLM-R, FLARE, IndicNLPSuite, Indic-TTS, e-government chatbots).
- Literature Review rewritten as **flowing prose with bold inline thematic lead-ins** (Table I removed).
- Research Gaps consolidated to **three** (Multilingual/Voice-First Accessibility; Explainable Situation-First Eligibility; Application-Process Guidance & Conflict-Awareness).
- Removed the **Knowledge Sources & Data (datasets)** section.
- All **five figures retained** and embedded.

## Pending before final submission

- Expected-results values are **target** numbers (this is a proposal); replace with measured values after experiments.
