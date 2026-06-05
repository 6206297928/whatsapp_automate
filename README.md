# whatsapp_automate — Weavedesk ADK V5

A **production-grade WhatsApp business-automation agent** built on **Google's Agent Development Kit (ADK)** and powered by **Gemini 2.5 Flash**. It automates the end-to-end B2B textile/fabric procurement workflow: customers send Requests for Quotation (RFQs) over WhatsApp, the agent understands them (text **and** fabric-tag images), opens tickets, routes them to vendors, validates vendor replies, and closes the loop with the customer — autonomously.

---

## What it does

- **Customer flow** — A customer sends a WhatsApp message (text and/or a photo of a fabric spec tag). The agent runs OCR on the image, classifies whether it's a genuine RFQ, creates a ticket (`IT-YYMMDD-Loc-NNNN`), and confirms back to the customer.
- **Vendor flow** — A vendor replies with pricing/delivery. The agent validates the reply, matches it to the ticket, records the response, and notifies the customer.
- **Conversational** — Remembers prior context, so follow-ups like *"why was no ticket created?"* get a real, contextual answer instead of a canned script.

It's effectively an **autonomous helpdesk + procurement broker living inside WhatsApp**.

---

## Agentic AI capabilities

| Capability | How it's implemented |
|---|---|
| **Autonomous tool orchestration** | An `LlmAgent` decides which of 9 tools to call, and in what order, based on context (customer vs. vendor, image present, valid query). |
| **Multimodal perception** | Gemini Vision OCR extracts fabric specs (Sort No, composition, EPIxPPI, weave) from tag photos. |
| **Function calling** | 9 real side-effecting tools: DB reads/writes, ticket generation, outbound WhatsApp. |
| **Dual-layer memory** | `InMemorySessionService` (per-session working memory) + `InMemoryMemoryService` (cross-session recall); `auto_save_to_memory()` persists every turn, `preload_memory` recalls prior conversations. |
| **Context optimization** | `EventsCompactionConfig(compaction_interval=3, overlap_size=1)` compacts history every 3 turns. |
| **Reliability** | Retry with exponential backoff on 429/500/503/504. |
| **Observability** | Built-in ADK `LoggingPlugin` traces every decision and tool call. |
| **Stateful runtime** | RAM-backed state retained across requests until process restart; drop-in upgrade path to durable backends. |

---

## Architecture

```
WhatsApp message (text + optional image)
        │
        ▼
   ADK Runner  ──  InMemorySessionService / InMemoryMemoryService
        │
        ▼
WeavedeskV5_Production  (LlmAgent · gemini-2.5-flash)
        │
        ├─ preload_memory            recall prior context
        ├─ fetch_user                identify customer / vendor   (PostgreSQL)
        ├─ extract_text_from_image   OCR fabric tags              (Gemini Vision)
        ├─ classify_customer_message is this a real RFQ?          (Gemini)
        ├─ validate_vendor_reply     parse vendor pricing/ticket  (Gemini)
        ├─ create_ticket             open RFQ ticket              (PostgreSQL)
        ├─ fetch_ticket_by_number    look up a ticket             (PostgreSQL)
        ├─ update_ticket_vendor      record vendor response       (PostgreSQL)
        └─ send_whatsapp_message     reply / notify               (REST :3002)
        │
        ▼
PostgreSQL  ──  persons · tickets · ticket_vendors
```

---

## Agentic AI engineering

End-to-end agent architecture techniques implemented in this project:

**1. Agent Orchestration Layer** — A reasoning-driven `LlmAgent` (`WeavedeskV5_Production`) that autonomously plans and sequences tool calls based on runtime context, with no hardcoded control flow. ADK `App` + `Runner` manage the execution lifecycle.

**2. Tool Calling / Function Calling** — 9 structured tools (DB reads/writes, OCR, classification, validation, outbound messaging) exposed to the LLM as typed callable functions. Tools share state via `ToolContext`, enabling stateful multi-step workflows.

**3. Context Engineering — Compaction** — `EventsCompactionConfig(compaction_interval=3, overlap_size=1)` compacts conversation history every 3 turns with 1-turn overlap, preventing token-context bloat while preserving continuity.

**4. Dual-Layer Memory Management**
- *Per-session (working) memory:* `InMemorySessionService` — isolated state within a single invocation (image data, user identity, classifier results).
- *Cross-session (long-term) memory:* `InMemoryMemoryService` + an `after_agent_callback` (`auto_save_to_memory`) persisting every turn, with `preload_memory` for recall across sessions.

**5. Multimodal Perception (Vision)** — Gemini Vision OCR (`extract_text_from_image`) extracts structured data from images, fusing visual + textual context into the agent's reasoning.

**6. Structured Prompt Engineering** — 4 specialized system prompts (root orchestrator + 3 task-specific JSON-constrained classifiers/extractors) enforcing deterministic, parseable LLM outputs.

**7. Reliability & Resilience** — LLM-call retry with exponential backoff (5 attempts) handling rate-limit/transient errors (HTTP 429/500/503/504).

**8. Observability** — ADK `LoggingPlugin` traces agent decisions, tool invocations, and model calls.

**9. Stateful In-Memory Runtime** — Both state layers are RAM-backed, making the system stateful for the lifetime of the running process: per-session and cross-session memory persist across requests until the process restarts. Architected for drop-in upgrade to durable backends (`DatabaseSessionService` / `VertexAiMemoryBankService`) for cross-restart, multi-instance persistence.

---

## Tech stack

- **Framework:** Google ADK (`google-adk` ≥ 1.0.0)
- **LLM:** Gemini 2.5 Flash (`google-genai`) — multimodal, fast, low-cost
- **Database:** PostgreSQL via SQLAlchemy ORM
- **HTTP:** httpx (async) for the WhatsApp REST bridge
- **Runtime:** Python 3.11+, `uv`

---

## Project structure

```
weavedesk_adk_v5/
├── agent.py        # LlmAgent definition, App, Runner, memory callback
├── tools.py        # 9 async tools (DB, OCR, classification, WhatsApp)
├── prompts.py      # 4 system prompts (classifier, validator, extractor, root)
├── database.py     # SQLAlchemy ORM: Person, Ticket, TicketVendor
├── __init__.py
├── .gitignore
└── README.md
```

---

## Setup & run

1. **Install dependencies**
   ```bash
   uv venv && source .venv/bin/activate
   uv pip install google-adk google-genai sqlalchemy httpx python-dotenv
   ```

2. **Configure environment** — create a `.env` file (not committed):
   ```bash
   GEMINI_API_KEY=your_gemini_api_key
   DATABASE_URL=postgresql://user:password@localhost:5432/yourdb
   ```

3. **Launch the ADK web UI**
   ```bash
   DATABASE_URL="postgresql://user:password@localhost:5432/yourdb" \
   uv run adk web --log_level DEBUG
   ```

---

## Configuration

| Variable | Purpose |
|---|---|
| `GEMINI_API_KEY` | Google Generative AI credentials |
| `DATABASE_URL` | PostgreSQL connection string |

> **Note:** `.env`, `*.db`, `.adk/`, and `__pycache__/` are git-ignored. Never commit secrets.

---

## Roadmap

- **Multi-agent / A2A** — split into Customer, Vendor, and Orchestrator agents for real-time vendor inventory checks.
- **Human-in-the-loop** approval gates for high-value quotes.
- **Distributed memory** (Firestore / Vertex) for multi-instance, horizontally-scaled deployment.

---

*Built with [Google Agent Development Kit](https://adk.dev/).*
