# src/connectors/base.py
"""커넥터 공통 추상 기반 클래스 및 데이터 모델

T1-2_GUIDE.md Section 3 기반 구현.
모든 사내 시스템 커넥터가 공유하는 BaseConnector ABC와
Skill 간 데이터 교환에 사용되는 공통 데이터 모델을 정의한다.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum
import logging
import time

logger = logging.getLogger(__name__)


# -- Common Enums ----------------------------------------------------------

class ConnectorType(str, Enum):
    GITHUB      = "github"
    CONFLUENCE  = "confluence"
    JSM         = "jsm"
    DOODREAM    = "doodream"
    ORACLE      = "oracle"
    MASTER      = "master"          # Program Master / Table Master
    DICTIONARY  = "dictionary"      # Term Dictionary / Word Dictionary


class AccessMode(str, Enum):
    READ  = "read"
    WRITE = "write"     # HITL approval required


# -- Common Data Models ----------------------------------------------------

@dataclass
class ConnectorResult:
    """Connector response wrapper"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    source: Optional[str] = None
    elapsed_ms: Optional[float] = None


@dataclass
class CodeFile:
    """GitHub code file"""
    path: str
    content: str
    repo: str
    branch: str
    sha: str
    url: str
    language: Optional[str] = None


@dataclass
class ConfluencePage:
    """Confluence page"""
    page_id: str
    title: str
    content: str
    space_key: str
    url: str
    last_modified: str
    labels: List[str] = field(default_factory=list)


@dataclass
class CRRecord:
    """Doodream CR record.

    두드림이 실제 관리하는(=신뢰 가능) 필드: cr_id, title, description, cr_type,
    status, requester, assignee, created_at, closed_at.

    아래 4개 필드는 두드림에서 관리되지 않는다(미관리). 타 소스/스킬에서 채운다:
      - affected_systems → Oracle 영향분석(T3-2)에서 도출
      - actual_hours / estimated_hours → 공수 산정(T3-5) 별도 실적 소스
      - tags → 분류 스킬이 생성
    RAG 적재(src/rag/collector.py)는 이 4개 필드를 직렬화하지 않는다.
    """
    cr_id: str
    title: str
    description: str
    cr_type: str            # new_dev | feature_change | db_change
    status: str
    requester: str
    assignee: str
    created_at: str
    closed_at: Optional[str] = None
    # ── 이하 두드림 미관리(타 소스/스킬에서 채움) ──
    actual_hours: Optional[float] = None
    estimated_hours: Optional[float] = None
    affected_systems: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


@dataclass
class OracleTableInfo:
    """Oracle dictionary table metadata"""
    table_name: str
    owner: str
    columns: List[Dict[str, str]]
    dependencies: List[str]
    row_count: Optional[int] = None
    comments: Optional[str] = None


@dataclass
class ProgramMasterRecord:
    """Program Master record"""
    program_id: str
    program_name: str
    system_code: str
    menu_path: str
    dev_language: str
    status: str
    created_at: str
    related_tables: List[str] = field(default_factory=list)


@dataclass
class TermRecord:
    """Term / Word Dictionary record"""
    term_id: str
    term_ko: str
    term_en: str
    abbreviation: str
    definition: str
    domain: str
    status: str             # approved | pending


# -- BaseConnector ABC -----------------------------------------------------

class BaseConnector(ABC):
    """
    Abstract base class for all connectors.

    Skill code depends only on this interface,
    allowing real <-> mock connector swap without Skill code change.
    """

    connector_type: ConnectorType
    is_mock: bool = False

    def _log_call(
        self,
        method: str,
        params: Dict[str, Any],
        result: ConnectorResult,
    ) -> None:
        """Log all connector calls for audit trail"""
        logger.info(
            "connector_call",
            extra={
                "connector": self.connector_type.value,
                "method": method,
                "params": {k: str(v)[:100] for k, v in params.items()},
                "success": result.success,
                "elapsed_ms": result.elapsed_ms,
                "is_mock": self.is_mock,
            },
        )

    def _timed_call(self, fn, *args, **kwargs):
        """Execution time measurement helper"""
        start = time.monotonic()
        try:
            result = fn(*args, **kwargs)
            elapsed = (time.monotonic() - start) * 1000
            if isinstance(result, ConnectorResult):
                result.elapsed_ms = elapsed
            return result
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            return ConnectorResult(
                success=False,
                error=str(e),
                elapsed_ms=elapsed,
            )

    @abstractmethod
    def health_check(self) -> ConnectorResult:
        """Check connection status"""
        ...


