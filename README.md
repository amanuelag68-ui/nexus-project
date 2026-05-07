[README.md](https://github.com/user-attachments/files/27493481/README.md)
# NEXUS — AI-Powered IT Support Multi-Agent System

> **Capstone Project · IT Support AI Systems · 2026**

NEXUS is a multi-agent AI system that transforms enterprise IT support. It replaces manual Level-1 triage with an intelligent pipeline of four coordinated agents — Intake, Knowledge, Workflow, and Escalation — each specialising in a distinct function.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Running the Tests](#running-the-tests)
- [Configuration](#configuration)
- [Agent Reference](#agent-reference)
- [RAG Pipeline](#rag-pipeline)
- [MCP Integrations](#mcp-integrations)
- [Switching to Production](#switching-to-production)
- [Test Results](#test-results)
- [Scaling](#scaling)

---

## Overview

| Metric | Value |
|---|---|
| Test pass rate | **100%** (8/8 scenarios, 56/56 checks) |
| Classification accuracy | **100%** (8 categories, correct priority every time) |
| Auto-resolution rate | **75%** (6/8 tickets resolved without human escalation) |
| Avg. pipeline latency | **19 ms** per request |
| RAG confidence range | 0.476 – 0.696 across all categories |
| LLM backend (prod) | Anthropic Claude claude-sonnet-4-20250514 |
| Embedding backend (prod) | OpenAI text-embedding-ada-002 → Pinecone |

---

## Architecture

```
UserMessage
    │
    ▼
┌─────────────────────────────────────────────────┐
│               ORCHESTRATOR                       │
│                                                  │
│  ┌─────────────┐    ┌──────────────────────┐    │
│  │ IntakeAgent │───▶│   KnowledgeAgent     │    │
│  │             │    │   (RAG pipeline)     │    │
│  │ • NLU class │    │ • TF-IDF / ada-002   │    │
│  │ • Priority  │    │ • Pinecone search    │    │
│  │ • Sentiment │    │ • LLM synthesis      │    │
│  └─────────────┘    └──────────────────────┘    │
│         │                      │                 │
│         ▼                      ▼                 │
│  ┌──────────────┐   ┌─────────────────────────┐ │
│  │WorkflowAgent │   │    EscalationAgent      │ │
│  │              │   │                         │ │
│  │ • Tickets    │   │ • P1 / security gate    │ │
│  │ • Auto-fix   │   │ • Context packaging     │ │
│  │ • Slack MCP  │   │ • PagerDuty / Slack MCP │ │
│  └──────────────┘   └─────────────────────────┘ │
└─────────────────────────────────────────────────┘
    │
    ▼
AgentResponse  →  user
```

### Agent Pipeline (sequential)

1. `IntakeAgent.process(message)` → `ClassificationResult`
2. `KnowledgeAgent.answer(text, classification)` → `RetrievalResult`
3. `WorkflowAgent.create_ticket(...)` → `Ticket`
4. If auto-remediated & resolved → **skip escalation**
5. Else `EscalationAgent.should_escalate(...)` → `(bool, reason)`
6. If escalate → `EscalationAgent.escalate(...)` → `EscalationPackage`
7. `Orchestrator` assembles and returns `AgentResponse`

---

## Project Structure

```
nexus/
├── config.py                # Priority levels, RAG thresholds, routing config
├── models.py                # Typed dataclasses shared across all agents
├── llm.py                   # MockLLM (swap for Anthropic client in production)
├── orchestrator.py          # Master coordinator — runs the full 4-agent pipeline
│
├── agents/
│   ├── intake_agent.py      # NLU classification + priority + sentiment
│   ├── knowledge_agent.py   # RAG retrieval + LLM answer synthesis
│   ├── workflow_agent.py    # Ticket lifecycle + auto-remediation + Slack MCP
│   └── escalation_agent.py  # Escalation decision tree + PagerDuty MCP
│
├── rag/
│   └── engine.py            # TF-IDF index, cosine search, 8 KB seed articles
│
├── tests/
│   └── test_scenarios.py    # 8 integration tests, 7 checks each (56 assertions)
│
├── outputs/
│   └── generate_charts.py   # matplotlib charts for the technical document
│
├── requirements.txt         # Dependencies (demo needs only numpy/pandas/matplotlib)
└── README.md                # This file
```

---

## Quick Start

### 1. Clone

```bash
git clone https://github.com/nexus-itsupport/nexus-multiagent.git
cd nexus-multiagent
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

> **No API keys needed for demo mode.** The system uses `MockLLM` which runs fully offline.

### 3. Run a single request

```python
import sys
sys.path.insert(0, 'nexus')

from models import UserMessage
from orchestrator import Orchestrator

orch = Orchestrator()
msg  = UserMessage(content="My VPN keeps disconnecting every 10 minutes.", user_id="emp_001")
resp = orch.handle(msg)

print(resp.answer)
print(f"Ticket: {resp.ticket.ticket_id} | Escalated: {resp.escalated}")
```

---

## Running the Tests

```bash
cd nexus
python tests/test_scenarios.py
```

Expected output:

```
======================================================================
  NEXUS TEST SUITE — Integration Scenarios
======================================================================

  Running TC-01: Password Reset — Auto-Remediated  ✅ PASS
  Running TC-02: VPN Connectivity Issue             ✅ PASS
  Running TC-03: Software License Request           ✅ PASS
  Running TC-04: Hardware Failure — P1 Escalation  ✅ PASS
  Running TC-05: Network Outage                     ✅ PASS
  Running TC-06: Email / Outlook Sync Issue         ✅ PASS
  Running TC-07: Printer Problem                    ✅ PASS
  Running TC-08: Security Alert — Always Escalates ✅ PASS

  Total: 8  |  Passed: 8 (100%)  |  Failed: 0
  Avg Time: 0.019s per scenario
```

### Generate charts

```bash
python outputs/generate_charts.py
# Writes 6 PNG charts to nexus/outputs/
```

---

## Configuration

All tunable parameters live in `config.py`:

```python
# Priority SLAs
PRIORITY_LEVELS = {
    "P1": {"label": "Critical",  "sla_minutes": 15,  "auto_escalate": True},
    "P2": {"label": "High",      "sla_minutes": 60,  "auto_escalate": True},
    "P3": {"label": "Medium",    "sla_minutes": 240, "auto_escalate": False},
    "P4": {"label": "Low",       "sla_minutes": 1440,"auto_escalate": False},
}

# RAG tuning
RAG_CONFIG = {
    "chunk_size": 512,        # tokens per KB chunk
    "chunk_overlap": 64,      # overlap between chunks
    "top_k": 5,               # docs to retrieve per query
    "min_similarity": 0.20,   # cosine sim floor for inclusion
}

# Agent thresholds
AGENT_CONFIG = {
    "confidence_threshold": 0.38,   # below this → escalate
    "escalation_threshold": 0.40,   # intake confidence gate
    "max_retries": 2,
}

# Auto-remediation eligibility
WORKFLOW_CONFIG = {
    "auto_remediate_categories": ["password_reset", "email_issue", "printer_problem"],
}
```

---

## Agent Reference

### IntakeAgent

Classifies the user message into one of 9 categories and assigns a priority level.

```python
from agents.intake_agent import IntakeAgent
from models import UserMessage

agent = IntakeAgent()
result = agent.process(UserMessage(content="I can't log in", user_id="u1"))
# result.category   → "password_reset"
# result.priority   → "P3"
# result.confidence → 0.95
# result.sentiment  → "frustrated"
```

**Categories:** `password_reset` · `vpn_issue` · `software_access` · `hardware_failure` · `network_outage` · `email_issue` · `printer_problem` · `security_alert` · `unknown`

---

### KnowledgeAgent

Queries the RAG engine and synthesises a resolution using the top retrieved KB article.

```python
from agents.knowledge_agent import KnowledgeAgent

agent = KnowledgeAgent()
result = agent.answer(user_text, classification)
# result.answer         → synthesised resolution steps
# result.top_similarity → 0.617
# result.confidence     → 0.679
# result.sources        → ["KB-001: Password Reset Guide"]
# result.fallback_to_human → False
```

---

### WorkflowAgent

Creates ITSM tickets and runs auto-remediation scripts for eligible categories.

```python
from agents.workflow_agent import WorkflowAgent

agent = WorkflowAgent()
ticket = agent.create_ticket(user_text, classification, retrieval)
# ticket.ticket_id          → "NXS-1001"
# ticket.status             → "resolved" (if auto-remediated)
# ticket.automation_applied → True
# ticket.assignee           → "L1-IAM"
```

**Auto-remediation scripts:**

| Category | Script | Avg time |
|---|---|---|
| `password_reset` | `reset_ad_password.ps1` | ~90s |
| `email_issue` | `clear_ost_cache.ps1` | ~2min |
| `printer_problem` | `restart_spooler.ps1` | ~30s |

---

### EscalationAgent

Decides whether to escalate and packages full context for the receiving team.

```python
from agents.escalation_agent import EscalationAgent

agent = EscalationAgent()
should_esc, reason = agent.should_escalate(classification, retrieval)
if should_esc:
    package = agent.escalate(message, classification, retrieval, ticket, reason)
    # package.suggested_team → "L3-Security — Security Operations Centre (SOC)"
    # package.failure_reason → "P1 critical priority — mandatory escalation"
```

**Escalation triggers (any one is sufficient):**

- Priority is `P1`
- Category is `security_alert`
- IntakeAgent confidence `< 0.40`
- KnowledgeAgent `fallback_to_human = True`

---

## RAG Pipeline

```
User query
    │
    ▼ enrich with category vocabulary boost
    │
    ▼ embed (TF-IDF BoW in demo / ada-002 in production)
    │
    ▼ cosine similarity search (in-memory / Pinecone)
    │
    ▼ filter by min_similarity (0.20)
    │
    ▼ top-k documents ranked by score
    │
    ▼ LLM answer synthesis (MockLLM / Claude claude-sonnet-4-20250514)
    │
    ▼ RetrievalResult → KnowledgeAgent → Orchestrator
```

The knowledge base (`rag/engine.py`) is seeded with 8 articles:

| Doc ID | Category | Avg Resolution |
|---|---|---|
| KB-001 | password_reset | 2.5 min |
| KB-002 | vpn_issue | 8.0 min |
| KB-003 | software_access | 15.0 min |
| KB-004 | network_outage | 20.0 min |
| KB-005 | email_issue | 12.0 min |
| KB-006 | printer_problem | 7.0 min |
| KB-007 | hardware_failure | 45.0 min |
| KB-008 | security_alert | 60.0 min |

---

## MCP Integrations

NEXUS uses the Anthropic **Model Context Protocol** to call external services as typed tools:

| MCP Server | Methods used |
|---|---|
| Jira MCP | `create_ticket`, `update_status`, `search_issues` |
| Slack MCP | `send_message` (P1/P2 → `#it-alerts`, P3/P4 → `#it-support`) |
| ServiceNow MCP | `open_incident`, `assign_group`, `close_ticket` |
| PagerDuty MCP | `trigger_incident`, `escalate`, `acknowledge_alert` |
| Datadog MCP | `query_metrics`, `get_alerts`, `pull_logs` |
| Active Directory | `reset_password`, `unlock_account`, `get_user_info` |

All MCP calls are authenticated via OAuth 2.0 and fully logged to PostgreSQL.

---

## Switching to Production

### 1. LLM — replace MockLLM with Claude

In `llm.py`, replace the `complete()` method:

```python
import anthropic, os

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

def complete(self, prompt: str, task_type: str = "general") -> str:
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system="You are NEXUS, an expert IT support AI agent.",
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text
```

### 2. Embeddings — replace TF-IDF with ada-002

In `rag/engine.py`, replace `_embed()`:

```python
from openai import OpenAI
_oai = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

def _embed(self, text: str) -> np.ndarray:
    resp = _oai.embeddings.create(model="text-embedding-ada-002", input=text)
    return np.array(resp.data[0].embedding, dtype=np.float32)
```

### 3. Vector store — replace in-memory with Pinecone

In `rag/engine.py`, replace `retrieve()`:

```python
import pinecone

_pc    = pinecone.Pinecone(api_key=os.environ["PINECONE_API_KEY"])
_index = _pc.Index("nexus-kb")

def retrieve(self, query: str, top_k: int = 3):
    q_vec   = self._embed(query).tolist()
    results = _index.query(vector=q_vec, top_k=top_k, include_metadata=True)
    return [(self._doc_from_metadata(m.metadata), m.score) for m in results.matches]
```

### 4. Environment variables

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...
export PINECONE_API_KEY=...
export PINECONE_ENV=us-east-1-aws
export JIRA_URL=https://yourorg.atlassian.net
export JIRA_TOKEN=...
export SLACK_BOT_TOKEN=xoxb-...
export PAGERDUTY_API_KEY=...
```

---

## Test Results

All 8 scenarios pass 7 independent checks each (56 total assertions):

| Check | Result |
|---|---|
| `category_match` | 8 / 8 |
| `priority_match` | 8 / 8 |
| `escalation_match` | 8 / 8 |
| `automation_match` | 8 / 8 |
| `has_ticket` | 8 / 8 |
| `has_answer` | 8 / 8 |
| `resolved_in_time` | 8 / 8 |

---

## Scaling

| Tier | Concurrent Users | Orchestrator Instances | Notes |
|---|---|---|---|
| MVP | 500 | 3 | Single Pinecone index, 1 Redis node |
| Growth | 2,000 | 8 | Read replicas on PostgreSQL |
| Scale | 5,000+ | 15–20 | Horizontal Pinecone sharding, SQS queues |

P99 response latency target: **< 500ms** (excluding auto-remediation scripts).

---

## License

Academic use only. Not for production deployment without security review.

---

*Built with Python 3.12 · NumPy · Matplotlib · Anthropic Claude · LangGraph · Pinecone · MCP*
