"""
NEXUS RAG Engine
================
Retrieval-Augmented Generation pipeline.

Pipeline:
  1. Knowledge base seeded with IT articles (KBDocument)
  2. Documents embedded via a TF-IDF-style bag-of-words vector (simulates ada-002)
  3. Cosine similarity used to retrieve top-k relevant docs
  4. Retrieved context injected into LLM prompt for answer synthesis

In production swap _embed() with:
    from openai import OpenAI
    client = OpenAI()
    resp = client.embeddings.create(model="text-embedding-ada-002", input=text)
    return np.array(resp.data[0].embedding)

And replace the in-memory index with Pinecone:
    import pinecone
    index = pinecone.Index("nexus-kb")
    results = index.query(vector=embedding, top_k=5, include_metadata=True)
"""

import numpy as np
import re
from typing import List, Tuple
from models import KBDocument, RetrievalResult


# ── Knowledge Base Seed Data ─────────────────────────────────────
KB_ARTICLES: List[KBDocument] = [
    KBDocument(
        doc_id="KB-001",
        title="Password Reset — Self-Service and Admin Guide",
        content=(
            "Users can reset passwords via the self-service portal at https://sso.corp/reset. "
            "Admins can use Active Directory Users and Computers (ADUC) or run: "
            "Set-ADAccountPassword -Identity <username> -Reset -NewPassword (Read-Host -Prompt 'New Password' -AsSecureString). "
            "After reset, the account is unlocked automatically. "
            "Password must meet complexity: 12+ chars, upper, lower, digit, symbol. "
            "Temporary passwords expire in 24 hours. Notify user via recovery email."
        ),
        category="password_reset",
        tags=["password", "reset", "active directory", "sso", "locked"],
        resolution_steps=[
            "Verify user identity via employee ID + manager confirmation",
            "Navigate to AD Users and Computers → find user account",
            "Right-click → Reset Password → generate temp password",
            "Ensure 'User must change password at next logon' is checked",
            "Email temp password to user's recovery address",
            "Confirm user can log in; close ticket",
        ],
        avg_resolution_time_min=2.5,
    ),
    KBDocument(
        doc_id="KB-002",
        title="VPN Connectivity Issues — Diagnosis and Fix",
        content=(
            "Common VPN issues: MTU mismatch, DNS resolver failure, split-tunnel misconfiguration. "
            "Check VPN client version — must be 2.4.x or above. "
            "MTU fix: netsh interface ipv4 set subinterface 'Ethernet' mtu=1400 store=persistent. "
            "DNS flush: ipconfig /flushdns. "
            "For persistent drops, check firewall rules for UDP 500 and UDP 4500 (IKEv2). "
            "Server-side: review /var/log/vpn/access.log for auth failures."
        ),
        category="vpn_issue",
        tags=["vpn", "disconnect", "mtu", "dns", "remote access", "tunnel"],
        resolution_steps=[
            "Collect VPN client version and OS from user",
            "Pull /var/log/vpn/access.log for user's IP",
            "Check for MTU mismatch errors in log",
            "Apply MTU fix remotely via RMM tool",
            "Flush DNS cache on client machine",
            "Test reconnection and monitor for 10 min",
        ],
        avg_resolution_time_min=8.0,
    ),
    KBDocument(
        doc_id="KB-003",
        title="Software Access & License Provisioning",
        content=(
            "New software requests must be approved by department manager before IT provisions. "
            "Submit requests via ServiceNow catalogue item 'Software Request'. "
            "For Adobe CC, Slack, Zoom Pro: auto-provisioned within 1h after manager approval. "
            "For Salesforce, SAP, custom tools: manual provisioning by IT admin (up to 4h). "
            "License counts are tracked in the Asset Management module. "
            "Expired licenses auto-revoke after 30-day grace period."
        ),
        category="software_access",
        tags=["software", "license", "access", "install", "provision", "permission"],
        resolution_steps=[
            "Confirm software name and version required",
            "Check license inventory in Asset Management",
            "Create ServiceNow catalogue request",
            "Notify manager for approval (email + Slack)",
            "Provision license upon approval",
            "Confirm user access and close ticket",
        ],
        avg_resolution_time_min=15.0,
    ),
    KBDocument(
        doc_id="KB-004",
        title="Network Outage Response Playbook",
        content=(
            "Network outages are classified by scope: building, floor, or VLAN-level. "
            "Check Datadog dashboard: https://datadog.corp/network. "
            "Common causes: spanning tree reconvergence (STP), switch firmware update, DHCP exhaustion. "
            "DHCP scope check: show ip dhcp pool on Cisco switches. "
            "Workaround for users: connect to CORP-WIFI-5G (separate SSID, different path). "
            "Escalate to NOC if affecting 10+ users or core routing. "
            "Document all actions in the incident bridge channel #noc-incidents."
        ),
        category="network_outage",
        tags=["network", "outage", "wifi", "internet", "slow", "stp", "dhcp"],
        resolution_steps=[
            "Identify scope: 1 user or multiple?",
            "Check Datadog for switch/port errors",
            "Identify affected VLAN or switch port",
            "Apply fix: restart port, clear STP, expand DHCP scope",
            "Provide workaround SSID to affected users",
            "Post update in #noc-incidents Slack channel",
        ],
        avg_resolution_time_min=20.0,
    ),
    KBDocument(
        doc_id="KB-005",
        title="Outlook / Exchange Email Issues",
        content=(
            "Common email issues: OST cache bloat (>10GB causes sync failures), "
            "profile corruption, Autodiscover misconfiguration. "
            "OST fix: File → Account Settings → Data Files → delete old .ost → restart Outlook. "
            "Profile rebuild: Control Panel → Mail → Show Profiles → Add new profile. "
            "Check mailbox size: Get-MailboxStatistics -Identity user@corp.com | Select TotalItemSize. "
            "If mailbox over quota (50GB), archive to PST or extend quota via EAC."
        ),
        category="email_issue",
        tags=["email", "outlook", "exchange", "ost", "mailbox", "inbox", "sync"],
        resolution_steps=[
            "Confirm Outlook version and last successful sync time",
            "Check OST file size (C:\\Users\\<user>\\AppData\\Local\\Microsoft\\Outlook)",
            "If OST > 10GB, delete and allow Outlook to rebuild",
            "If recurring, rebuild Outlook profile from scratch",
            "Verify Autodiscover via Test E-mail AutoConfiguration",
            "Monitor for 30 min after fix",
        ],
        avg_resolution_time_min=12.0,
    ),
    KBDocument(
        doc_id="KB-006",
        title="Printer Issues — Spooler, Queue, Driver",
        content=(
            "Printer issues commonly caused by: stuck print spooler, corrupt print queue, outdated driver. "
            "Restart spooler: net stop spooler && del /Q /F /S %systemroot%\\system32\\spool\\PRINTERS\\* && net start spooler. "
            "Re-add printer: Settings → Printers → Remove → Add printer → use IP address. "
            "Driver update: check vendor site or use Windows Update. "
            "For network printers, verify the printer IP hasn't changed via DHCP lease."
        ),
        category="printer_problem",
        tags=["printer", "print", "spooler", "queue", "driver", "scan"],
        resolution_steps=[
            "Identify printer name and user OS",
            "Restart print spooler service remotely via RMM",
            "Clear all stuck jobs from the print queue",
            "Verify printer IP address matches the driver configuration",
            "Update driver if version is outdated",
            "Print test page to confirm resolution",
        ],
        avg_resolution_time_min=7.0,
    ),
    KBDocument(
        doc_id="KB-007",
        title="Hardware Failure — Laptops and Desktops",
        content=(
            "Hardware failures include: BSOD, failure to boot, screen damage, keyboard/trackpad failure. "
            "For BSOD: collect minidump from C:\\Windows\\Minidump, analyse with WinDbg. "
            "For failure to boot: check SMART data via HDAT2 bootable USB. "
            "Loaner devices available at IT desk, Room 101 — requires employee ID. "
            "Data recovery: if disk is failing, image immediately with dd or Clonezilla. "
            "RMA process: log asset tag in CMDB, file vendor warranty claim if < 3 years old."
        ),
        category="hardware_failure",
        tags=["hardware", "laptop", "bsod", "crash", "screen", "keyboard", "broken", "boot"],
        resolution_steps=[
            "Determine if data is accessible (boot test)",
            "Collect minidump or SMART data",
            "Issue loaner device from IT desk",
            "Begin data recovery/imaging if needed",
            "File RMA with vendor if under warranty",
            "Update CMDB with new asset assignment",
        ],
        avg_resolution_time_min=45.0,
    ),
    KBDocument(
        doc_id="KB-008",
        title="Security Incidents — Malware, Phishing, Breach",
        content=(
            "Security incidents require immediate escalation to the Security team. "
            "Do NOT attempt self-remediation for suspected breaches. "
            "Containment steps: isolate device from network (unplug ethernet, disable wifi). "
            "Preserve evidence: do not restart or wipe the device. "
            "Notify: security@corp.com and #security-incidents Slack channel immediately. "
            "SIEM alerting: Splunk monitors for IOCs and will auto-page the on-call SOC analyst."
        ),
        category="security_alert",
        tags=["security", "malware", "phishing", "breach", "virus", "hack", "suspicious"],
        resolution_steps=[
            "Isolate affected device immediately",
            "Notify Security team via email + Slack",
            "Preserve all logs and do NOT restart device",
            "SIEM auto-creates P1 incident in ServiceNow",
            "SOC analyst leads investigation",
            "Post-incident review within 48h",
        ],
        avg_resolution_time_min=60.0,
    ),
]


