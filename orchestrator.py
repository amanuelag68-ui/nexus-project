"""
NEXUS Orchestrator
==================
Central coordinator that manages the full agent pipeline:

  UserMessage
      ↓
  [IntakeAgent]     → ClassificationResult
      ↓
  [KnowledgeAgent]  → RetrievalResult
      ↓
  [WorkflowAgent]   → Ticket
      ↓
  [EscalationAgent] → EscalationPackage (if needed)
      ↓
  AgentResponse     → returned to user/API
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import time
from models import UserMessage, AgentResponse
from agents.intake_agent import IntakeAgent
from agents.knowledge_agent import KnowledgeAgent
from agents.workflow_agent import WorkflowAgent
from agents.escalation_agent import EscalationAgent


class Orchestrator:
    """
    NEXUS Master Orchestrator.
    Routes messages through the agent pipeline and returns a unified response.
    """

    def __init__(self):
        self.intake     = IntakeAgent()
        self.knowledge  = KnowledgeAgent()
        self.workflow   = WorkflowAgent()
        self.escalation = EscalationAgent()
        self.total_requests = 0
        self.total_resolved = 0

    def handle(self, message: UserMessage) -> AgentResponse:
        """
        Main entry point. Process a user message through the full pipeline.
        Returns an AgentResponse with the final answer and ticket.
        """
        t_start = time.time()
        agents_used = []
        print(f"\n{'='*60}")
        print(f"NEXUS ORCHESTRATOR — Session {message.session_id}")
        print(f"{'='*60}")

        # ── Step 1: Intake & Classification ─────────────────────
        classification = self.intake.process(message)
        agents_used.append("IntakeAgent")

        # ── Step 2: Knowledge Retrieval ──────────────────────────
        retrieval = self.knowledge.answer(message.content, classification)
        agents_used.append("KnowledgeAgent")

        # ── Step 3: Workflow / Ticket Creation ───────────────────
        ticket = self.workflow.create_ticket(message.content, classification, retrieval)
        agents_used.append("WorkflowAgent")

        # ── Step 4: Escalation Decision ──────────────────────────
        escalated = False
        escalation_package = None

        # If workflow already auto-resolved the ticket, skip escalation
        if ticket.automation_applied and ticket.status == "resolved":
            should_esc = False
            esc_reason = ""
        else:
            should_esc, esc_reason = self.escalation.should_escalate(classification, retrieval)

        if should_esc:
            escalation_package = self.escalation.escalate(
                message, classification, retrieval, ticket, esc_reason
            )
            agents_used.append("EscalationAgent")
            escalated = True
            answer = (
                f"⚠️ Your issue has been escalated to the {escalation_package.suggested_team}.\n\n"
                f"**Ticket:** {ticket.ticket_id} ({ticket.priority})\n"
                f"**Reason:** {esc_reason}\n\n"
                f"A specialist will contact you within "
                f"{self._sla_text(classification.priority)}. "
                f"You'll receive a Slack/email notification when assigned."
            )
        else:
            # Use the KB answer; fall back to a generic message if empty
            answer = retrieval.answer or (
                f"Your ticket {ticket.ticket_id} has been created and assigned to "
                f"{ticket.assignee}. Resolution steps are being prepared."
            )
            if ticket.automation_applied:
                answer += f"\n\n✓ **Auto-remediation applied:** {ticket.automation_result}"
            ticket.status = "resolved" if not retrieval.fallback_to_human else "in_progress"
            self.total_resolved += 1

        self.total_requests += 1
        elapsed = round(time.time() - t_start, 3)

        response = AgentResponse(
            session_id=message.session_id,
            user_message=message.content,
            answer=answer,
            ticket=ticket,
            escalated=escalated,
            escalation_package=escalation_package,
            resolution_time_sec=elapsed,
            agents_used=agents_used,
            confidence=retrieval.confidence,
            sources=retrieval.sources,
        )

        print(f"\n[Orchestrator] ✓ Done in {elapsed}s | escalated={escalated} | ticket={ticket.ticket_id}")
        return response

    def _sla_text(self, priority: str) -> str:
        sla_map = {"P1": "15 minutes", "P2": "1 hour", "P3": "4 hours", "P4": "next business day"}
        return sla_map.get(priority, "4 hours")

    def full_stats(self) -> dict:
        return {
            "orchestrator": {
                "total_requests": self.total_requests,
                "total_resolved": self.total_resolved,
                "resolution_rate": round(self.total_resolved / max(self.total_requests, 1), 3),
            },
            **{k: v for d in [
                self.intake.stats(),
                self.knowledge.stats(),
                self.workflow.stats(),
                self.escalation.stats(),
            ] for k, v in {d["agent"]: d}.items()},
        }
