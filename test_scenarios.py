"""
NEXUS Test Suite
================
Scenario-based integration tests covering all rubric checkpoints.
Run: python tests/test_scenarios.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import json
import time
from models import UserMessage
from orchestrator import Orchestrator

# ── Test Scenarios ───────────────────────────────────────────────
SCENARIOS = [
    {
        "id": "TC-01",
        "name": "Password Reset — Auto-Remediated",
        "message": "I'm locked out of my account and can't log in to my computer. Need urgent help with password reset.",
        "expected_category": "password_reset",
        "expected_priority": "P3",
        "expect_escalation": False,
        "expect_automation": True,
    },
    {
        "id": "TC-02",
        "name": "VPN Connectivity Issue",
        "message": "My VPN keeps disconnecting every 10 minutes. I'm working from home and can't stay connected to the corporate network.",
        "expected_category": "vpn_issue",
        "expected_priority": "P2",
        "expect_escalation": False,
        "expect_automation": False,
    },
    {
        "id": "TC-03",
        "name": "Software License Request",
        "message": "I need access to Adobe Creative Cloud for a design project. Can you install it and get me a license?",
        "expected_category": "software_access",
        "expected_priority": "P3",
        "expect_escalation": False,
        "expect_automation": False,
    },
    {
        "id": "TC-04",
        "name": "Hardware Failure — P1 Escalation",
        "message": "My laptop crashed and won't turn on. Blue screen then nothing. I have a client presentation in 2 hours!",
        "expected_category": "hardware_failure",
        "expected_priority": "P1",
        "expect_escalation": True,
        "expect_automation": False,
    },
    {
        "id": "TC-05",
        "name": "Network Outage",
        "message": "The internet is completely down on our floor. About 20 people are affected and can't work.",
        "expected_category": "network_outage",
        "expected_priority": "P2",
        "expect_escalation": False,
        "expect_automation": False,
    },
    {
        "id": "TC-06",
        "name": "Email / Outlook Sync Issue — Auto-Remediated",
        "message": "Outlook isn't syncing my emails. I haven't received anything since this morning and it just spins.",
        "expected_category": "email_issue",
        "expected_priority": "P3",
        "expect_escalation": False,
        "expect_automation": True,
    },
    {
        "id": "TC-07",
        "name": "Printer Problem — Auto-Remediated",
        "message": "The printer on Floor 2 won't print. It's in the queue but nothing comes out.",
        "expected_category": "printer_problem",
        "expected_priority": "P4",
        "expect_escalation": False,
        "expect_automation": True,
    },
    {
        "id": "TC-08",
        "name": "Security Alert — Always Escalates",
        "message": "I received a suspicious email and clicked a link by mistake. I think my computer might have a virus or malware.",
        "expected_category": "security_alert",
        "expected_priority": "P1",
        "expect_escalation": True,
        "expect_automation": False,
    },
]


class TestRunner:
    def __init__(self):
        self.orchestrator = Orchestrator()
        self.results = []

    def run_all(self):
        print("\n" + "="*70)
        print("  NEXUS TEST SUITE — Integration Scenarios")
        print("="*70)

        for scenario in SCENARIOS:
            result = self._run_scenario(scenario)
            self.results.append(result)

        self._print_summary()
        return self.results

    def _run_scenario(self, scenario: dict) -> dict:
        print(f"\n{'─'*60}")
        print(f"  Running {scenario['id']}: {scenario['name']}")
        print(f"{'─'*60}")

        msg = UserMessage(
            content=scenario["message"],
            user_id=f"test_user_{scenario['id']}",
            channel="test",
        )

        t0 = time.time()
        response = self.orchestrator.handle(msg)
        elapsed = round(time.time() - t0, 3)

        # Assertions
        checks = {}
        checks["category_match"] = (
            response.ticket.category == scenario["expected_category"]
        )
        checks["priority_match"] = (
            response.ticket.priority == scenario["expected_priority"]
        )
        checks["escalation_match"] = (
            response.escalated == scenario["expect_escalation"]
        )
        checks["automation_match"] = (
            response.ticket.automation_applied == scenario["expect_automation"]
        )
        checks["has_ticket"] = response.ticket is not None
        checks["has_answer"] = len(response.answer) > 20
        checks["resolved_in_time"] = elapsed < 5.0  # should be fast

        passed = all(checks.values())
        status = "✅ PASS" if passed else "❌ FAIL"

        print(f"\n  Result: {status} ({elapsed}s)")
        print(f"  Category:   got={response.ticket.category:<20} expected={scenario['expected_category']}")
        print(f"  Priority:   got={response.ticket.priority}   expected={scenario['expected_priority']}")
        print(f"  Escalated:  got={response.escalated}  expected={scenario['expect_escalation']}")
        print(f"  Automated:  got={response.ticket.automation_applied}  expected={scenario['expect_automation']}")
        print(f"  Confidence: {response.confidence:.3f}")
        print(f"  Ticket:     {response.ticket.ticket_id}")
        print(f"  Checks:     {checks}")

        if not checks["category_match"] or not checks["priority_match"]:
            print(f"  ⚠ Answer preview: {response.answer[:120]}...")

        return {
            "scenario_id": scenario["id"],
            "name": scenario["name"],
            "passed": passed,
            "checks": checks,
            "elapsed_sec": elapsed,
            "ticket_id": response.ticket.ticket_id,
            "category": response.ticket.category,
            "priority": response.ticket.priority,
            "confidence": response.confidence,
            "escalated": response.escalated,
            "automated": response.ticket.automation_applied,
        }

    def _print_summary(self):
        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"])
        failed = total - passed
        avg_time = round(sum(r["elapsed_sec"] for r in self.results) / total, 3)

        print("\n" + "="*70)
        print("  TEST SUMMARY")
        print("="*70)
        print(f"  Total:   {total}")
        print(f"  Passed:  {passed}  ({'%.0f' % (passed/total*100)}%)")
        print(f"  Failed:  {failed}")
        print(f"  Avg Time: {avg_time}s per scenario")
        print()

        # Per-check breakdown
        check_names = list(self.results[0]["checks"].keys())
        for check in check_names:
            c_passed = sum(1 for r in self.results if r["checks"].get(check))
            print(f"  {check:<25} {c_passed}/{total}")

        print()
        # Agent stats
        stats = self.orchestrator.full_stats()
        print("  AGENT STATS:")
        print(json.dumps(stats, indent=4))

        return passed, failed


if __name__ == "__main__":
    runner = TestRunner()
    results = runner.run_all()
    passed = sum(1 for r in results if r["passed"])
    sys.exit(0 if passed == len(results) else 1)
