# src/connectors/mock/dictionary_mock.py
"""Term / Word Dictionary Mock (T1-2_GUIDE.md Section 5)"""
from __future__ import annotations
import re
from ..base import BaseDictionaryConnector, ConnectorResult, TermRecord


class DictionaryMockConnector(BaseDictionaryConnector):
    """Term / Word Dictionary Mock"""
    is_mock = True

    _TERMS = {
        "납기일": TermRecord(term_id="T001", term_ko="납기일", term_en="Delivery Date", abbreviation="DLV_DT", definition="Scheduled delivery date", domain="Sales", status="approved"),
        "발주처": TermRecord(term_id="T002", term_ko="발주처", term_en="Client", abbreviation="CLIENT", definition="Ordering organization", domain="Sales", status="approved"),
        "선박": TermRecord(term_id="T003", term_ko="선박", term_en="Ship", abbreviation="SHIP", definition="Ship/Vessel", domain="General", status="approved"),
        "수주": TermRecord(term_id="T004", term_ko="수주", term_en="Order", abbreviation="ORD", definition="Order receipt", domain="Sales", status="approved"),
    }

    def health_check(self) -> ConnectorResult:
        return ConnectorResult(success=True, data="mock-connected")

    def check_term_registered(self, term: str) -> ConnectorResult:
        rec = self._TERMS.get(term)
        if rec:
            return ConnectorResult(success=True, data={"registered": True, "record": rec})
        return ConnectorResult(success=True, data={"registered": False, "record": None})

    def detect_unregistered_terms(self, text: str) -> ConnectorResult:
        korean_words = list(set(re.findall(r'[가-힣]{2,}', text)))
        unregistered = [w for w in korean_words if w not in self._TERMS]
        return ConnectorResult(success=True, data={"unregistered_terms": unregistered, "total_checked": len(korean_words)})

    def build_term_draft(self, term_ko: str, context: str) -> ConnectorResult:
        draft = {"term_ko": term_ko, "term_en": "", "abbreviation": "", "definition": "", "domain": "", "context_sample": context[:200], "_meta": {"note": "Mock draft"}}
        return ConnectorResult(success=True, data=draft)
