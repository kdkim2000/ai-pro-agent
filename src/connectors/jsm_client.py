# src/connectors/jsm_client.py
"""JSM (Jira Service Management) REST API connector (T1-2_GUIDE.md Section 4.3)"""
from __future__ import annotations
from typing import Optional
import httpx, os
from .base import BaseJSMConnector, ConnectorResult, CRRecord


class JSMConnector(BaseJSMConnector):
    """JSM (Jira Service Management) REST API connector"""

    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None, project_key: Optional[str] = None, timeout: int = 30):
        self.base_url = (base_url or os.getenv("JSM_URL", "")).rstrip("/")
        self.token = token or os.getenv("JSM_TOKEN", "")
        self.project_key = project_key or os.getenv("JSM_PROJECT_KEY", "")
        self.timeout = timeout
        self._headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    def _get(self, path: str, params: dict = None) -> dict:
        url = f"{self.base_url}/rest/api/3{path}"
        with httpx.Client(timeout=self.timeout, verify=False) as client:
            resp = client.get(url, headers=self._headers, params=params or {})
            resp.raise_for_status()
            return resp.json()

    def health_check(self) -> ConnectorResult:
        try:
            data = self._get(f"/project/{self.project_key}")
            return ConnectorResult(success=True, data=data.get("name"), source=self.base_url)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    def get_issue(self, issue_key: str) -> ConnectorResult:
        try:
            data = self._get(f"/issue/{issue_key}")
            return ConnectorResult(success=True, data=data, source=f"{self.base_url}/browse/{issue_key}")
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    def search_issues(self, jql: str, top_k: int = 10) -> ConnectorResult:
        try:
            data = self._get("/search", params={"jql": jql, "maxResults": top_k})
            return ConnectorResult(success=True, data=data.get("issues", []))
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    def build_issue_draft(self, cr_record: CRRecord) -> ConnectorResult:
        try:
            draft = {
                "project": {"key": self.project_key},
                "summary": f"[{cr_record.cr_type.upper()}] {cr_record.title}",
                "description": {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": cr_record.description}]}]},
                "issuetype": {"name": self._map_cr_type_to_issue(cr_record.cr_type)},
                "labels": cr_record.tags,
                "customfield_affected_systems": cr_record.affected_systems,
                "_meta": {"note": "Agent generated draft. Review before submission.", "cr_id": cr_record.cr_id},
            }
            return ConnectorResult(success=True, data=draft)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    @staticmethod
    def _map_cr_type_to_issue(cr_type: str) -> str:
        return {"new_dev": "New Feature", "feature_change": "Improvement", "db_change": "Change"}.get(cr_type, "Task")
