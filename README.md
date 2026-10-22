# GraminSahay 🌾

**An LLM-Powered, RAG-Based Rural Welfare & Government Services Navigator**

GraminSahay helps rural citizens discover the government welfare schemes they are entitled
to — **without needing to know the scheme's name**. A citizen describes their situation
("I am a small farmer in Warangal with a daughter starting college"), and the system
retrieves relevant Telangana welfare schemes, determines eligibility with clear
explanations, warns about schemes that cannot be claimed together, and guides them through
applying.

## 🔗 Live demo

- **App:** https://graminsahay.onrender.com
- **API docs:** https://graminsahay.onrender.com/docs

> Hosted on Render's free tier: after 15 minutes without visitors the app sleeps, and the
> next visit takes about a minute to wake it up.

---

## Features

- **Describe your situation in plain words** — typed or spoken — and get matching schemes
  with a clear verdict: Eligible, Possibly eligible, More info needed, or Not eligible.
- **Example situations** (small farmer, elderly citizen, college student, landless labourer)
  that fill in the form with one click.
- **Optional profile details** (occupation, age, income, land, district, category, BPL) —
  left blank, they are extracted from the description automatically.
- **"Here's what we understood"** summary, so citizens can correct anything that was misread.
- **Conflict warnings** for schemes that cannot be claimed together.
- **Documents needed and steps to apply** for every scheme, with a link to the official portal.
- **Schemes directory** — browse and search every scheme in the knowledge base.
- **Telugu, Hindi and English**, including explanations in the chosen language.
- **Voice input** (browser speech recognition, with Whisper as a fallback) and **read-aloud**
  answers.
- **Adjustable text size** (A- / A / A+) for easier reading.
- **Download / print** the results.
- **Optional sign-in** to save a profile — the navigator works fully without an account.

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
| Embeddings | `all-MiniLM-L6-v2` on **fastembed** (ONNX Runtime, no PyTorch) — **runs locally, no API key** |
| Vector store | **PostgreSQL + pgvector** (cosine distance) via SQLAlchemy |
| LLM | Groq `openai/gpt-oss-20b` (default in deployment) *or* OpenAI `gpt-4o-mini` — chat only |
| Speech-to-text | Browser Web Speech API, with Groq Whisper (`whisper-large-v3-turbo`) as a fallback |
| Validation | **Pydantic v2** |
| Auth | JWT (PyJWT) + bcrypt password hashing; users stored in Postgres |
| Frontend | Plain HTML + CSS + JavaScript (served by FastAPI) |
| Hosting | **Render** (free web service) + **Neon** (free Postgres with pgvector) |
| Local dev | Docker Compose (Postgres + pgvector) |

> 💡 Because embeddings are **local**, you only need an LLM key for extraction, translation
> and explanations. Retrieval, eligibility and conflict detection need no external API.
> Running the model on ONNX instead of PyTorch keeps memory use low enough for a 512 MB
> free instance.

---

## Pages and API

| Path | What it is |
|---|---|
| `/` | The navigator web app |
| `/login` | Sign in / create an account (optional) |
| `/docs` | Interactive API documentation |
| `POST /api/navigate` | Find schemes for a situation + profile (no account needed) |
| `GET /api/schemes` | List every scheme (used by the directory) |
| `POST /api/transcribe` | Turn a voice recording into text |
| `POST /api/auth/register`, `POST /api/auth/login` | Create an account / sign in; both return a JWT |

Old `/app.html` and `/login.html` links redirect to `/` and `/login`.

---

