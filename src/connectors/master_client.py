# src/connectors/master_client.py
"""Program Master / Table Master connector (T1-2_GUIDE.md Section 4.6)"""
from __future__ import annotations
from typing import Any, Dict, Optional
import httpx, os
from .base import BaseMasterConnector, ConnectorResult, OracleTableInfo, ProgramMasterRecord


class MasterSystemConnector(BaseMasterConnector):
    """Program Master / Table Master management system connector"""

    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None, timeout: int = 30):
        self.base_url = (base_url or os.getenv("MASTER_SYSTEM_URL", "")).rstrip("/")
        self.token = token or os.getenv("MASTER_SYSTEM_TOKEN", "")
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

    def check_program_registered(self, program_id: str) -> ConnectorResult:
        try:
            data = self._get(f"/programs/{program_id}")
            record = ProgramMasterRecord(
                program_id=data.get("program_id", ""), program_name=data.get("program_name", ""),
                system_code=data.get("system_code", ""), menu_path=data.get("menu_path", ""),
                dev_language=data.get("dev_language", ""), status=data.get("status", ""),
                created_at=data.get("created_at", ""), related_tables=data.get("related_tables", []),
            )
            return ConnectorResult(success=True, data={"registered": True, "record": record})
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return ConnectorResult(success=True, data={"registered": False, "record": None})
            return ConnectorResult(success=False, error=str(e))

    def check_table_registered(self, table_name: str) -> ConnectorResult:
        try:
            data = self._get(f"/tables/{table_name.upper()}")
            return ConnectorResult(success=True, data={"registered": True, "record": data})
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return ConnectorResult(success=True, data={"registered": False, "record": None})
            return ConnectorResult(success=False, error=str(e))

    def build_program_master_draft(self, context: Dict[str, Any]) -> ConnectorResult:
        draft = {
            "program_id": context.get("program_id", ""), "program_name": context.get("program_name", ""),
            "system_code": context.get("system_code", ""), "menu_path": context.get("menu_path", ""),
            "dev_language": context.get("dev_language", "Java"), "description": context.get("description", ""),
            "related_tables": context.get("affected_tables", []),
            "_meta": {"note": "Agent generated draft. Review before submission.", "cr_id": context.get("cr_id", "")},
        }
        return ConnectorResult(success=True, data=draft)

    def build_table_master_draft(self, table_info: OracleTableInfo) -> ConnectorResult:
        draft = {
            "table_name": table_info.table_name, "owner": table_info.owner,
            "description": table_info.comments or "",
            "columns": [{"column_name": c.get("column_name", ""), "data_type": c.get("data_type", ""), "nullable": c.get("nullable", "Y"), "description": c.get("comments", "")} for c in table_info.columns],
            "_meta": {"note": "Auto-generated from Oracle dictionary. Review before submission.", "row_count": table_info.row_count},
        }
        return ConnectorResult(success=True, data=draft)
