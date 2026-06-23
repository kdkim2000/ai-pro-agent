# src/connectors/mock/doodream_mock.py
"""Doodream Mock (T1-2_GUIDE.md Section 5)"""
from __future__ import annotations
from typing import Optional
from ..base import BaseDoodreamConnector, ConnectorResult, CRRecord


class DoodreamMockConnector(BaseDoodreamConnector):
    """Doodream Mock -- realistic CR sample data"""
    is_mock = True

    _CR_SAMPLES = [
        CRRecord(cr_id="CR-2026-0312", title="Ship Order Status Inquiry Screen Development",
                 description="New screen for ship order status query with order number, ship name, client, delivery date.",
                 cr_type="new_dev", status="closed", requester="Hong", assignee="Kim",
                 created_at="2026-03-10T09:00:00", closed_at="2026-03-25T18:00:00",
                 actual_hours=24.0, estimated_hours=20.0,
                 affected_systems=["SHIP_ORDER", "PROGRAM_MASTER"], tags=["new_screen", "inquiry", "sales"]),
        CRRecord(cr_id="CR-2026-0287", title="Material INOUT Table Schema Change",
                 description="Add LOT_NO column to MATERIAL_INOUT table for material management improvement.",
                 cr_type="db_change", status="closed", requester="Lee", assignee="Park",
                 created_at="2026-02-20T10:30:00", closed_at="2026-03-05T17:00:00",
                 actual_hours=16.0, estimated_hours=12.0,
                 affected_systems=["MATERIAL_INOUT", "TABLE_MASTER"], tags=["db_change", "material"]),
        CRRecord(cr_id="CR-2026-0198", title="Process Progress Screen Feature Change",
                 description="Add department filter to existing process progress inquiry screen.",
                 cr_type="feature_change", status="closed", requester="Choi", assignee="Kim",
                 created_at="2026-01-15T11:00:00", closed_at="2026-01-28T16:00:00",
                 actual_hours=12.0, estimated_hours=10.0,
                 affected_systems=["PROCESS_STATUS"], tags=["feature_change", "process"]),
    ]

    def health_check(self) -> ConnectorResult:
        return ConnectorResult(success=True, data="mock-connected")

    def get_cr(self, cr_id: str) -> ConnectorResult:
        for cr in self._CR_SAMPLES:
            if cr.cr_id == cr_id:
                return ConnectorResult(success=True, data=cr)
        return ConnectorResult(success=False, error=f"Mock: CR '{cr_id}' not found")

    def search_cr_history(self, query: str, cr_type: Optional[str] = None, top_k: int = 10) -> ConnectorResult:
        results = self._CR_SAMPLES
        if cr_type:
            results = [cr for cr in results if cr.cr_type == cr_type]
        return ConnectorResult(success=True, data=results[:top_k])

    def get_recent_crs(self, days: int = 90, status: Optional[str] = None) -> ConnectorResult:
        results = self._CR_SAMPLES
        if status:
            results = [cr for cr in results if cr.status == status]
        return ConnectorResult(success=True, data=results)