# -- System-specific ABCs -------------------------------------------------

class BaseGitHubConnector(BaseConnector):
    connector_type = ConnectorType.GITHUB

    @abstractmethod
    def search_code(self, query: str, repo: Optional[str] = None, top_k: int = 5) -> ConnectorResult:
        ...

    @abstractmethod
    def get_file(self, repo: str, path: str, ref: str = "main") -> ConnectorResult:
        ...

    @abstractmethod
    def list_repos(self, org: str) -> ConnectorResult:
        ...

    @abstractmethod
    def create_pr_draft(self, repo: str, title: str, body: str, head: str, base: str = "main") -> ConnectorResult:
        ...


class BaseConfluenceConnector(BaseConnector):
    connector_type = ConnectorType.CONFLUENCE

    @abstractmethod
    def search_pages(self, query: str, space_key: Optional[str] = None, top_k: int = 5) -> ConnectorResult:
        ...

    @abstractmethod
    def get_page(self, page_id: str) -> ConnectorResult:
        ...

    @abstractmethod
    def get_template(self, template_name: str) -> ConnectorResult:
        ...

    @abstractmethod
    def create_page(self, space_key: str, title: str, content: str, parent_id: Optional[str] = None) -> ConnectorResult:
        ...


class BaseJSMConnector(BaseConnector):
    connector_type = ConnectorType.JSM

    @abstractmethod
    def get_issue(self, issue_key: str) -> ConnectorResult:
        ...

    @abstractmethod
    def search_issues(self, jql: str, top_k: int = 10) -> ConnectorResult:
        ...

    @abstractmethod
    def build_issue_draft(self, cr_record: CRRecord) -> ConnectorResult:
        ...


class BaseDoodreamConnector(BaseConnector):
    connector_type = ConnectorType.DOODREAM

    @abstractmethod
    def get_cr(self, cr_id: str) -> ConnectorResult:
        ...

    @abstractmethod
    def search_cr_history(self, query: str, cr_type: Optional[str] = None, top_k: int = 10) -> ConnectorResult:
        ...

    @abstractmethod
    def get_recent_crs(self, days: int = 90, status: Optional[str] = None) -> ConnectorResult:
        ...


class BaseOracleConnector(BaseConnector):
    connector_type = ConnectorType.ORACLE

    @abstractmethod
    def get_table_info(self, table_name: str, owner: Optional[str] = None) -> ConnectorResult:
        ...

    @abstractmethod
    def get_dependencies(self, object_name: str, object_type: str = "TABLE") -> ConnectorResult:
        ...

    @abstractmethod
    def get_affected_programs(self, table_name: str) -> ConnectorResult:
        ...

    @abstractmethod
    def check_consistency(self, table_names: List[str]) -> ConnectorResult:
        ...


class BaseMasterConnector(BaseConnector):
    connector_type = ConnectorType.MASTER

    @abstractmethod
    def check_program_registered(self, program_id: str) -> ConnectorResult:
        ...

    @abstractmethod
    def check_table_registered(self, table_name: str) -> ConnectorResult:
        ...

    @abstractmethod
    def build_program_master_draft(self, context: Dict[str, Any]) -> ConnectorResult:
        ...

    @abstractmethod
    def build_table_master_draft(self, table_info: OracleTableInfo) -> ConnectorResult:
        ...


class BaseDictionaryConnector(BaseConnector):
    connector_type = ConnectorType.DICTIONARY

    @abstractmethod
    def check_term_registered(self, term: str) -> ConnectorResult:
        ...

    @abstractmethod
    def detect_unregistered_terms(self, text: str) -> ConnectorResult:
        ...

    @abstractmethod
    def build_term_draft(self, term_ko: str, context: str) -> ConnectorResult:
        ...
