# src/connectors/mock/confluence_mock.py
"""Confluence Mock (T1-2_GUIDE.md Section 5)"""
from __future__ import annotations
from typing import Optional
from ..base import BaseConfluenceConnector, ConnectorResult, ConfluencePage


class ConfluenceMockConnector(BaseConfluenceConnector):
    """Confluence Mock -- realistic page samples"""
    is_mock = True

    _PAGE_SAMPLES = [
        ConfluencePage(
            page_id="10001", title="Requirements Analysis Template",
            content="<h1>Requirements Analysis</h1><p>CR ID: __CR_ID__</p><h2>1. Overview</h2><p>__OVERVIEW__</p><h2>2. Details</h2><p>__DETAILS__</p>",
            space_key="DEV", url="https://confluence.internal/pages/10001",
            last_modified="2026-05-01T10:00:00", labels=["template", "requirements"],
        ),
        ConfluencePage(
            page_id="10002", title="Impact Analysis Template",
            content="<h1>Impact Analysis</h1><h2>Affected Tables</h2><p>__TABLES__</p><h2>Affected Programs</h2><p>__PROGRAMS__</p>",
            space_key="DEV", url="https://confluence.internal/pages/10002",
            last_modified="2026-05-01T10:00:00", labels=["template", "impact"],
        ),
        ConfluencePage(
            page_id="10003", title="Ship Order Development Guide",
            content="<h1>Ship Order Module</h1><p>Guide for ship order management module development.</p>",
            space_key="DEV", url="https://confluence.internal/pages/10003",
            last_modified="2026-04-15T14:00:00", labels=["guide", "ship_order"],
        ),
    ]

    def health_check(self) -> ConnectorResult:
        return ConnectorResult(success=True, data="mock-connected")

    def search_pages(self, query: str, space_key: Optional[str] = None, top_k: int = 5) -> ConnectorResult:
        results = self._PAGE_SAMPLES
        if space_key:
            results = [p for p in results if p.space_key == space_key]
        return ConnectorResult(success=True, data=results[:top_k])

    def get_page(self, page_id: str) -> ConnectorResult:
        for p in self._PAGE_SAMPLES:
            if p.page_id == page_id:
                return ConnectorResult(success=True, data=p, source=p.url)
        return ConnectorResult(success=False, error=f"Mock: Page '{page_id}' not found")

    def get_template(self, template_name: str) -> ConnectorResult:
        for p in self._PAGE_SAMPLES:
            if template_name.lower() in p.title.lower():
                return ConnectorResult(success=True, data=p.content)
        return ConnectorResult(success=False, error=f"Mock: Template '{template_name}' not found")

    def create_page(self, space_key: str, title: str, content: str, parent_id: Optional[str] = None) -> ConnectorResult:
        return ConnectorResult(success=True, data={"page_id": "99999", "url": "https://confluence.internal/pages/99999"})
