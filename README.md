# GraminSahay 🌾 (Python / FastAPI)

**An LLM-Powered, RAG-Based Rural Welfare & Government Services Navigator**

GraminSahay helps rural citizens discover the government welfare schemes they are entitled
to — **without needing to know the scheme's name**. A citizen describes their situation
("I am a small farmer in Warangal with a daughter starting college"), and the system
retrieves relevant Telangana welfare schemes, determines eligibility with clear
explanations, warns about schemes that cannot be claimed together, and guides them through
applying.

> Supports **SDG 1 (No Poverty)** and **SDG 10 (Reduced Inequalities)** · Built for **SIH 2026 (SIH26088)**.

---

## Why this design is different

> **The LLM handles _language_ (retrieval + explanation). Deterministic rules make the
> _eligibility decision_.**

Eligibility for a welfare scheme is **safety-critical** — a hallucinated "you are eligible"
could send a poor citizen on a wasted trip and erode trust. LLMs hallucinate; transparent
rules do not. So eligibility is decided by an auditable rule engine, and the LLM only phrases
the already-decided verdict and cites the official source.

---

## Architecture

```
Citizen situation + profile
        │
        ▼
┌───────────────────┐   local embedding + search   ┌──────────────────────┐
│  VectorStore      │ ───────────────────────────► │  pgvector (Postgres) │
│  (RAG retrieval)  │ ◄─────────────────────────── │   scheme embeddings  │
└───────────────────┘      candidate scheme ids     └──────────────────────┘
        │
        ▼
┌─────────────────────┐   deterministic, auditable
│  eligibility.evaluate│   ELIGIBLE / POSSIBLY / NOT / MISSING_INFO
└─────────────────────┘
        │
        ▼
┌───────────────────────┐   graph of mutually-exclusive schemes
│  detect_conflicts     │   "you can't claim both A and B"
└───────────────────────┘
        │
        ▼
┌─────────────────────┐   grounded, cited, plain-language
│  AnswerGenerator    │   (LLM phrases the decision; cannot change it)
└─────────────────────┘
        │
        ▼
   JSON response  →  web UI (served at /)
```

### Eligibility classification logic
| Situation | Result |
|---|---|
| Every rule passes, nothing missing | `ELIGIBLE` |
| A rule is violated | `NOT_ELIGIBLE` |
| Nothing fails, but a required field is unknown (some rules already passed) | `POSSIBLY_ELIGIBLE` |
| Nothing fails, nothing passes yet, a required field is unknown | `MISSING_INFORMATION` |

---

## Tech stack

| Layer | Technology |
|---|---|
| Language / Framework | **Python 3.11 · FastAPI** |
| Embeddings | **sentence-transformers** `all-MiniLM-L6-v2` — **runs locally, no API key** |
| Vector store | **PostgreSQL + pgvector** (cosine distance) via SQLAlchemy |
| LLM | OpenAI `gpt-4o-mini` *or* Groq `llama-3.3-70b-versatile` (chat only) |
| Validation | **Pydantic v2** |
| Frontend | Plain HTML + CSS + JavaScript (served by FastAPI) |
| Infra | Docker Compose |

> 💡 Because embeddings are **local**, you only need an LLM key for the explanation step.
> Retrieval + eligibility + conflict detection all work with no external API at all.

---

## Project layout
```
app/
  main.py          # FastAPI app, startup wiring, /api/navigate endpoint
  config.py        # settings from env / .env (pydantic-settings)
  domain.py        # Pydantic models + enums (the data shapes)
  eligibility.py   # deterministic eligibility engine + conflict detection  ← core logic
  knowledge.py     # loads the scheme JSON
  vectorstore.py   # local embeddings + pgvector storage/search
  generator.py     # grounded LLM explanation
  navigator.py     # orchestrates the whole pipeline
  data/telangana_schemes.json
  static/          # web UI (index.html, styles.css, app.js)
tests/
  test_eligibility.py   # pure-logic tests (no DB / LLM needed)
```

---

## Running locally

### Prerequisites
- Python 3.11+
- Docker (for PostgreSQL + pgvector)
- An LLM API key (OpenAI, or Groq — see `.env.example`)

### 1. Start the database
```bash
docker compose up -d
```

### 2. Install dependencies
Using `uv` (fast) — or plain `pip`:
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### 3. Configure credentials
```bash
cp .env.example .env
# edit .env and set OPENAI_API_KEY (and base-url/model if using Groq)
```

### 4. Run the app
```bash
uvicorn app.main:app --reload
```
On first startup the app downloads the embedding model (once), creates the pgvector table,
embeds the Telangana schemes, and is then ready.

### 5. Use it
- **Web UI:** open **http://localhost:8000/**
- **Interactive API docs** (FastAPI gives these free): **http://localhost:8000/docs**
- **Or curl:**
```bash
curl -s -X POST http://localhost:8000/api/navigate \
  -H 'Content-Type: application/json' \
  -d '{
        "situation": "I am a small farmer in Warangal and I own two acres of land",
        "occupation": "farmer",
        "landHoldingAcres": 2.0,
        "age": 45,
        "district": "Warangal",
        "isBpl": true,
        "withExplanations": true
      }'
```

### Run the tests (no DB or API key needed)
```bash
pytest
```
`tests/test_eligibility.py` covers the safety-critical decision logic in isolation.

---

## Telangana schemes included (Phase 1)
Agriculture (Rythu Bharosa, Indiramma Atmeeya Bharosa), Pension (Aasara Old-Age, Aasara
Widow), Education (Kalyana Lakshmi/Shaadi Mubarak, ePASS Post-Matric Scholarship),
Healthcare (Rajiv Aarogyasri), Housing (Indiramma Indlu).

> Scheme details are approximate and for demonstration; always verify on the official portal
> linked in each result before applying.

---

## Roadmap
- [x] RAG retrieval, deterministic eligibility, conflict detection, grounded explanations
- [x] LLM extraction: turn a free-text situation into the structured profile automatically
- [x] Multilingual support (Telugu + Hindi) — input translated for processing, answers returned in the chosen language
- [x] Voice-first access — speech-to-text (Whisper) for input, browser text-to-speech to read answers aloud
- [ ] Faithfulness / grounding check on generated answers (RAGAs-style evaluation)
- [ ] Expand the knowledge base and add citation highlighting

New to Python? See **[LEARNING.md](LEARNING.md)** — a guide to the Python/FastAPI concepts
used, mapped to each file in this project.
