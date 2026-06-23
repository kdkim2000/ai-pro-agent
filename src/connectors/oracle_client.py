# src/connectors/oracle_client.py
"""Oracle 19c Dictionary Read-only connector (T1-2_GUIDE.md Section 4.5)"""
from __future__ import annotations
from typing import List, Optional
import os
from .base import BaseOracleConnector, ConnectorResult, OracleTableInfo

try:
    import oracledb as cx_Oracle
    ORACLE_DRIVER = "oracledb"
except ImportError:
    try:
        import cx_Oracle
        ORACLE_DRIVER = "cx_Oracle"
    except ImportError:
        cx_Oracle = None
        ORACLE_DRIVER = None


class Oracle19cConnector(BaseOracleConnector):
    """Oracle 19c Dictionary Read-only connector using ALL_DEPENDENCIES, ALL_TAB_COLUMNS views"""

    SQL_TABLE_INFO = """
        SELECT t.table_name, t.owner, t.num_rows, c.comments AS table_comments
        FROM all_tables t
        LEFT JOIN all_tab_comments c ON c.table_name = t.table_name AND c.owner = t.owner
        WHERE t.table_name = UPPER(:table_name) AND t.owner = UPPER(:owner)
    """
    SQL_COLUMNS = """
        SELECT col.column_name, col.data_type, col.data_length, col.nullable, col.data_default, com.comments
        FROM all_tab_columns col
        LEFT JOIN all_col_comments com ON com.table_name = col.table_name AND com.column_name = col.column_name AND com.owner = col.owner
        WHERE col.table_name = UPPER(:table_name) AND col.owner = UPPER(:owner)
        ORDER BY col.column_id
    """
    SQL_DEPENDENCIES = """
        SELECT DISTINCT d.name AS object_name, d.type AS object_type, d.owner AS object_owner
        FROM all_dependencies d
        WHERE d.referenced_name = UPPER(:object_name) AND d.referenced_type = UPPER(:object_type) AND d.referenced_owner = UPPER(:owner)
        ORDER BY d.type, d.name
    """
    SQL_AFFECTED_PROGRAMS = """
        SELECT DISTINCT d.name AS program_name, d.type AS program_type, d.owner
        FROM all_dependencies d
        WHERE d.referenced_name = UPPER(:table_name) AND d.referenced_type = 'TABLE'
          AND d.type IN ('PROCEDURE', 'FUNCTION', 'PACKAGE', 'PACKAGE BODY', 'TRIGGER', 'VIEW')
        ORDER BY d.type, d.name
    """

    def __init__(self, dsn: Optional[str] = None, user: Optional[str] = None, password: Optional[str] = None, default_owner: Optional[str] = None):
        if cx_Oracle is None:
            raise ImportError("Oracle driver not installed. Run 'pip install oracledb' or 'pip install cx_Oracle'.")
        self.dsn = dsn or os.getenv("ORACLE_DSN", "")
        self.user = user or os.getenv("ORACLE_USER", "")
        self.password = password or os.getenv("ORACLE_PASSWORD", "")
        self.default_owner = default_owner or os.getenv("ORACLE_DEFAULT_OWNER", self.user.upper())
        self._conn = None

    def _get_connection(self):
        if self._conn is None:
            self._conn = cx_Oracle.connect(user=self.user, password=self.password, dsn=self.dsn)
        return self._conn

    def _execute(self, sql: str, params: dict) -> list:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(sql, params)
        columns = [col[0].lower() for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def health_check(self) -> ConnectorResult:
        try:
            self._execute("SELECT 1 FROM dual", {})
            return ConnectorResult(success=True, data="connected", source=self.dsn)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    def get_table_info(self, table_name: str, owner: Optional[str] = None) -> ConnectorResult:
        try:
            owner = (owner or self.default_owner).upper()
            tbl_rows = self._execute(self.SQL_TABLE_INFO, {"table_name": table_name, "owner": owner})
            if not tbl_rows:
                return ConnectorResult(success=False, error=f"Table {owner}.{table_name} not found")
            tbl = tbl_rows[0]
            col_rows = self._execute(self.SQL_COLUMNS, {"table_name": table_name, "owner": owner})
            return ConnectorResult(success=True, data=OracleTableInfo(
                table_name=table_name.upper(), owner=owner, row_count=tbl.get("num_rows"),
                comments=tbl.get("table_comments"), columns=col_rows, dependencies=[],
            ))
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    def get_dependencies(self, object_name: str, object_type: str = "TABLE") -> ConnectorResult:
        try:
            rows = self._execute(self.SQL_DEPENDENCIES, {"object_name": object_name, "object_type": object_type, "owner": self.default_owner})
            return ConnectorResult(success=True, data=rows)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    def get_affected_programs(self, table_name: str) -> ConnectorResult:
        try:
            rows = self._execute(self.SQL_AFFECTED_PROGRAMS, {"table_name": table_name})
            return ConnectorResult(success=True, data={"programs": [r["program_name"] for r in rows], "detail": rows})
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    def check_consistency(self, table_names: List[str]) -> ConnectorResult:
        try:
            results = []
            for t in table_names:
                rows = self._execute("SELECT COUNT(*) AS cnt FROM all_tables WHERE table_name = UPPER(:t) AND owner = UPPER(:o)", {"t": t, "o": self.default_owner})
                results.append({"table_name": t, "exists_in_oracle": rows[0]["cnt"] > 0 if rows else False})
            return ConnectorResult(success=True, data=results)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))