class RAGEngine:
    """
    Lightweight RAG engine with TF-IDF-style embeddings and cosine similarity.
    Simulates a Pinecone vector store with an in-memory numpy index.
    """

    def __init__(self, documents: List[KBDocument] = KB_ARTICLES):
        self.documents = documents
        self._vocab: List[str] = []
        self._index: np.ndarray = np.array([])
        self._build_index()

    # ── Index Construction ───────────────────────────────────────
    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r'\b[a-z]{3,}\b', text.lower())

    def _build_vocab(self) -> List[str]:
        vocab = set()
        for doc in self.documents:
            combined = doc.title + " " + doc.content + " " + " ".join(doc.tags)
            vocab.update(self._tokenize(combined))
        return sorted(vocab)

    def _embed(self, text: str) -> np.ndarray:
        """Bag-of-words TF vector over shared vocabulary."""
        tokens = self._tokenize(text)
        vec = np.zeros(len(self._vocab), dtype=np.float32)
        for tok in tokens:
            if tok in self._vocab:
                vec[self._vocab.index(tok)] += 1.0
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec

    def _build_index(self):
        self._vocab = self._build_vocab()
        self._index = np.stack([
            self._embed(d.title + " " + d.content + " " + " ".join(d.tags))
            for d in self.documents
        ])
        print(f"[RAGEngine] Index built: {len(self.documents)} docs, vocab size {len(self._vocab)}")

    # ── Retrieval ────────────────────────────────────────────────
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        if na == 0 or nb == 0:
            return 0.0
        return float(np.dot(a, b) / (na * nb))

    def retrieve(self, query: str, top_k: int = 3) -> List[Tuple[KBDocument, float]]:
        """Return top_k (document, similarity_score) pairs."""
        q_vec = self._embed(query)
        scores = [self._cosine_similarity(q_vec, doc_vec) for doc_vec in self._index]
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:top_k]
        return [(self.documents[i], score) for i, score in ranked]

    def query(self, query: str, top_k: int = 3, min_sim: float = 0.30) -> RetrievalResult:
        """Full RAG query: retrieve + filter + synthesise answer."""
        results = self.retrieve(query, top_k=top_k)
        filtered = [(doc, score) for doc, score in results if score >= min_sim]

        if not filtered:
            return RetrievalResult(
                documents=[],
                top_similarity=0.0,
                answer="No relevant knowledge base articles found.",
                sources=[],
                confidence=0.0,
                fallback_to_human=True,
            )

        top_doc, top_score = filtered[0]

        # Build answer from top document resolution steps
        steps_text = "\n".join(f"{i+1}. {s}" for i, s in enumerate(top_doc.resolution_steps))
        answer = (
            f"**{top_doc.title}**\n\n"
            f"{top_doc.content[:300]}...\n\n"
            f"**Resolution Steps:**\n{steps_text}"
        )

        return RetrievalResult(
            documents=[doc for doc, _ in filtered],
            top_similarity=top_score,
            answer=answer,
            sources=[f"{doc.doc_id}: {doc.title}" for doc, _ in filtered],
            confidence=min(top_score * 1.1, 1.0),
            fallback_to_human=(top_score < 0.40),
        )


# Singleton
rag_engine = RAGEngine()
