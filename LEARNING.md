# Learning GraminSahay (Python + FastAPI, for Java developers)

You know Java. This guide teaches the Python and FastAPI concepts used in **this project** by
mapping them to the Java/Spring Boot ideas you already met in the original version. Read it
once top-to-bottom, then keep it open beside the code.

---

## 0. The big-picture translation table

| Java / Spring Boot | Python / FastAPI | Where in this project |
|---|---|---|
| `record` / POJO | Pydantic `BaseModel` | `app/domain.py` |
| `enum` | `class X(str, Enum)` | `EligibilityStatus`, `Operator` |
| Jackson (JSON ↔ object) | Pydantic (built in) | everywhere |
| Bean Validation `@NotBlank` | Pydantic `Field(min_length=1)` | `NavigateRequest` in `app/main.py` |
| `application.yml` + `@Value` | pydantic-settings `BaseSettings` | `app/config.py` |
| `@RestController` + `@PostMapping` | `@app.post(...)` | `app/main.py` |
| `@Service` / `@Component` bean | a plain class you instantiate at startup | `app/navigator.py`, etc. |
| Dependency injection (Spring wires beans) | you wire objects yourself in `lifespan()` | `app/main.py` |
| `ApplicationRunner` (startup task) | `lifespan()` async context manager | `app/main.py` |
| Maven `pom.xml` | `pyproject.toml` | project root |
| JUnit | pytest | `tests/` |

Keep this table handy — it's the Rosetta Stone for the whole project.

---

## 1. Python basics you'll see (quick Java→Python)

| Java | Python |
|---|---|
| `String name;` | `name: str` (type hints are optional but we use them) |
| `Integer age;` (nullable) | `age: int | None` |
| `List<String>` | `list[str]` |
| `Map<String,Scheme>` | `dict[str, Scheme]` |
| `null` | `None` |
| `this.x` | `self.x` |
| `boolean b = true;` | `b = True` |
| `if (x) {...}` | `if x:` (indentation, not braces) |
| `//` comment | `#` comment |

Python uses **indentation** instead of `{ }` to define blocks. That's the biggest visual
difference. No semicolons.

---

## 2. Pydantic models = your records + Jackson + validation (`app/domain.py`)

In Java a `Scheme` was a `record` and Jackson turned JSON into it. In Python, one Pydantic
`BaseModel` does both — it defines the shape **and** parses/validates JSON:

```python
class Scheme(BaseModel):
    id: str
    name: str
    required_documents: list[str] = Field(default_factory=list, alias="requiredDocuments")
```

- Each line is a field with a **type hint** (`id: str`).
- `Field(alias="requiredDocuments")` means: in the JSON the key is camelCase
  (`requiredDocuments`), but in Python we use the snake_case name (`required_documents`).
  This is how we read the SAME scheme JSON the Java app used.
- `Scheme.model_validate(dict)` builds and validates a Scheme from a parsed JSON object
  (see `app/knowledge.py`).

**Enums**: `class EligibilityStatus(str, Enum)` — subclassing `str` makes it serialize to a
plain string like `"ELIGIBLE"`, exactly like the Java enum.

---

## 3. Configuration (`app/config.py`)

Spring read `application.yml` and injected values with `@Value`. Here, a `BaseSettings` class
does it:

```python
class Settings(BaseSettings):
    openai_api_key: str = "changeme"
    rag_top_k: int = 6
    model_config = SettingsConfigDict(env_file=".env")
```

- Each attribute is auto-filled from an environment variable of the same name in UPPER case
  (`openai_api_key` ← `OPENAI_API_KEY`), or the default if unset.
- `get_settings()` is wrapped in `@lru_cache`, so it's built once and reused — a singleton,
  just like a Spring config bean.

---

## 4. The FastAPI app and the endpoint (`app/main.py`)

### The request model (your DTO + @Valid)
```python
class NavigateRequest(BaseModel):
    situation: str = Field(min_length=1)         # like @NotBlank
    land_holding_acres: float | None = Field(default=None, alias="landHoldingAcres")
    with_explanations: bool = Field(default=False, alias="withExplanations")
```
FastAPI automatically parses the request body JSON into this object and validates it. If
`situation` is empty, FastAPI returns a 422 error on its own — you write no validation code.

### The endpoint (your @RestController)
```python
@app.post("/api/navigate", response_model=NavigationResponse)
def navigate(request: NavigateRequest) -> NavigationResponse:
    return state["navigator"].navigate(...)
```
- `@app.post("/api/navigate")` = `@PostMapping("/api/navigate")`.
- The `request: NavigateRequest` parameter = `@RequestBody NavigateRequest request`.
- Returning a Pydantic model → FastAPI serializes it to JSON automatically.

