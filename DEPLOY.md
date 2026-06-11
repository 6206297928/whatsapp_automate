# Deploying Weavedesk V5 to Vertex AI Agent Engine (free tier)

A step-by-step runbook to deploy this agent for **$0** using:

- **Vertex AI Agent Engine** — managed ADK runtime, free monthly tier, scales to zero
- **Google AI Studio** — free Gemini API tier for the LLM calls
- **Neon** — free, durable PostgreSQL

Testing is done via the Python SDK / `adk web` — **no WhatsApp bridge required**.

---

## Prerequisites (one-time)

1. **Google Cloud account** with billing enabled — https://cloud.google.com/free
   (Card needed for verification; $300 free credits, won't charge within free tier.)
2. **AI Studio API key** — https://aistudio.google.com/apikey
3. **Neon account + project** — https://neon.tech (free tier)
4. **gcloud CLI** installed and authenticated:
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

---

## Step 1 — Create the Neon database

1. In the Neon dashboard, create a project (any name).
2. Copy the **connection string** (it looks like
   `postgresql://user:pass@ep-xxxx.region.aws.neon.tech/dbname?sslmode=require`).

## Step 2 — Configure local env

```bash
cp .env.example weavedesk_v5/.env
# edit weavedesk_v5/.env: paste GEMINI_API_KEY (and GOOGLE_API_KEY), and the Neon DATABASE_URL
```

## Step 3 — Initialize the database (one time)

Creates the tables and seeds one demo customer + one demo vendor:

```bash
# uses DATABASE_URL from your shell/.env
export DATABASE_URL="postgresql://user:pass@ep-xxxx.region.aws.neon.tech/dbname?sslmode=require"
python weavedesk_v5/init_db.py
```

Expected output:
```
✅ Tables created (persons, tickets, ticket_vendors)
✅ Seeded customer: +910000000001
✅ Seeded vendor:   +910000000002
🎉 Database ready.
```

## Step 4 — Enable required Google Cloud APIs

```bash
gcloud services enable \
  aiplatform.googleapis.com \
  storage.googleapis.com \
  logging.googleapis.com
```

## Step 5 — Deploy to Agent Engine

Run from the repo root (the package `weavedesk_v5` is a subfolder here):

```bash
adk deploy agent_engine \
  --project=YOUR_PROJECT_ID \
  --region=us-central1 \
  weavedesk_v5 \
  --agent_engine_config_file=weavedesk_v5/.agent_engine_config.json
```

Deployment takes ~2-5 min and prints a resource name like:
`projects/PROJECT_NUMBER/locations/us-central1/reasoningEngines/ID`

## Step 6 — Test the deployed agent (no WhatsApp)

```python
import vertexai
from vertexai import agent_engines

vertexai.init(project="YOUR_PROJECT_ID", location="us-central1")
remote = list(agent_engines.list())[0]

# Simulate an incoming WhatsApp message as plain text
import asyncio
async def chat():
    async for event in remote.async_stream_query(
        message="Hi, I need a quote for 60x60 cotton fabric, 500 meters",
        user_id="+910000000001",   # the seeded demo customer
    ):
        print(event)
asyncio.run(chat())
```

## Step 7 — Clean up (avoid charges)

When done testing, delete the deployment:

```python
import vertexai
from vertexai import agent_engines
vertexai.init(project="YOUR_PROJECT_ID", location="us-central1")
for a in agent_engines.list():
    agent_engines.delete(resource_name=a.resource_name, force=True)
```

---

## Notes

- **Cost:** Agent Engine has a free monthly runtime tier and scales to zero
  (`min_instances: 0`). AI Studio's Gemini free tier covers the LLM calls. Neon is
  free. Delete the deployment when idle to be safe.
- **`send_whatsapp_message`** will return `{"error": "API Unreachable"}` in the cloud
  (no `:3002` bridge) — expected for this demo. The rest of the workflow (identity,
  classification, ticket creation in Neon) works end-to-end.
- **Long-term memory:** the agent runs with Agent-Engine-managed session memory.
  To enable persistent cross-session memory, turn on **Vertex AI Memory Bank** and the
  `auto_save_to_memory` callback will start persisting automatically.
- **Upgrade to real WhatsApp later:** point `send_whatsapp_message` at Meta's
  WhatsApp Cloud API (free conversation tier) instead of the local `:3002` bridge.
