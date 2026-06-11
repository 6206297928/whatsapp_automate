# Deploying Weavedesk V5 on Render (free)

Runs the agent as a FastAPI web service (with the built-in ADK web UI) on Render's
free tier. LLM via Google AI Studio (free), database via Neon (free).

Testing is via the ADK web UI / HTTP API — **no WhatsApp bridge required**.

```
repo root/
├── main.py            # FastAPI app: get_fast_api_app(agents_dir=".")
├── requirements.txt
├── render.yaml        # Render blueprint
└── weavedesk_v5/      # the agent package (discovered as the agent)
    ├── __init__.py    # exposes root_agent
    ├── agent.py
    ├── tools.py · prompts.py · database.py · init_db.py
```

---

## Prerequisites (one-time, no GCP needed)

1. **Render account** — https://render.com (free, no card)
2. **AI Studio API key** — https://aistudio.google.com/apikey (free)
3. **Neon Postgres** — https://neon.tech (free) → copy the connection string
   (looks like `postgresql://user:pass@ep-xxx.region.aws.neon.tech/db?sslmode=require`)
4. GitHub repo already connected: `github.com/6206297928/whatsapp_automate`

---

## Step 1 — Initialize the Neon database (once)

Locally, create the tables + demo seed data:

```bash
cd weavedesk_v5
python -m venv .venv && source .venv/bin/activate
pip install -r ../requirements.txt
export DATABASE_URL="postgresql://user:pass@ep-xxx.region.aws.neon.tech/db?sslmode=require"
python init_db.py
```

Expected: tables created + a demo customer (`+910000000001`) and vendor (`+910000000002`).

## Step 2 — Create the Render Web Service

**Option A — Blueprint (uses `render.yaml`):**
1. Render dashboard → **New + → Blueprint**
2. Select the `whatsapp_automate` repo → Render reads `render.yaml`
3. Fill in the secret env vars when prompted (see Step 3)

**Option B — Manual Web Service:**
1. **New + → Web Service** → connect the repo
2. Settings:
   - **Runtime:** Python
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Health check path:** `/healthz`
   - **Plan:** Free

## Step 3 — Set environment variables (Render dashboard → Environment)

| Key | Value |
|---|---|
| `GEMINI_API_KEY` | your AI Studio key |
| `GOOGLE_API_KEY` | same AI Studio key |
| `GOOGLE_GENAI_USE_VERTEXAI` | `0` |
| `ADK_MODEL` | `gemini-2.5-flash` |
| `DATABASE_URL` | your Neon connection string (`...?sslmode=require`) |

## Step 4 — Deploy & test

- Render builds and deploys automatically. When live you get a URL like
  `https://weavedesk-v5.onrender.com`.
- Open `https://weavedesk-v5.onrender.com/dev-ui/` for the **ADK web UI** — pick the
  `weavedesk_v5` agent and chat (simulate an incoming WhatsApp message as text).
- Health check: `https://weavedesk-v5.onrender.com/healthz` → `{"status":"ok"}`
- Or hit the API directly:

```bash
# create a session
curl -X POST https://weavedesk-v5.onrender.com/apps/weavedesk_v5/users/u1/sessions/s1

# send a message
curl -X POST https://weavedesk-v5.onrender.com/run \
  -H 'Content-Type: application/json' \
  -d '{
    "app_name": "weavedesk_v5",
    "user_id": "u1",
    "session_id": "s1",
    "new_message": {"role": "user", "parts": [{"text": "Quote for 60x60 cotton, 500 meters"}]}
  }'
```

---

## Notes & limits

- **Free tier sleeps** after 15 min idle and cold-starts (~1 min) on the next request.
- **Conversation sessions are ephemeral** (ADK default local storage; wiped on
  restart/redeploy). **Business data (persons, tickets) is durable in Neon.**
- **`send_whatsapp_message`** returns `{"error": "API Unreachable"}` in the cloud
  (no `:3002` bridge) — expected for this demo; the rest of the flow works end-to-end.
- **Local `.env`** for development goes in `weavedesk_v5/.env` (ADK auto-loads it).
  On Render, use the dashboard env vars instead — do not commit secrets.
