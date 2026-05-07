"""
NEXUS Data Models
=================
Shared dataclasses used across all agents.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import datetime
import uuid


def _now() -> str:
    return datetime.datetime.utcnow().isoformat()


@dataclass
class UserMessage:
    """Incoming message from the end user."""
    content: str
    user_id: str
    channel: str = "web"          # web | slack | teams | email
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: str = field(default_factory=_now)


@dataclass
class ClassificationResult:
    """Output from IntakeAgent."""
    category: str
    priority: str                  # P1–P4
    confidence: float              # 0.0–1.0
    keywords: List[str]
    sentiment: str                 # frustrated | neutral | positive
    needs_escalation: bool = False
    raw_text: str = ""


@dataclass
class KBDocument:
    """A knowledge-base article."""
    doc_id: str
    title: str
    content: str
    category: str
    tags: List[str]
    resolution_steps: List[str]
    avg_resolution_time_min: float = 5.0


@dataclass
class RetrievalResult:
    """Output from KnowledgeAgent."""
    documents: List[KBDocument]
    top_similarity: float
    answer: str
    sources: List[str]
    confidence: float
    fallback_to_human: bool = False


@dataclass
class Ticket:
    """ITSM ticket created by WorkflowAgent."""
    ticket_id: str
    title: str
    description: str
    category: str
    priority: str
    status: str = "open"          # open | in_progress | resolved | escalated
    assignee: Optional[str] = None
    resolution: Optional[str] = None
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    automation_applied: bool = False
    automation_result: Optional[str] = None


@dataclass
class EscalationPackage:
    """Context bundle sent to human L2/L3 agent."""
    ticket: Ticket
    original_message: str
    classification: ClassificationResult
    kb_attempt: Optional[RetrievalResult]
    failure_reason: str
    suggested_team: str
    priority_justification: str
    created_at: str = field(default_factory=_now)


@dataclass
class AgentResponse:
    """Final unified response returned to the user."""
    session_id: str
    user_message: str
    answer: str
    ticket: Optional[Ticket]
    escalated: bool
    escalation_package: Optional[EscalationPackage]
    resolution_time_sec: float
    agents_used: List[str]
    confidence: float
    sources: List[str]
    timestamp: str = field(default_factory=_now)
