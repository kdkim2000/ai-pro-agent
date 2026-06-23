# src/connectors/dictionary_client.py
"""Term / Word Dictionary connector (T1-2_GUIDE.md Section 4.7)"""
from __future__ import annotations
from typing import List, Optional
import httpx, os, re
from .base import BaseDictionaryConnector, ConnectorResult, TermRecord


class DictionaryConnector(BaseDictionaryConnector):
    """Term / Word Dictionary management system connector"""

    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None, timeout: int = 30):
        self.base_url = (base_url or os.getenv("DICTIONARY_URL", "")).rstrip("/")
        self.token = token or os.getenv("DICTIONARY_TOKEN", "")
        self.timeout = timeout
        self._headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    def _get(self, path: str, params: dict = None) -> dict:
        url = f"{self.base_url}/api/v1{path}"
        with httpx.Client(timeout=self.timeout, verify=False) as client:
            resp = client.get(url, headers=self._headers, params=params or {})
            resp.raise_for_status()
            return resp.json()

    def health_check(self) -> ConnectorResult:
        try:
            self._get("/health")
            return ConnectorResult(success=True, data="connected", source=self.base_url)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    def check_term_registered(self, term: str) -> ConnectorResult:
        try:
            data = self._get("/terms/search", params={"q": term, "exact": True})
            results = data.get("results", [])
            if results:
                t = results[0]
                record = TermRecord(
                    term_id=t.get("term_id", ""), term_ko=t.get("term_ko", ""), term_en=t.get("term_en", ""),
                    abbreviation=t.get("abbreviation", ""), definition=t.get("definition", ""),
                    domain=t.get("domain", ""), status=t.get("status", "approved"),
                )
                return ConnectorResult(success=True, data={"registered": True, "record": record})
            return ConnectorResult(success=True, data={"registered": False, "record": None})
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    def detect_unregistered_terms(self, text: str) -> ConnectorResult:
        try:
            korean_words = list(set(re.findall(r'[가-힣]{2,}', text)))
            unregistered = []
            for word in korean_words:
                result = self.check_term_registered(word)
                if result.success and not result.data.get("registered"):
                    unregistered.append(word)
            return ConnectorResult(success=True, data={"unregistered_terms": unregistered, "total_checked": len(korean_words)})
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    def build_term_draft(self, term_ko: str, context: str) -> ConnectorResult:
        draft = {
            "term_ko": term_ko, "term_en": "", "abbreviation": "",
            "definition": f"Definition for '{term_ko}' required.",
            "domain": "", "context_sample": context[:200],
            "_meta": {"note": "Agent generated draft. Review before submission."},
        }
        return ConnectorResult(success=True, data=draft)
