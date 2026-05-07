"""
NEXUS Intake Agent
==================
Responsible for:
  - Receiving raw user messages
  - Classifying issue category via LLM
  - Assigning priority (P1–P4)
  - Detecting sentiment and escalation triggers
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import json
import time
from models import UserMessage, ClassificationResult
from llm import llm
from config import PRIORITY_LEVELS, AGENT_CONFIG


class IntakeAgent:
    """
    Agent 1: Intake & Classification.
    Wraps the LLM classification call with retry logic and confidence gating.
    """

    name = "IntakeAgent"

    def __init__(self):
        self.processed = 0
        self.escalations = 0

    def process(self, message: UserMessage) -> ClassificationResult:
        """Classify an incoming user message."""
        t0 = time.time()
        print(f"\n[{self.name}] Processing message from user={message.user_id} channel={message.channel}")
        print(f"[{self.name}] Message: \"{message.content[:80]}...\"" if len(message.content) > 80 else f"[{self.name}] Message: \"{message.content}\"")

        result = self._classify_with_retry(message.content)
        result.raw_text = message.content

        # Escalation override: P1/security always escalates
        if result.priority == "P1" or result.category == "security_alert":
            result.needs_escalation = True
            self.escalations += 1

        # Low-confidence fallback
        if result.confidence < AGENT_CONFIG["escalation_threshold"]:
            result.needs_escalation = True
            result.priority = "P2"  # bump priority when unsure

        self.processed += 1
        elapsed = round(time.time() - t0, 3)
        print(f"[{self.name}] → category={result.category} priority={result.priority} confidence={result.confidence:.2f} sentiment={result.sentiment} ({elapsed}s)")
        return result

    def _classify_with_retry(self, text: str, retries: int = 0) -> ClassificationResult:
        prompt = (
            f"You are an IT support classifier. Analyse this user message and return JSON.\n"
            f"Message: {text}\n"
            f"Return: {{category, priority (P1-P4), confidence (0-1), keywords (list), sentiment}}"
        )
        try:
            raw = llm.complete(prompt, task_type="classify")
            data = json.loads(raw)
            return ClassificationResult(
                category=data.get("category", "unknown"),
                priority=data.get("priority", "P3"),
                confidence=float(data.get("confidence", 0.5)),
                keywords=data.get("keywords", []),
                sentiment=data.get("sentiment", "neutral"),
            )
        except (json.JSONDecodeError, KeyError) as e:
            if retries < AGENT_CONFIG["max_retries"]:
                print(f"[{self.name}] Retry {retries+1} after parse error: {e}")
                return self._classify_with_retry(text, retries + 1)
            # Hard fallback
            return ClassificationResult(
                category="unknown", priority="P3",
                confidence=0.30, keywords=[], sentiment="neutral",
            )

    def stats(self) -> dict:
        return {
            "agent": self.name,
            "processed": self.processed,
            "escalations_triggered": self.escalations,
            "escalation_rate": round(self.escalations / max(self.processed, 1), 3),
        }