> 💡 **Free bonus:** FastAPI auto-generates interactive API docs at `/docs`. Open
> `http://localhost:8000/docs` and you can call your endpoint from the browser. Spring has
> nothing built in like this.

---

## 5. No automatic dependency injection — you wire it yourself (`lifespan` in `app/main.py`)

This is the biggest conceptual difference from Spring. Spring scanned for `@Service` beans and
injected them automatically. FastAPI does **not** do that. Instead, we build the objects
ourselves, once, at startup, inside a `lifespan` function:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    repository = SchemeRepository(settings.schemes_path)
    vector_store = VectorStore(...)
    vector_store.ensure_schema()
    vector_store.ingest(repository.all())      # same job as Spring's ApplicationRunner
    generator = AnswerGenerator(...)
    state["navigator"] = NavigatorService(repository, vector_store, generator, ...)
    yield                                       # app runs here
    state.clear()                               # cleanup on shutdown
```

- Everything **before** `yield` runs at startup (wiring + ingestion).
- Everything **after** `yield` runs at shutdown.
- We stash the finished `NavigatorService` in a `state` dict so the endpoint can reach it.

This explicit wiring is actually *good for learning* — you can see exactly how objects connect,
with no "magic".

---

## 6. The core logic is plain functions (`app/eligibility.py`)

In Java the engine was a `@Component` class. In Python it's just a **module of functions** —
no class needed, because there's no state to hold:

```python
def evaluate(scheme: Scheme, profile: CitizenProfile) -> EligibilityResult:
    ...
def detect_conflicts(results: list[EligibilityResult]) -> list[Conflict]:
    ...
```

Because these functions have no dependencies (pure logic), you can import and test them with
no database and no LLM — which is exactly what `tests/test_eligibility.py` does. This is the
single best thing to show an interviewer: **the safety-critical decision logic is pure and
unit-tested in isolation.**

---

## 7. Local embeddings (`app/vectorstore.py`) — the Python advantage

```python
self._model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
vector = self._model.encode(text, normalize_embeddings=True)
```

- This loads a small model **onto your own machine** and turns text into a 384-number vector.
- No API, no key, no cost for retrieval. (The Java version had to call a paid embedding API.)
- The vectors go into Postgres via `pgvector`; `cosine_distance` finds the nearest schemes.

This is why Python is the AI default — libraries like sentence-transformers are first-class.

---

## 8. How one request flows through the app (trace this!)

```
POST /api/navigate                 → app/main.py        navigate(request)
request.to_profile()               → app/domain.py      CitizenProfile
navigator.navigate(...)            → app/navigator.py   orchestrator
   ├─ vector_store.search(...)         → app/vectorstore.py  (local embed + pgvector search)
   ├─ eligibility.evaluate(...)        → app/eligibility.py  (deterministic rules)
   ├─ eligibility.detect_conflicts(...)→ app/eligibility.py  (conflict graph)
   └─ generator.explain(...)           → app/generator.py    (grounded LLM explanation)
NavigationResponse → JSON          → back to the browser / web UI
```

If you can walk an interviewer through these steps, you understand the project.

---

## 9. Suggested study order
1. `app/domain.py` — the data shapes (easy Python warm-up)
2. `app/eligibility.py` — the core logic (pure functions)
3. `tests/test_eligibility.py` — see the logic proven
4. `app/vectorstore.py` + `app/generator.py` — the RAG halves
5. `app/navigator.py` — how it all connects
6. `app/main.py` — the FastAPI edge + startup wiring
7. `app/config.py` + `pyproject.toml` — configuration & dependencies

---

## 10. Running it (recap)
```bash
docker compose up -d                 # Postgres + pgvector
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env                 # add your OPENAI_API_KEY
uvicorn app.main:app --reload        # http://localhost:8000  (UI)  + /docs (API docs)
pytest                               # core logic tests, no DB/key needed
```

---

## 11. Mini glossary

| Term | Plain meaning |
|---|---|
| Pydantic `BaseModel` | A class that defines a data shape and validates/serializes JSON |
| Type hint | `x: int` — documents (and lets tools check) a variable's type |
| `None` | Python's `null` |
| ASGI / Uvicorn | The server that runs a FastAPI app (like embedded Tomcat for Spring) |
| `lifespan` | Startup/shutdown hook where we build and wire objects |
| decorator (`@app.post`) | A `@`-annotation that adds behaviour to a function |
| `uv` / `pip` | Package managers (install dependencies, like Maven does) |
| venv | An isolated Python environment for this project's dependencies |
| `pyproject.toml` | Project + dependency definition (like `pom.xml`) |
| embedding | A list of numbers representing text meaning, used for semantic search |
