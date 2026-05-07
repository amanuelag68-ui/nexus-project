"""
NEXUS Workflow Agent
====================
Responsible for:
  - Creating ITSM tickets (simulates Jira/ServiceNow API)
  - Running automated remediation for eligible categories
  - Sending notifications (simulates Slack MCP)
  - Updating ticket status on completion
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import time
import uuid
from models import ClassificationResult, RetrievalResult, Ticket
from config import WORKFLOW_CONFIG, PRIORITY_LEVELS


class WorkflowAgent:
    """
    Agent 3: Workflow Automation.
    Handles ticket lifecycle and automated remediations.
    """

    name = "WorkflowAgent"

    def __init__(self):
        self.tickets: dict[str, Ticket] = {}
        self.ticket_counter = 1000
        self.automations_run = 0

    # ── Ticket Management ────────────────────────────────────────
    def create_ticket(
        self,
        user_text: str,
        classification: ClassificationResult,
        retrieval: RetrievalResult,
    ) -> Ticket:
        """Create a new ITSM ticket for the issue."""
        t0 = time.time()
        self.ticket_counter += 1
        ticket_id = f"{WORKFLOW_CONFIG['ticket_prefix']}-{self.ticket_counter}"

        ticket = Ticket(
            ticket_id=ticket_id,
            title=f"[{classification.category.replace('_', ' ').title()}] {user_text[:60]}",
            description=user_text,
            category=classification.category,
            priority=classification.priority,
            status="open",
        )

        # Auto-assign based on category
        ticket.assignee = self._route_to_team(classification.category)

        # Attempt automated remediation
        if classification.category in WORKFLOW_CONFIG["auto_remediate_categories"]:
            ticket = self._auto_remediate(ticket, retrieval)

        self.tickets[ticket_id] = ticket
        elapsed = round(time.time() - t0, 3)
        print(f"\n[{self.name}] Ticket created: {ticket_id} | priority={ticket.priority} | assignee={ticket.assignee} | auto={ticket.automation_applied} ({elapsed}s)")
        self._notify(ticket)
        return ticket

    def update_ticket(self, ticket_id: str, status: str, resolution: str = None) -> Ticket:
        """Update ticket status and resolution."""
        if ticket_id not in self.tickets:
            raise KeyError(f"Ticket {ticket_id} not found")
        ticket = self.tickets[ticket_id]
        ticket.status = status
        if resolution:
            ticket.resolution = resolution
        print(f"[{self.name}] Ticket {ticket_id} updated → status={status}")
        return ticket

    # ── Auto-Remediation ─────────────────────────────────────────
    def _auto_remediate(self, ticket: Ticket, retrieval: RetrievalResult) -> Ticket:
        """
        Simulate running an automated fix script.
        In production: calls AWS Lambda / Ansible playbook via MCP tool.
        """
        remediation_scripts = {
            "password_reset": "scripts/reset_ad_password.ps1",
            "email_issue":    "scripts/clear_ost_cache.ps1",
            "printer_problem": "scripts/restart_spooler.ps1",
        }

        script = remediation_scripts.get(ticket.category)
        if script:
            print(f"[{self.name}] Running automation: {script}")
            time.sleep(0.05)  # simulate execution
            ticket.automation_applied = True
            ticket.automation_result = f"Script {script} executed successfully. Exit code: 0."
            ticket.status = "resolved"
            ticket.resolution = ticket.automation_result
            self.automations_run += 1

        return ticket

    # ── Routing ──────────────────────────────────────────────────
    def _route_to_team(self, category: str) -> str:
        routing = {
            "password_reset":   "L1-IAM",
            "vpn_issue":        "L2-Network",
            "software_access":  "L1-Provisioning",
            "hardware_failure": "L2-Hardware",
            "network_outage":   "L2-Network",
            "email_issue":      "L1-Messaging",
            "printer_problem":  "L1-General",
            "security_alert":   "L3-Security",
            "unknown":          "L1-General",
        }
        return routing.get(category, "L1-General")

    # ── Notifications (simulates Slack MCP) ──────────────────────
    def _notify(self, ticket: Ticket):
        """Simulate Slack MCP notification."""
        sla = PRIORITY_LEVELS.get(ticket.priority, {}).get("sla_minutes", 240)
        channel = "#it-alerts" if ticket.priority in ("P1", "P2") else "#it-support"
        print(f"[{self.name}] [Slack MCP] → {channel}: Ticket {ticket.ticket_id} ({ticket.priority}) | SLA: {sla}min | Team: {ticket.assignee}")

    def stats(self) -> dict:
        statuses = {}
        for t in self.tickets.values():
            statuses[t.status] = statuses.get(t.status, 0) + 1
        return {
            "agent": self.name,
            "total_tickets": len(self.tickets),
            "automations_run": self.automations_run,
            "automation_rate": round(self.automations_run / max(len(self.tickets), 1), 3),
            "ticket_statuses": statuses,
        }
