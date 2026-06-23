# src/connectors/mock/jsm_mock.py
"""JSM Mock (T1-2_GUIDE.md Section 5)"""
from __future__ import annotations
from ..base import BaseJSMConnector, ConnectorResult, CRRecord


class JSMMockConnector(BaseJSMConnector):
    """JSM (Jira Service Management) Mock"""
    is_mock = True

    def health_check(self) -> ConnectorResult:
        return ConnectorResult(success=True, data="mock-connected")

    def get_issue(self, issue_key: str) -> ConnectorResult:
        return ConnectorResult(success=True, data={
            "key": issue_key, "fields": {"summary": f"Mock issue {issue_key}", "status": {"name": "Open"}},
        })

    def search_issues(self, jql: str, top_k: int = 10) -> ConnectorResult:
        return ConnectorResult(success=True, data=[
            {"key": "SHIC-001", "fields": {"summary": "Ship order screen", "status": {"name": "Done"}}},
            {"key": "SHIC-002", "fields": {"summary": "Material schema change", "status": {"name": "In Progress"}}},
        ][:top_k])

    def build_issue_draft(self, cr_record: CRRecord) -> ConnectorResult:
        draft = {
            "project": {"key": "SHIC"},
            "summary": f"[{cr_record.cr_type.upper()}] {cr_record.title}",
            "description": {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": cr_record.description}]}]},
            "issuetype": {"name": "Task"},
            "labels": cr_record.tags,
            "_meta": {"note": "Agent generated draft.", "cr_id": cr_record.cr_id},
        }
        return ConnectorResult(success=True, data=draft)
