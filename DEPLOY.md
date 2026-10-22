# Deploying GraminSahay

This guide gets GraminSahay live on a public URL. The app needs two things in the cloud:
a **PostgreSQL database with the pgvector extension**, and the **web service** itself.

The recommended host is **Railway** (easiest for this stack — Postgres + web app in one
project). A **Render** alternative is included at the bottom.

> 💡 Memory note: the embedding model (`all-MiniLM-L6-v2`) runs on ONNX Runtime via
> `fastembed` — no PyTorch — so the app fits in a **512 MB** instance (Render's free tier).

---

## Option A — Railway (recommended)

### 1. Create the project and database
1. Go to [railway.app](https://railway.app) and sign in with GitHub.
2. **New Project → Deploy from GitHub repo →** select `GraminSahay`.
3. In the project, **New → Database → Add PostgreSQL**.
4. Enable pgvector: open the Postgres service → **Data/Query** tab → run:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
   (The app also runs this on startup, but doing it here first avoids a race.)

### 2. Configure the web service
Open your web service → **Variables** and add:

| Variable | Value |
|---|---|
| `DATABASE_URL` | Reference the Postgres service's `DATABASE_URL` (Railway lets you link it) |
| `OPENAI_API_KEY` | your Groq key (`gsk_...`) |
| `OPENAI_BASE_URL` | `https://api.groq.com/openai/v1` |
| `CHAT_MODEL` | `openai/gpt-oss-20b` |
| `JWT_SECRET` | a long random string — generate with `python -c "import secrets; print(secrets.token_hex(32))"` |

> `DATABASE_URL` from Railway starts with `postgresql://`; the app rewrites it to the
> SQLAlchemy driver form automatically (see `config.py: sqlalchemy_url`).

### 3. Deploy
Railway auto-detects the `Procfile` and runs:
```
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```
First boot downloads the embedding model and ingests the schemes (watch the logs for
`Ingested 8 scheme documents` then `GraminSahay is ready`). Then open the generated URL.

---

## Option B — Render (free tier, via `render.yaml`)

1. In the Render dashboard: **New + → Blueprint →** select the `GraminSahay` repo.
2. Render reads `render.yaml` and creates a free **web service** and a free **PostgreSQL**
   database, with `DATABASE_URL` and `JWT_SECRET` already set. Click **Apply**.
3. When prompted, set `OPENAI_API_KEY` to your Groq key (`gsk_...`).
4. The app enables pgvector by itself on startup.

Free-tier limits: the web service sleeps after 15 minutes idle (the next request takes about
a minute to wake it), and the free database **expires after 30 days**. For an always-on,
permanent setup, change the two `plan:` values in `render.yaml` to paid plans.

---

## After it's live
- Open the public URL — the web UI loads at `/`, interactive API docs at `/docs`.
- Try a situation; confirm schemes, conflicts and explanations appear.
- Put the live link in your resume and GitHub repo description. A clickable demo is the
  single strongest signal that the project is real and works.

## Troubleshooting
| Symptom | Fix |
|---|---|
| App crashes on boot with a memory error | Move to the next instance size up (1 GB) |
| `relation "scheme_embeddings" ... type "vector" does not exist` | Run `CREATE EXTENSION IF NOT EXISTS vector;` on the DB |
| Explanations blank, logs show model 404 | Update `CHAT_MODEL` to a model your Groq key lists (`/v1/models`) |
| First request slow | Expected — the model loads lazily on first use; subsequent requests are fast |
