"""
NEXUS Escalation Agent
======================
Responsible for:
  - Deciding whether to escalate to human L2/L3
  - Packaging full context for human agents
  - Routing to the correct specialist team
  - Logging escalation audit trail
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import time
from models import (
    ClassificationResult, RetrievalResult, Ticket,
    EscalationPackage, UserMessage
)
from llm import llm
from config import PRIORITY_LEVELS


TEAM_ROUTING = {
    "password_reset":   ("L1-IAM",        "Identity & Access Management team"),
    "vpn_issue":        ("L2-Network",     "Network Infrastructure team"),
    "software_access":  ("L1-Provisioning","IT Provisioning team"),
    "hardware_failure": ("L2-Hardware",    "Hardware & Depot team"),
    "network_outage":   ("L2-Network",     "Network Operations Centre (NOC)"),
    "email_issue":      ("L2-Messaging",   "Messaging & Collaboration team"),
    "printer_problem":  ("L1-General",     "General IT Support desk"),
    "security_alert":   ("L3-Security",    "Security Operations Centre (SOC)"),
    "unknown":          ("L2-General",     "Tier-2 General IT"),
}


class EscalationAgent:
    """
    Agent 4: Escalation & Human Handoff.
    Packages full context and routes to the right team.
    """

    name = "EscalationAgent"

    def __init__(self):
        self.escalations: list[EscalationPackage] = []

    def should_escalate(
        self,
        classification: ClassificationResult,
        retrieval: RetrievalResult,
    ) -> tuple[bool, str]:
        """
        Determine if escalation is needed and why.
        Returns (should_escalate: bool, reason: str)
        """
        reasons = []

        if classification.priority == "P1":
            reasons.append("P1 critical priority — mandatory escalation")

        if classification.category == "security_alert":
            reasons.append("Security incident — always escalate to SOC")

        if classification.needs_escalation:
            reasons.append("Intake agent flagged for escalation (low confidence or sentiment trigger)")

        if retrieval.fallback_to_human:
            reasons.append(f"KB confidence too low ({retrieval.confidence:.2f} < threshold)")

        if not reasons:
            return False, ""

        return True, " | ".join(reasons)

    def escalate(
        self,
        message: UserMessage,
        classification: ClassificationResult,
        retrieval: RetrievalResult,
        ticket: Ticket,
        reason: str,
    ) -> EscalationPackage:
        """Build and log an escalation package."""
        t0 = time.time()
        print(f"\n[{self.name}] Building escalation package for ticket={ticket.ticket_id}")
        print(f"[{self.name}] Reason: {reason}")

        team_id, team_desc = TEAM_ROUTING.get(classification.category, TEAM_ROUTING["unknown"])

        # Use LLM to write escalation summary
        summary_prompt = (
            f"Write a concise L2 handoff summary.\n"
            f"Issue: {message.content}\nCategory: {classification.category}\n"
            f"Priority: {classification.priority}\nReason: {reason}"
        )
        priority_justification = llm.complete(summary_prompt, task_type="summarize")

        package = EscalationPackage(
            ticket=ticket,
            original_message=message.content,
            classification=classification,
            kb_attempt=retrieval if retrieval.documents else None,
            failure_reason=reason,
            suggested_team=f"{team_id} — {team_desc}",
            priority_justification=priority_justification,
        )

        # Update ticket
        ticket.status = "escalated"
        ticket.assignee = team_id

        self.escalations.append(package)
        elapsed = round(time.time() - t0, 3)
        print(f"[{self.name}] Escalated to: {team_id} ({elapsed}s)")
        self._notify_team(package, team_id)
        return package

    def _notify_team(self, package: EscalationPackage, team_id: str):
        """Simulate PagerDuty / Slack MCP notification to receiving team."""
        p = package.ticket.priority
        channel = "#escalations-p1" if p == "P1" else "#escalations"
        print(f"[{self.name}] [PagerDuty MCP] → {team_id} paged | ticket={package.ticket.ticket_id} | priority={p}")
        print(f"[{self.name}] [Slack MCP] → {channel}: Escalation {package.ticket.ticket_id} assigned to {team_id}")

    def stats(self) -> dict:
        by_priority = {}
        by_category = {}
        for e in self.escalations:
            p = e.classification.priority
            c = e.classification.category
            by_priority[p] = by_priority.get(p, 0) + 1
            by_category[c] = by_category.get(c, 0) + 1
        return {
            "agent": self.name,
            "total_escalations": len(self.escalations),
            "by_priority": by_priority,
            "by_category": by_category,
        }
