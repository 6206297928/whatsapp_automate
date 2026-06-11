"""FastAPI entry point for deploying the Weavedesk V5 agent on Render.

ADK's `get_fast_api_app` discovers agents as subfolders of `agents_dir`. Here the
repo root is the agents_dir and `weavedesk_v5/` is the agent package, so the agent
is served (with the built-in ADK web UI) at the service URL.

Start command (Render):  uvicorn main:app --host 0.0.0.0 --port $PORT
"""
import os

from google.adk.cli.fast_api import get_fast_api_app

# Repo root — contains the `weavedesk_v5/` agent package as a subfolder.
AGENTS_DIR = os.path.dirname(os.path.abspath(__file__))

app = get_fast_api_app(
    agents_dir=AGENTS_DIR,
    # Conversation sessions use ADK's default local storage (ephemeral on Render's
    # free tier — resets on restart/redeploy). Business data (persons, tickets) is
    # durable in Neon via DATABASE_URL inside the agent's own DB layer.
    web=True,
    allow_origins=["*"],
)


@app.get("/healthz")
def healthz():
    return {"status": "ok", "agent": "weavedesk_v5"}