## Project layout
```
app/
  main.py          # FastAPI app, startup wiring, routes
  config.py        # settings from env / .env (pydantic-settings)
  domain.py        # Pydantic models + enums (the data shapes)
  eligibility.py   # deterministic eligibility engine + conflict detection  ← core logic
  knowledge.py     # loads the scheme JSON
  vectorstore.py   # local embeddings (fastembed) + pgvector storage/search
  extractor.py     # LLM: free-text situation -> structured profile
  translation.py   # LLM: Telugu/Hindi <-> English
  transcription.py # speech-to-text (Whisper)
  generator.py     # grounded LLM explanation
  navigator.py     # orchestrates the whole pipeline
  auth.py          # accounts, bcrypt hashing, JWT
  data/telangana_schemes.json
  static/          # web UI: app.html (served at /), login.html, styles.css,
                   # app.js, auth.js, i18n.js (translations), logo/favicon
tests/
  test_eligibility.py   # pure-logic tests (no DB / LLM needed)
  test_extractor.py     # form values always win over LLM-extracted ones (no LLM needed)
render.yaml        # Render Blueprint (free web service)
DEPLOY.md          # step-by-step deployment guide
```

---

## Running locally

### Prerequisites
- Python 3.11+
- Docker (for PostgreSQL + pgvector)
- An LLM API key (Groq or OpenAI — see `.env.example`)

### 1. Start the database
```bash
docker compose up -d
```

### 2. Install dependencies
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
On first startup the app downloads the embedding model (once, into `.cache/fastembed`),
creates the pgvector table, embeds the Telangana schemes, and is then ready.

### 5. Use it
- **Web UI:** open **http://localhost:8000**
- **Interactive API docs:** **http://localhost:8000/docs**
- **Or curl** — no account needed:
```bash
curl -s -X POST http://localhost:8000/api/navigate \
  -H 'Content-Type: application/json' \
  -d '{
        "situation": "I am a small farmer in Warangal and I own two acres of land",
        "withExplanations": true
      }'
```
To act as a signed-in user, call `/api/auth/register` (or `/api/auth/login`) and send the
returned token as `Authorization: Bearer <token>`.

### Run the tests (no DB or API key needed)
```bash
pytest
```
`tests/test_eligibility.py` covers the safety-critical decision logic in isolation;
`tests/test_extractor.py` checks that values the citizen types in the form always override
what the LLM extracted.

---

## Deployment

The live app runs as a single free **Render** web service (API + web UI), using a free
**Neon** Postgres database. Render's own free Postgres is deleted after 30 days, so it isn't used.

1. Create a free Neon project and copy its connection string.
2. In Render: **New + → Blueprint →** select this repo (it reads `render.yaml`).
3. Set `DATABASE_URL` (Neon connection string) and `OPENAI_API_KEY` (Groq key).
   `JWT_SECRET` is generated automatically.

Every push to `main` redeploys automatically. Full guide and troubleshooting:
**[DEPLOY.md](DEPLOY.md)**.

---

## Telangana schemes included (13)

| Category | Schemes |
|---|---|
| Agriculture | Rythu Bharosa, Indiramma Atmeeya Bharosa |
| Pension | Aasara Old Age Pension, Aasara Widow Pension, Aasara Disability Pension (Divyangula), Aasara Pension for Toddy Tappers & Weavers |
| Education | Kalyana Lakshmi / Shaadi Mubarak, ePASS Post-Matric Scholarship, CM Overseas Study Scheme |
| Healthcare | Rajiv Aarogyasri, KCR Kit (Maternity Benefit), CM Relief Fund (CMRF) Medical Assistance |
| Housing | Indiramma Indlu |

> Scheme details are approximate and for demonstration; always verify on the official portal
> linked in each result before applying.

---

## Roadmap
- [x] RAG retrieval, deterministic eligibility, conflict detection, grounded explanations
- [x] LLM extraction: turn a free-text situation into the structured profile automatically
- [x] Multilingual support (Telugu + Hindi) — input translated for processing, answers returned in the chosen language
- [x] Voice-first access — speech-to-text for input, browser text-to-speech to read answers aloud
- [x] Schemes directory, example situations, adjustable text size, download/print results
- [x] Free public deployment (Render + Neon)
- [ ] Faithfulness / grounding check on generated answers (RAGAs-style evaluation)
- [ ] Expand the knowledge base and add citation highlighting

New to Python? See **[LEARNING.md](LEARNING.md)** — a guide to the Python/FastAPI concepts
used, mapped to each file in this project.
