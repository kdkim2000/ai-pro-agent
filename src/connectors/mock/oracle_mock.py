# src/connectors/mock/oracle_mock.py
"""Oracle 19c Dictionary Mock (T1-2_GUIDE.md Section 5)"""
from __future__ import annotations
from typing import List, Optional
from ..base import BaseOracleConnector, ConnectorResult, OracleTableInfo


class OracleMockConnector(BaseOracleConnector):
    """Oracle 19c Dictionary Mock -- realistic table metadata"""
    is_mock = True

    _TABLE_SAMPLES = {
        "SHIP_ORDER": OracleTableInfo(
            table_name="SHIP_ORDER", owner="SHIC", row_count=15420, comments="Ship order master table",
            columns=[
                {"column_name": "ORDER_NO", "data_type": "VARCHAR2", "nullable": "N", "comments": "Order number"},
                {"column_name": "SHIP_NAME", "data_type": "VARCHAR2", "nullable": "Y", "comments": "Ship name"},
                {"column_name": "CLIENT_NM", "data_type": "VARCHAR2", "nullable": "Y", "comments": "Client name"},
                {"column_name": "DELIVERY_DT", "data_type": "DATE", "nullable": "Y", "comments": "Delivery date"},
            ],
            dependencies=["PKG_SHIP_ORDER", "V_SHIP_STATUS", "TRG_SHIP_ORDER_AI"],
        ),
        "MATERIAL_INOUT": OracleTableInfo(
            table_name="MATERIAL_INOUT", owner="SHIC", row_count=203450, comments="Material in/out history table",
            columns=[
                {"column_name": "INOUT_SEQ", "data_type": "NUMBER", "nullable": "N", "comments": "In/out sequence"},
                {"column_name": "MATERIAL_CD", "data_type": "VARCHAR2", "nullable": "N", "comments": "Material code"},
                {"column_name": "INOUT_QTY", "data_type": "NUMBER", "nullable": "Y", "comments": "In/out quantity"},
            ],
            dependencies=["PKG_MATERIAL", "V_MATERIAL_STOCK"],
        ),
    }

    def health_check(self) -> ConnectorResult:
        return ConnectorResult(success=True, data="mock-connected")

    def get_table_info(self, table_name: str, owner: Optional[str] = None) -> ConnectorResult:
        tbl = self._TABLE_SAMPLES.get(table_name.upper())
        if tbl:
            return ConnectorResult(success=True, data=tbl)
        return ConnectorResult(success=False, error=f"Mock: Table '{table_name}' not found")

    def get_dependencies(self, object_name: str, object_type: str = "TABLE") -> ConnectorResult:
        tbl = self._TABLE_SAMPLES.get(object_name.upper())
        deps = [{"object_name": d, "object_type": "PACKAGE"} for d in (tbl.dependencies if tbl else [])]
        return ConnectorResult(success=True, data=deps)

    def get_affected_programs(self, table_name: str) -> ConnectorResult:
        tbl = self._TABLE_SAMPLES.get(table_name.upper())
        programs = tbl.dependencies if tbl else []
        return ConnectorResult(success=True, data={"programs": programs, "detail": []})

    def check_consistency(self, table_names: List[str]) -> ConnectorResult:
        results = [{"table_name": t, "exists_in_oracle": t.upper() in self._TABLE_SAMPLES} for t in table_names]
        return ConnectorResult(success=True, data=results)
