# GraminSahay — IEEE Literature Review Paper

Literature review / research-proposal paper for **GraminSahay: An LLM-Powered RAG-Based Rural Welfare and Government Services Navigator** (SIH26088, Batch 26MP_TA22, Dept. of CSE, MLR Institute of Technology).

## Files

| File | Description |
|------|-------------|
| `GraminSahay_IEEE_Paper.pdf` | **Final paper — just download and use.** Two-column IEEE layout, 7 pages, all 5 figures, 20 references. Pre-rendered, so you do **not** need Word, Pages, Safari, or any converter. |
| `GraminSahay_IEEE_Paper.html` | Source for the PDF. Renders two columns + all figures. To re-make the PDF: open in **Chrome or Edge** → Print → Save as PDF (A4). *Note: Safari's print engine ignores CSS columns, so use Chrome/Edge, or just use the committed `.pdf`.* |
| `GraminSahay.tex` | **LaTeX source** (two-column `IEEEtran`). Compiles on Overleaf to a polished two-column IEEE PDF — a good option on macOS. |
| `build_doc.py` | Generator (pure Python stdlib). `python3 build_doc.py` writes the `.html` and, if headless Chrome is present, the `.pdf`. |
| `GraminSahay_Architecture.drawio` / `.svg` | Editable draw.io source + SVG for the architecture figure (Fig. 3). |
| `fig_existing.svg` · `fig_proposed.svg` · `fig_chart_bar.svg` · `fig_chart_line.svg` | Legacy top-level figure SVGs. |
| `figures/` | Clean Times New Roman figure sources (Fig. 1–5, PNG/SVG/drawio) used in the paper. |

> **Just need the PDF?** Download `GraminSahay_IEEE_Paper.pdf` — it is the finished two-column paper. No conversion needed.
>
> The HTML-based `.doc` was removed: Microsoft Word and Apple Pages reject HTML files with a `.doc` extension. Use the committed `.pdf` (or compile `GraminSahay.tex` on Overleaf) instead.

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
