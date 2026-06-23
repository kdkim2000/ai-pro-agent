# src/connectors/mock/master_mock.py
"""Program Master / Table Master Mock (T1-2_GUIDE.md Section 5)"""
from __future__ import annotations
from typing import Any, Dict
from ..base import BaseMasterConnector, ConnectorResult, OracleTableInfo, ProgramMasterRecord


class MasterMockConnector(BaseMasterConnector):
    """Program Master / Table Master Mock"""
    is_mock = True

    _PROGRAMS = {
        "SHI_SHIP_ORDER_01": ProgramMasterRecord(
            program_id="SHI_SHIP_ORDER_01", program_name="Ship Order Status Inquiry",
            system_code="SHIP", menu_path="Sales > Order Management",
            dev_language="Java", status="active", created_at="2025-06-01",
            related_tables=["SHIP_ORDER"],
        ),
    }
    _TABLES = {"SHIP_ORDER": True, "MATERIAL_INOUT": True}

    def health_check(self) -> ConnectorResult:
        return ConnectorResult(success=True, data="mock-connected")

    def check_program_registered(self, program_id: str) -> ConnectorResult:
        rec = self._PROGRAMS.get(program_id)
        if rec:
            return ConnectorResult(success=True, data={"registered": True, "record": rec})
        return ConnectorResult(success=True, data={"registered": False, "record": None})

    def check_table_registered(self, table_name: str) -> ConnectorResult:
        registered = table_name.upper() in self._TABLES
        return ConnectorResult(success=True, data={"registered": registered, "record": None})

    def build_program_master_draft(self, context: Dict[str, Any]) -> ConnectorResult:
        draft = {
            "program_id": context.get("program_id", ""), "program_name": context.get("program_name", ""),
            "system_code": context.get("system_code", ""), "menu_path": context.get("menu_path", ""),
            "dev_language": context.get("dev_language", "Java"),
            "related_tables": context.get("affected_tables", []),
            "_meta": {"note": "Mock draft", "cr_id": context.get("cr_id", "")},
        }
        return ConnectorResult(success=True, data=draft)

    def build_table_master_draft(self, table_info: OracleTableInfo) -> ConnectorResult:
        draft = {
            "table_name": table_info.table_name, "owner": table_info.owner,
            "description": table_info.comments or "",
            "columns": [{"column_name": c.get("column_name", ""), "data_type": c.get("data_type", "")} for c in table_info.columns],
            "_meta": {"note": "Mock draft from Oracle dictionary"},
        }
        return ConnectorResult(success=True, data=draft)
