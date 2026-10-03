# GraminSahay 🌾

**An LLM-Powered, RAG-Based Rural Welfare & Government Services Navigator**

GraminSahay helps rural citizens discover the government welfare schemes they are
entitled to — **without needing to know the scheme's name**. A citizen describes their
situation ("I am a small farmer in Warangal with a daughter starting college"), and the
system retrieves relevant Telangana welfare schemes, determines eligibility with clear
explanations, warns about schemes that cannot be claimed together, and guides them
through applying.

> Supports **SDG 1 (No Poverty)** and **SDG 10 (Reduced Inequalities)** · Built for **SIH 2026 (SIH26088)**.

---

## Why this design is different

The headline idea is not "a chatbot over scheme PDFs." The core engineering decision is:

> **The LLM handles _language_ (retrieval + explanation). Deterministic rules make the
> _eligibility decision_.**

Eligibility for a welfare scheme is **safety-critical** — telling a poor citizen "you are
eligible" when they are not wastes a trip to the office and erodes trust, while a false
"not eligible" denies them a benefit they deserve. LLMs hallucinate; transparent rules do
not. So eligibility is decided by an auditable rule engine, and the LLM only phrases the
already-decided verdict and cites the official source.

---

## Architecture

```
Citizen situation + profile
        │
        ▼
┌───────────────────┐   semantic search    ┌──────────────────────┐
│  SchemeRetriever  │ ───────────────────► │  pgvector (Postgres) │
│   (RAG retrieval) │ ◄─────────────────── │   scheme embeddings  │
└───────────────────┘   candidate schemes  └──────────────────────┘
        │
        ▼
┌─────────────────────┐   deterministic, auditable
│  EligibilityEngine  │   ELIGIBLE / POSSIBLY / NOT / MISSING_INFO
└─────────────────────┘
        │
        ▼
┌─────────────────────┐   graph of mutually-exclusive schemes
│  ConflictDetector   │   "you can't claim both A and B"
└─────────────────────┘
        │
        ▼
┌─────────────────────┐   grounded, cited, plain-language
│  AnswerGenerator    │   (LLM phrases the decision; cannot change it)
└─────────────────────┘
        │
        ▼
   JSON response  →  (Next.js frontend / mobile app)
```

### Eligibility classification logic
| Situation | Result |
|---|---|
| Every rule passes, nothing missing | `ELIGIBLE` |
| A rule is violated | `NOT_ELIGIBLE` |
| Nothing fails, but a required field is unknown (some rules already passed) | `POSSIBLY_ELIGIBLE` |
| Nothing fails, nothing passes yet, a required field is unknown | `MISSING_INFORMATION` |

The `MISSING_INFORMATION` vs `NOT_ELIGIBLE` distinction is deliberate: the system asks for
the missing detail instead of silently assuming and producing a wrong answer.

---

## Tech stack

| Layer | Technology |
|---|---|
| Language / Framework | **Java 21 · Spring Boot 3.3** |
| AI / RAG | **Spring AI** (chat + embeddings + vector store) |
| Vector store | **PostgreSQL + pgvector** (HNSW, cosine distance) |
| LLM | OpenAI `gpt-4o-mini` *or* Groq `llama-3.3-70b-versatile` |
| Build | Maven |
| Infra | Docker Compose |

---

## Running locally

### Prerequisites
- Java 21+ and Maven (or the included `mvnw`)
- Docker (for PostgreSQL + pgvector)
- An LLM API key (OpenAI, or Groq + an embedding provider — see `.env.example`)

### 1. Start the database
```bash
docker compose up -d
```

### 2. Configure credentials
```bash
cp .env.example .env
# edit .env and set OPENAI_API_KEY (and base-url/model if using Groq)
export $(grep -v '^#' .env | xargs)
```

### 3. Run the app
```bash
mvn spring-boot:run
```
On first startup the app loads the Telangana scheme knowledge base
(`src/main/resources/schemes/telangana-schemes.json`), embeds each scheme into pgvector,
and is then ready to serve requests.

### 4. Ask it something
```bash
curl -s -X POST http://localhost:8080/api/navigate \
  -H 'Content-Type: application/json' \
  -d '{
        "situation": "I am a small farmer in Warangal and I own two acres of land",
        "occupation": "farmer",
        "landHoldingAcres": 2.0,
        "age": 45,
        "district": "Warangal",
        "isBpl": true,
        "withExplanations": true
      }' | jq
```

You will get back the schemes the citizen is eligible / possibly eligible for, any
conflicts between them, and (if `withExplanations: true`) a grounded, cited explanation
for each.

### Run the tests (no DB or API key needed for the core logic)
```bash
mvn test
```
`EligibilityEngineTest` and `ConflictDetectorTest` cover the safety-critical decision logic
in isolation — no database, no LLM.

---

## Telangana schemes included (Phase 1)
Agriculture (Rythu Bharosa, Indiramma Atmeeya Bharosa), Pension (Aasara Old-Age, Aasara
Widow), Education (Kalyana Lakshmi/Shaadi Mubarak, ePASS Post-Matric Scholarship),
Healthcare (Rajiv Aarogyasri), Housing (Indiramma Indlu).

> Scheme details are approximate and for demonstration; always verify on the official
> portal linked in each result before applying.

---

## Roadmap (next phases)
- [ ] LLM extraction: turn free-text/voice situation into the structured profile automatically
- [ ] Faithfulness / grounding check on generated answers (RAGAs-style evaluation)
- [ ] Multilingual support (Telugu + Hindi) with Indic STT/TTS for voice-first access
- [ ] Next.js web frontend + Flutter mobile app
- [ ] Expand the knowledge base and add citation highlighting

---

## ⚠️ Spring AI version note
This project pins **Spring AI `1.0.0-M3`** (a milestone). The vector-search API changed
between milestones and the GA release:
- **M3 (this project):** `SearchRequest.query("...").withTopK(k).withSimilarityThreshold(t)`
- **1.0.0 GA and later:** `SearchRequest.builder().query("...").topK(k).similarityThreshold(t).build()`

If you upgrade `spring-ai.version` in `pom.xml`, update the two calls in
`SchemeRetriever` and `SchemeIngestionService` to the builder form, and confirm the
starter artifact ids (the `-spring-boot-starter` suffix also changed in GA). The milestone
repo is already configured in `pom.xml`.

---

## API reference

### `POST /api/navigate`
**Request body**
| Field | Type | Required | Notes |
|---|---|---|---|
| `situation` | string | ✅ | Free-text description of the citizen's situation |
| `occupation` | string | | e.g. `farmer`, `student`, `labourer` |
| `annualIncome` | int | | Household annual income (INR) |
| `landHoldingAcres` | number | | Agricultural land owned |
| `age` | int | | |
| `gender` | string | | `male` / `female` / `other` |
| `district` | string | | |
| `isBpl` | boolean | | Below Poverty Line (white ration card) |
| `category` | string | | `general` / `obc` / `sc` / `st` / `minority` |
| `withExplanations` | boolean | | Generate LLM explanations (one API call per scheme) |

Omitting a profile field is meaningful: it makes the engine return
`MISSING_INFORMATION` / `POSSIBLY_ELIGIBLE` rather than guessing.
