"""
NEXUS Knowledge Agent
=====================
Responsible for:
  - Querying the RAG engine with the user's issue
  - Synthesising a natural-language answer from retrieved docs
  - Returning confidence scores and source citations
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import time
from models import ClassificationResult, RetrievalResult
from rag.engine import rag_engine
from llm import llm
from config import AGENT_CONFIG, RAG_CONFIG


class KnowledgeAgent:
    """
    Agent 2: Knowledge Retrieval & Answer Synthesis.
    Uses RAG to find relevant KB articles, then synthesises a response.
    """

    name = "KnowledgeAgent"

    def __init__(self):
        self.queries = 0
        self.cache_hits = 0
        self._cache: dict = {}

    def answer(self, user_text: str, classification: ClassificationResult) -> RetrievalResult:
        """Retrieve knowledge and synthesise answer for a classified issue."""
        t0 = time.time()
        print(f"\n[{self.name}] Querying RAG for category={classification.category}")

        # Check simple cache
        cache_key = classification.category + "|" + user_text[:40]
        if cache_key in self._cache:
            self.cache_hits += 1
            print(f"[{self.name}] Cache hit!")
            return self._cache[cache_key]

        # Build enriched query: combine user text + category + known KB tags
        CATEGORY_BOOST = {
            "vpn_issue":        "vpn disconnect tunnel remote access mtu dns",
            "software_access":  "software license install access provision permission",
            "network_outage":   "network internet wifi outage slow stp dhcp",
            "password_reset":   "password reset active directory sso locked",
            "email_issue":      "email outlook exchange ost mailbox inbox sync",
            "printer_problem":  "printer print spooler queue driver scan",
            "hardware_failure": "hardware laptop bsod crash screen keyboard broken boot",
            "security_alert":   "security malware phishing breach virus hack suspicious",
        }
        boost = CATEGORY_BOOST.get(classification.category, "")
        enriched_query = f"{user_text} {classification.category} {' '.join(classification.keywords)} {boost}"

        # RAG retrieval
        retrieval = rag_engine.query(
            enriched_query,
            top_k=RAG_CONFIG["top_k"],
            min_sim=RAG_CONFIG["min_similarity"],
        )

        # If RAG found something, enrich with LLM synthesis
        if retrieval.documents and not retrieval.fallback_to_human:
            synth_prompt = (
                f"Context from KB: {retrieval.documents[0].content[:400]}\n"
                f"User issue category: {classification.category}\n"
                f"Synthesise a helpful IT support response."
            )
            llm_answer = llm.complete(synth_prompt, task_type="answer")
            retrieval.answer = llm_answer

        # Gate on confidence threshold
        if retrieval.confidence < AGENT_CONFIG["confidence_threshold"]:
            retrieval.fallback_to_human = True

        elapsed = round(time.time() - t0, 3)
        print(f"[{self.name}] → docs_found={len(retrieval.documents)} top_sim={retrieval.top_similarity:.3f} confidence={retrieval.confidence:.3f} fallback={retrieval.fallback_to_human} ({elapsed}s)")

        self.queries += 1
        self._cache[cache_key] = retrieval
        return retrieval

    def stats(self) -> dict:
        return {
            "agent": self.name,
            "total_queries": self.queries,
            "cache_hits": self.cache_hits,
            "cache_hit_rate": round(self.cache_hits / max(self.queries, 1), 3),
        }
