"""
NEXUS Configuration
===================
Central config for all agents, thresholds, and system parameters.
"""

from dataclasses import dataclass, field
from typing import Dict, List
import datetime

# ── Priority Levels ──────────────────────────────────────────────
PRIORITY_LEVELS = {
    "P1": {"label": "Critical",  "sla_minutes": 15,  "auto_escalate": True},
    "P2": {"label": "High",      "sla_minutes": 60,  "auto_escalate": True},
    "P3": {"label": "Medium",    "sla_minutes": 240, "auto_escalate": False},
    "P4": {"label": "Low",       "sla_minutes": 1440,"auto_escalate": False},
}

# ── Issue Categories ─────────────────────────────────────────────
ISSUE_CATEGORIES = [
    "password_reset",
    "vpn_issue",
    "software_access",
    "hardware_failure",
    "network_outage",
    "email_issue",
    "printer_problem",
    "security_alert",
    "unknown",
]

# ── RAG Config ───────────────────────────────────────────────────
RAG_CONFIG = {
    "chunk_size": 512,
    "chunk_overlap": 64,
    "top_k": 5,
    "min_similarity": 0.20,
    "embedding_dim": 64,   # reduced for simulation
}

# ── Agent Config ─────────────────────────────────────────────────
AGENT_CONFIG = {
    "max_retries": 2,
    "confidence_threshold": 0.38,
    "escalation_threshold": 0.40,
    "timeout_seconds": 30,
}

# ── Workflow Config ──────────────────────────────────────────────
WORKFLOW_CONFIG = {
    "auto_remediate_categories": ["password_reset", "email_issue", "printer_problem"],
    "ticket_prefix": "NXS",
    "notification_channels": ["slack", "email"],
}
