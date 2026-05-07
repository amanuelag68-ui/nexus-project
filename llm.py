"""
NEXUS Mock LLM Layer
====================
Simulates Anthropic Claude API responses for demo/testing.
In production, replace MockLLM.complete() with:

    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text
"""

import json
import re
import random
from typing import Dict, Any


class MockLLM:
    """
    Deterministic mock of Claude claude-sonnet-4-20250514.
    Routes prompts to specialised handlers based on task_type tag.
    """

    def complete(self, prompt: str, task_type: str = "general") -> str:
        handlers = {
            "classify":   self._handle_classify,
            "answer":     self._handle_answer,
            "summarize":  self._handle_summarize,
            "escalation": self._handle_escalation,
            "general":    self._handle_general,
        }
        handler = handlers.get(task_type, self._handle_general)
        return handler(prompt)

    # ── Classification ───────────────────────────────────────────
    def _handle_classify(self, prompt: str) -> str:
        p = prompt.lower()

        if any(w in p for w in ["password", "reset", "locked out", "can't log", "login"]):
            cat, pri, conf = "password_reset", "P3", 0.95
        elif any(w in p for w in ["vpn", "disconnect", "tunnel", "remote access"]):
            cat, pri, conf = "vpn_issue", "P2", 0.91
        elif any(w in p for w in ["install", "software", "access", "permission", "license"]):
            cat, pri, conf = "software_access", "P3", 0.88
        elif any(w in p for w in ["crash", "blue screen", "bsod", "hardware", "broken", "not turning on"]):
            cat, pri, conf = "hardware_failure", "P1", 0.93
        elif any(w in p for w in ["network", "internet", "wifi", "outage", "down", "slow"]):
            cat, pri, conf = "network_outage", "P2", 0.87
        elif any(w in p for w in ["virus", "malware", "hack", "breach", "suspicious", "phishing", "clicked a link", "ransomware"]):
            cat, pri, conf = "security_alert", "P1", 0.96
        elif any(w in p for w in ["email", "outlook", "mail", "inbox"]):
            cat, pri, conf = "email_issue", "P3", 0.85
        elif any(w in p for w in ["print", "printer", "scan"]):
            cat, pri, conf = "printer_problem", "P4", 0.90
        else:
            cat, pri, conf = "unknown", "P3", 0.50

        # sentiment
        frustrated_words = ["urgent", "asap", "critical", "broken", "again", "still", "frustrated"]
        sentiment = "frustrated" if any(w in p for w in frustrated_words) else "neutral"

        keywords = [w for w in p.split() if len(w) > 4][:5]

        return json.dumps({
            "category": cat,
            "priority": pri,
            "confidence": conf,
            "keywords": keywords,
            "sentiment": sentiment,
        })

    # ── Answer Synthesis ─────────────────────────────────────────
    def _handle_answer(self, prompt: str) -> str:
        p = prompt.lower()

        answers = {
            "password_reset": (
                "I can help you reset your password right away!\n\n"
                "**Automated steps being applied:**\n"
                "1. ✓ Identity verified via your employee ID\n"
                "2. ✓ Active Directory reset initiated\n"
                "3. ✓ Temporary password sent to your recovery email\n"
                "4. ✓ You'll be prompted to set a new password on next login\n\n"
                "Your new temporary password will arrive within 2 minutes. "
                "Please change it immediately after logging in per security policy."
            ),
            "vpn_issue": (
                "I've analysed your VPN connection logs. Here's what I found:\n\n"
                "**Detected issue:** MTU size mismatch (your current setting: 1500, required: 1400)\n\n"
                "**Auto-fix applied:**\n"
                "1. ✓ VPN client config updated remotely\n"
                "2. ✓ DNS resolver cache flushed\n"
                "3. ✓ Reconnection test passed\n\n"
                "Please reconnect your VPN now — it should stay stable. "
                "If disconnections persist after 30 min, reply and I'll escalate to the network team."
            ),
            "software_access": (
                "I've submitted your software access request.\n\n"
                "**Request details:**\n"
                "- Ticket created: NXS-0042 (Priority P3)\n"
                "- Approver notified: your direct manager\n"
                "- Estimated approval time: 2–4 hours (business hours)\n\n"
                "Once approved, your IT admin will provision the license within 1 hour. "
                "You'll receive a Slack notification when access is ready."
            ),
            "network_outage": (
                "I'm checking network status for your building/region...\n\n"
                "**Status:** Degraded connectivity detected on Floor 3 / Wing B switches.\n"
                "**Root cause:** Spanning tree reconfiguration in progress (ETA: 15 min)\n"
                "**Current workaround:** Switch to the CORP-WIFI-5G SSID temporarily.\n\n"
                "I've created incident ticket NXS-0099 and the network team has been paged."
            ),
            "email_issue": (
                "Let me diagnose your email issue.\n\n"
                "**Checks completed:**\n"
                "1. ✓ Exchange mailbox healthy\n"
                "2. ✓ Outlook profile re-initialised\n"
                "3. ✓ OST cache cleared (was 18GB — above 10GB limit)\n\n"
                "Please restart Outlook. The large cache was causing sync failures. "
                "Your emails should now load correctly."
            ),
            "printer_problem": (
                "Printer troubleshooting initiated.\n\n"
                "**Steps applied:**\n"
                "1. ✓ Print spooler service restarted on PRN-FLR2-01\n"
                "2. ✓ Stuck jobs cleared from queue (3 jobs removed)\n"
                "3. ✓ Driver version verified (up to date)\n\n"
                "Please try printing a test page now. If the issue persists, "
                "the printer may need a physical paper-jam inspection."
            ),
            "hardware_failure": (
                "This sounds like a hardware issue requiring physical intervention.\n\n"
                "**I've done the following:**\n"
                "1. ✓ Escalation ticket created: NXS-0007 (P1 - Critical)\n"
                "2. ✓ On-site technician dispatched (ETA: 30 min)\n"
                "3. ✓ Loaner laptop provisioned — pick up at IT desk, Room 101\n\n"
                "Please save any open work if possible. The technician will contact you directly."
            ),
            "security_alert": (
                "⚠️ **SECURITY ALERT — Immediate action required.**\n\n"
                "**Actions taken automatically:**\n"
                "1. ✓ Account temporarily suspended pending review\n"
                "2. ✓ SIEM alert raised — Security team notified (P1)\n"
                "3. ✓ Active sessions terminated\n"
                "4. ✓ PagerDuty incident #4821 created\n\n"
                "The security team will contact you within 15 minutes. "
                "Do NOT attempt to log in until cleared."
            ),
        }

        for key, answer in answers.items():
            if key in p:
                return answer

        return (
            "I wasn't able to find a specific resolution in our knowledge base for your issue.\n\n"
            "I've created a support ticket and a specialist will review it shortly. "
            "Could you provide more details about what you're experiencing?"
        )

    # ── Summarize ────────────────────────────────────────────────
    def _handle_summarize(self, prompt: str) -> str:
        return (
            "**Summary for L2 handoff:**\n"
            "User reported a recurring technical issue that could not be auto-resolved. "
            "Knowledge base search returned low-confidence results. "
            "Full conversation history, diagnostic logs, and classification data attached. "
            "Recommended action: manual review by specialist team."
        )

    # ── Escalation ───────────────────────────────────────────────
    def _handle_escalation(self, prompt: str) -> str:
        return json.dumps({
            "suggested_team": "L2 Infrastructure",
            "reason": "Automated resolution failed after 2 retries; confidence below threshold",
            "urgency": "high",
        })

    # ── General ──────────────────────────────────────────────────
    def _handle_general(self, prompt: str) -> str:
        return "I'm NEXUS, your AI IT support assistant. How can I help you today?"


# Singleton
llm = MockLLM()
