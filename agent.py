import os
import logging

# PERFECTED IMPORTS BASED ON DAY 3/DAY 4 NOTEBOOKS
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.memory import InMemoryMemoryService
from google.adk.tools import load_memory, preload_memory
from google.adk.apps.app import App, EventsCompactionConfig
from google.adk.plugins.logging_plugin import LoggingPlugin

# Restored all tools from V4
from .tools import (
    fetch_user,
    extract_text_from_image,
    classify_customer_message,
    validate_vendor_reply,
    create_ticket,
    fetch_ticket_by_number,
    update_ticket_vendor,
    send_whatsapp_message,
)
from .prompts import ROOT_AGENT_INSTRUCTION, RETRY_CONFIG

# Configure standard python logging to capture the plugin output
logging.basicConfig(level=logging.INFO)

# 1. Automatic Memory Ingestion Callback (V5 Feature)
async def auto_save_to_memory(callback_context):
    """Saves every turn to long-term memory automatically.

    Defensive: when deployed to Vertex AI Agent Engine, a memory service is only
    present if Memory Bank is enabled. Skip gracefully if it is unavailable so the
    agent keeps working with session-only memory.
    """
    try:
        memory_service = callback_context._invocation_context.memory_service
        if memory_service is not None:
            await memory_service.add_session_to_memory(
                callback_context._invocation_context.session
            )
    except Exception as exc:  # noqa: BLE001 - never let memory save break a turn
        logging.warning(f"Skipped long-term memory save: {exc}")

# 2. Agent Definition
root_agent = LlmAgent(
    model=Gemini(model="gemini-2.5-flash", retry_options=RETRY_CONFIG),
    name="WeavedeskV5_Production",
    instruction=ROOT_AGENT_INSTRUCTION,
    tools=[
        preload_memory,
        fetch_user,
        extract_text_from_image,
        classify_customer_message,
        validate_vendor_reply,
        create_ticket,
        fetch_ticket_by_number,
        update_ticket_vendor,
        send_whatsapp_message
    ],
    after_agent_callback=auto_save_to_memory,
)

# 3. App Definition with Context Compaction and Plugins
weavedesk_app = App(
    name="weavedesk_v5_app",
    root_agent=root_agent,
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=3,
        overlap_size=1
    ),
    plugins=[LoggingPlugin()],  # <--- MOVED HERE
)

# 4. Initialize Services
session_service = InMemorySessionService()
memory_service = InMemoryMemoryService()

# 5. Runner with Production Observability
runner = Runner(
    app=weavedesk_app,
    session_service=session_service,
    memory_service=memory_service,
    # No plugins here anymore!
)
