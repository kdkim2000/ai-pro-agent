# src/connectors/doodream_client.py
"""Doodream (Samsung HI request management) REST API connector (T1-2_GUIDE.md Section 4.4)"""
from __future__ import annotations
from typing import Optional
import httpx, os
from .base import BaseDoodreamConnector, ConnectorResult, CRRecord


class DoodreamConnector(BaseDoodreamConnector):
    """Doodream REST API connector"""

    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None, timeout: int = 30):
        self.base_url = (base_url or os.getenv("DOODREAM_URL", "")).rstrip("/")
        self.token = token or os.getenv("DOODREAM_TOKEN", "")
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

    def _parse_cr(self, item: dict) -> CRRecord:
        return CRRecord(
            cr_id=item.get("cr_id", ""), title=item.get("title", ""), description=item.get("description", ""),
            cr_type=item.get("cr_type", "new_dev"), status=item.get("status", ""),
            requester=item.get("requester", ""), assignee=item.get("assignee", ""),
            created_at=item.get("created_at", ""), closed_at=item.get("closed_at"),
            actual_hours=item.get("actual_hours"), estimated_hours=item.get("estimated_hours"),
            affected_systems=item.get("affected_systems", []), tags=item.get("tags", []),
        )

    def get_cr(self, cr_id: str) -> ConnectorResult:
        try:
            data = self._get(f"/cr/{cr_id}")
            return ConnectorResult(success=True, data=self._parse_cr(data))
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    def search_cr_history(self, query: str, cr_type: Optional[str] = None, top_k: int = 10) -> ConnectorResult:
        try:
            params = {"q": query, "limit": top_k}
            if cr_type:
                params["cr_type"] = cr_type
            data = self._get("/cr/search", params=params)
            return ConnectorResult(success=True, data=[self._parse_cr(item) for item in data.get("results", [])])
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    def get_recent_crs(self, days: int = 90, status: Optional[str] = None) -> ConnectorResult:
        try:
            params = {"days": days}
            if status:
                params["status"] = status
            data = self._get("/cr/recent", params=params)
            return ConnectorResult(success=True, data=[self._parse_cr(item) for item in data.get("results", [])])
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))
