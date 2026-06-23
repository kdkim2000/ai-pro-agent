# T1-2. 시스템 연동 인터페이스 설계 — 수행 가이드

> **과제**: 프로그램 개발 전주기 지원 AI Agent  
> **Task**: T1-2. 사내 시스템 연동 인터페이스 설계 및 커넥터 구현  
> **환경**: 삼성SDS 사내망 (SCP/VDI)  
> **선행 조건**: T1-1 완료 (환경 셋업, 스모크 테스트 5개 통과)

---

## 1. 개요

### 1.1 목적

본 Task는 AI Agent의 8개 Skill이 사내 시스템 데이터를 **일관된 인터페이스**로 조회·활용할 수 있도록,  
각 시스템별 연동 클라이언트를 설계·구현하는 것을 목표로 한다.

단순 API 호출 코드를 나열하는 것이 아니라, **추상화 계층(ABC)**을 통해 Skill 코드가 특정 시스템에 종속되지 않도록 설계한다.  
이를 통해 T3 Skill 구현 시 Mock → 실 클라이언트 교체가 코드 변경 없이 가능해진다.

### 1.2 연동 대상 시스템 및 용도

| 시스템 | 용도 | 접근 방식 | Skill 연동 대상 |
|--------|------|-----------|-----------------|
| GitHub Enterprise | 코드베이스 검색, 파일 조회, PR 초안 생성 | REST API (PAT 인증) | T3-3 요구사항, T3-4 영향도, T3-10 배포 |
| Confluence | 문서 검색, 산출물 초안 저장, 템플릿 조회 | REST API (API Token) | T3-3 요구사항, T3-7 산출물 |
| JSM | 변경 등록 입력값 초안 생성, 티켓 상태 조회 | REST API (Jira 호환) | T3-8 등록 지원 |
| 두드림 | CR 접수·처리 이력 조회 | REST API | T3-3 요구사항, T3-5 공수 산정 |
| Oracle 19c | 딕셔너리 뷰 조회 (영향도 분석) | cx_Oracle (Read-only) | T3-4 영향도 분석 |
| 프로그램마스터 | 등록 여부 조회, 입력값 초안 생성 | REST API (자체 개발) | T3-8 등록 지원, T3-9 게이트 |
| 테이블마스터 | 등록 여부 조회, 입력값 초안 생성 | REST API (자체 개발) | T3-8 등록 지원, T3-9 게이트 |
| 용어사전·단어사전 | 미등록 용어 감지, 신규 등록 안내 | REST API (자체 개발) | T3-8 등록 지원, T3-9 게이트 |

### 1.3 설계 원칙

1. **추상화 우선**: 모든 커넥터는 `BaseConnector` ABC를 구현. Skill은 추상 인터페이스만 의존
2. **Mock 우선 개발**: T3 Skill 구현 시 실 시스템 연동 없이 Mock으로 선행 개발 가능
3. **Read/Write 분리**: 조회 메서드와 변경 메서드를 명확히 구분, 변경은 HITL 승인 후만 허용
4. **오류 격리**: 개별 시스템 장애가 전체 Agent 중단으로 이어지지 않도록 예외 처리
5. **감사 추적**: 모든 외부 시스템 호출 이력 로그 기록

### 1.4 완료 기준 (Definition of Done)

- [ ] `BaseConnector` ABC 및 공통 데이터 모델 정의 완료
- [ ] 8개 시스템 커넥터 클래스 구현 완료
- [ ] 8개 시스템 Mock 커넥터 구현 완료 (T3 선행 개발용)
- [ ] `ConnectorFactory` 구현 완료 (환경변수 기반 실/Mock 자동 선택)
- [ ] 실 연동 가능한 시스템 최소 3개 이상 연동 테스트 통과
- [ ] 전체 Mock 기반 통합 테스트 통과
- [ ] `src/connectors/` 모듈 GitHub Enterprise push 완료

---

## 2. 디렉토리 구조

```
src/connectors/
├── __init__.py
├── base.py                  # BaseConnector ABC + 공통 데이터 모델
├── factory.py               # ConnectorFactory (실/Mock 자동 선택)
├── github_client.py         # GitHub Enterprise 커넥터
├── confluence_client.py     # Confluence 커넥터
├── jsm_client.py            # JSM 커넥터
├── doodream_client.py       # 두드림 커넥터
├── oracle_client.py         # Oracle 19c 딕셔너리 커넥터
├── master_client.py         # 프로그램마스터·테이블마스터 커넥터
├── dictionary_client.py     # 용어사전·단어사전 커넥터
└── mock/
    ├── __init__.py
    ├── github_mock.py
    ├── confluence_mock.py
    ├── jsm_mock.py
    ├── doodream_mock.py
    ├── oracle_mock.py
    ├── master_mock.py
    └── dictionary_mock.py

tests/connectors/
├── test_github.py
├── test_confluence.py
├── test_jsm.py
├── test_doodream.py
├── test_oracle.py
├── test_master.py
├── test_dictionary.py
└── test_factory.py
```

---

## 3. BaseConnector ABC 및 공통 데이터 모델

모든 커넥터가 공유하는 추상 기반 클래스와 데이터 모델을 정의한다.

```python
# src/connectors/base.py
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum
import logging
import time

logger = logging.getLogger(__name__)


# ── 공통 Enum ────────────────────────────────────────────────

class ConnectorType(str, Enum):
    GITHUB      = "github"
    CONFLUENCE  = "confluence"
    JSM         = "jsm"
    DOODREAM    = "doodream"
    ORACLE      = "oracle"
    MASTER      = "master"          # 프로그램마스터·테이블마스터
    DICTIONARY  = "dictionary"      # 용어사전·단어사전


class AccessMode(str, Enum):
    READ  = "read"
    WRITE = "write"     # HITL 승인 후에만 허용


# ── 공통 데이터 모델 ─────────────────────────────────────────

@dataclass
class ConnectorResult:
    """커넥터 응답 공통 래퍼"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    source: Optional[str] = None        # 데이터 출처 (URL, 파일경로 등)
    elapsed_ms: Optional[float] = None  # 호출 소요 시간


@dataclass
class CodeFile:
    """GitHub 코드 파일"""
    path: str
    content: str
    repo: str
    branch: str
    sha: str
    url: str
    language: Optional[str] = None


@dataclass
class ConfluencePage:
    """Confluence 페이지"""
    page_id: str
    title: str
    content: str            # 마크다운 또는 HTML
    space_key: str
    url: str
    last_modified: str
    labels: List[str] = field(default_factory=list)


@dataclass
class CRRecord:
    """두드림 CR 이력"""
    cr_id: str
    title: str
    description: str
    cr_type: str            # new_dev | feature_change | db_change
    status: str
    requester: str
    assignee: str
    created_at: str
    closed_at: Optional[str]
    actual_hours: Optional[float]   # 실적 공수
    estimated_hours: Optional[float]
    affected_systems: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


@dataclass
class OracleTableInfo:
    """Oracle 딕셔너리 테이블 메타데이터"""
    table_name: str
    owner: str
    columns: List[Dict[str, str]]   # [{name, data_type, nullable, comments}]
    dependencies: List[str]         # 이 테이블을 참조하는 프로그램/패키지
    row_count: Optional[int] = None
    comments: Optional[str] = None


@dataclass
class ProgramMasterRecord:
    """프로그램마스터 레코드"""
    program_id: str
    program_name: str
    system_code: str
    menu_path: str
    dev_language: str
    status: str             # active | inactive
    created_at: str
    related_tables: List[str] = field(default_factory=list)


@dataclass
class TermRecord:
    """용어사전·단어사전 레코드"""
    term_id: str
    term_ko: str            # 한국어 용어
    term_en: str            # 영문 용어
    abbreviation: str       # 약어
    definition: str
    domain: str
    status: str             # approved | pending


# ── BaseConnector ABC ────────────────────────────────────────

class BaseConnector(ABC):
    """
    모든 사내 시스템 커넥터의 추상 기반 클래스.

    Skill 코드는 이 인터페이스만 의존하므로,
    실 커넥터 ↔ Mock 커넥터 교체 시 Skill 코드 변경 불필요.
    """

    connector_type: ConnectorType
    is_mock: bool = False

    def _log_call(
        self,
        method: str,
        params: Dict[str, Any],
        result: ConnectorResult,
    ) -> None:
        """모든 커넥터 호출을 감사 로그에 기록"""
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
        """실행 시간 측정 헬퍼"""
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
        """연결 상태 확인"""
        ...


class BaseGitHubConnector(BaseConnector):
    connector_type = ConnectorType.GITHUB

    @abstractmethod
    def search_code(self, query: str, repo: Optional[str] = None, top_k: int = 5) -> ConnectorResult:
        """코드 검색 — 반환: List[CodeFile]"""
        ...

    @abstractmethod
    def get_file(self, repo: str, path: str, ref: str = "main") -> ConnectorResult:
        """파일 내용 조회 — 반환: CodeFile"""
        ...

    @abstractmethod
    def list_repos(self, org: str) -> ConnectorResult:
        """조직 내 레포지토리 목록 — 반환: List[str]"""
        ...

    @abstractmethod
    def create_pr_draft(
        self,
        repo: str,
        title: str,
        body: str,
        head: str,
        base: str = "main",
    ) -> ConnectorResult:
        """PR 초안 생성 (HITL 승인 후 호출) — 반환: pr_url"""
        ...


class BaseConfluenceConnector(BaseConnector):
    connector_type = ConnectorType.CONFLUENCE

    @abstractmethod
    def search_pages(self, query: str, space_key: Optional[str] = None, top_k: int = 5) -> ConnectorResult:
        """페이지 검색 — 반환: List[ConfluencePage]"""
        ...

    @abstractmethod
    def get_page(self, page_id: str) -> ConnectorResult:
        """페이지 내용 조회 — 반환: ConfluencePage"""
        ...

    @abstractmethod
    def get_template(self, template_name: str) -> ConnectorResult:
        """산출물 표준 템플릿 조회 — 반환: str (템플릿 본문)"""
        ...

    @abstractmethod
    def create_page(
        self,
        space_key: str,
        title: str,
        content: str,
        parent_id: Optional[str] = None,
    ) -> ConnectorResult:
        """페이지 생성 (HITL 승인 후 호출) — 반환: page_id"""
        ...


class BaseJSMConnector(BaseConnector):
    connector_type = ConnectorType.JSM

    @abstractmethod
    def get_issue(self, issue_key: str) -> ConnectorResult:
        """이슈 조회 — 반환: dict"""
        ...

    @abstractmethod
    def search_issues(self, jql: str, top_k: int = 10) -> ConnectorResult:
        """JQL 검색 — 반환: List[dict]"""
        ...

    @abstractmethod
    def build_issue_draft(self, cr_record: CRRecord) -> ConnectorResult:
        """CR 기반 JSM 등록 입력값 초안 생성 — 반환: dict (입력 필드)"""
        ...


class BaseDoodreamConnector(BaseConnector):
    connector_type = ConnectorType.DOODREAM

    @abstractmethod
    def get_cr(self, cr_id: str) -> ConnectorResult:
        """CR 단건 조회 — 반환: CRRecord"""
        ...

    @abstractmethod
    def search_cr_history(
        self,
        query: str,
        cr_type: Optional[str] = None,
        top_k: int = 10,
    ) -> ConnectorResult:
        """유사 CR 이력 검색 — 반환: List[CRRecord]"""
        ...

    @abstractmethod
    def get_recent_crs(self, days: int = 90, status: Optional[str] = None) -> ConnectorResult:
        """최근 CR 목록 — 반환: List[CRRecord]"""
        ...


class BaseOracleConnector(BaseConnector):
    connector_type = ConnectorType.ORACLE

    @abstractmethod
    def get_table_info(self, table_name: str, owner: Optional[str] = None) -> ConnectorResult:
        """테이블 메타데이터 조회 — 반환: OracleTableInfo"""
        ...

    @abstractmethod
    def get_dependencies(self, object_name: str, object_type: str = "TABLE") -> ConnectorResult:
        """의존 객체 조회 — 반환: List[dict]"""
        ...

    @abstractmethod
    def get_affected_programs(self, table_name: str) -> ConnectorResult:
        """테이블 변경 시 영향받는 프로그램 목록 — 반환: List[str]"""
        ...

    @abstractmethod
    def check_consistency(self, table_names: List[str]) -> ConnectorResult:
        """테이블마스터 대비 Oracle 딕셔너리 정합성 확인 — 반환: List[dict]"""
        ...


class BaseMasterConnector(BaseConnector):
    connector_type = ConnectorType.MASTER

    @abstractmethod
    def check_program_registered(self, program_id: str) -> ConnectorResult:
        """프로그램마스터 등록 여부 확인 — 반환: bool"""
        ...

    @abstractmethod
    def check_table_registered(self, table_name: str) -> ConnectorResult:
        """테이블마스터 등록 여부 확인 — 반환: bool"""
        ...

    @abstractmethod
    def build_program_master_draft(self, context: Dict[str, Any]) -> ConnectorResult:
        """프로그램마스터 등록 입력값 초안 생성 — 반환: dict"""
        ...

    @abstractmethod
    def build_table_master_draft(self, table_info: OracleTableInfo) -> ConnectorResult:
        """테이블마스터 등록 입력값 초안 생성 — 반환: dict"""
        ...


class BaseDictionaryConnector(BaseConnector):
    connector_type = ConnectorType.DICTIONARY

    @abstractmethod
    def check_term_registered(self, term: str) -> ConnectorResult:
        """용어 등록 여부 확인 — 반환: TermRecord | None"""
        ...

    @abstractmethod
    def detect_unregistered_terms(self, text: str) -> ConnectorResult:
        """텍스트 내 미등록 용어 감지 — 반환: List[str]"""
        ...

    @abstractmethod
    def build_term_draft(self, term_ko: str, context: str) -> ConnectorResult:
        """신규 용어 등록 입력값 초안 생성 — 반환: dict"""
        ...
```

---

## 4. 시스템별 실 커넥터 구현

### 4.1 GitHub Enterprise 커넥터

```python
# src/connectors/github_client.py
from __future__ import annotations
from typing import Optional
import httpx
import os
import base64
from .base import (
    BaseGitHubConnector, ConnectorResult, CodeFile
)


class GitHubEnterpriseConnector(BaseGitHubConnector):
    """GitHub Enterprise REST API v3 커넥터"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        timeout: int = 30,
    ):
        self.base_url = (base_url or os.getenv("GITHUB_ENTERPRISE_URL", "")).rstrip("/")
        self.token = token or os.getenv("GITHUB_TOKEN", "")
        self.timeout = timeout
        self._headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _get(self, path: str, params: dict = None) -> dict:
        url = f"{self.base_url}/api/v3{path}"
        with httpx.Client(timeout=self.timeout, verify=False) as client:
            resp = client.get(url, headers=self._headers, params=params or {})
            resp.raise_for_status()
            return resp.json()

    def _post(self, path: str, json: dict) -> dict:
        url = f"{self.base_url}/api/v3{path}"
        with httpx.Client(timeout=self.timeout, verify=False) as client:
            resp = client.post(url, headers=self._headers, json=json)
            resp.raise_for_status()
            return resp.json()

    def health_check(self) -> ConnectorResult:
        try:
            data = self._get("/meta")
            return ConnectorResult(success=True, data=data.get("version"), source=self.base_url)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    def search_code(self, query: str, repo: Optional[str] = None, top_k: int = 5) -> ConnectorResult:
        """
        GitHub 코드 검색.
        query: 검색어 (예: "프로그램마스터 등록 repo:org/repo")
        """
        try:
            q = f"{query} repo:{repo}" if repo else query
            data = self._get("/search/code", params={"q": q, "per_page": top_k})
            files = []
            for item in data.get("items", [])[:top_k]:
                # 파일 내용 개별 조회
                content_data = self._get(
                    f"/repos/{item['repository']['full_name']}/contents/{item['path']}"
                )
                decoded = base64.b64decode(
                    content_data.get("content", "").replace("\n", "")
                ).decode("utf-8", errors="replace")
                files.append(CodeFile(
                    path=item["path"],
                    content=decoded,
                    repo=item["repository"]["full_name"],
                    branch=content_data.get("ref", "main"),
                    sha=content_data.get("sha", ""),
                    url=item["html_url"],
                    language=item.get("language"),
                ))
            return ConnectorResult(success=True, data=files, source=self.base_url)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    def get_file(self, repo: str, path: str, ref: str = "main") -> ConnectorResult:
        try:
            data = self._get(f"/repos/{repo}/contents/{path}", params={"ref": ref})
            decoded = base64.b64decode(
                data.get("content", "").replace("\n", "")
            ).decode("utf-8", errors="replace")
            file = CodeFile(
                path=path, content=decoded, repo=repo,
                branch=ref, sha=data.get("sha", ""), url=data.get("html_url", ""),
            )
            return ConnectorResult(success=True, data=file, source=data.get("html_url"))
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    def list_repos(self, org: str) -> ConnectorResult:
        try:
            data = self._get(f"/orgs/{org}/repos", params={"per_page": 100, "type": "all"})
            repos = [r["full_name"] for r in data]
            return ConnectorResult(success=True, data=repos)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    def create_pr_draft(
        self, repo: str, title: str, body: str, head: str, base: str = "main"
    ) -> ConnectorResult:
        """PR 초안 생성 — HITL 승인 후에만 호출"""
        try:
            data = self._post(f"/repos/{repo}/pulls", json={
                "title": title, "body": body,
                "head": head, "base": base, "draft": True,
            })
            return ConnectorResult(
                success=True,
                data={"pr_number": data["number"], "pr_url": data["html_url"]},
                source=data["html_url"],
            )
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))
```

---

### 4.2 Confluence 커넥터

```python
# src/connectors/confluence_client.py
from __future__ import annotations
from typing import Optional
import httpx, os
from .base import BaseConfluenceConnector, ConnectorResult, ConfluencePage


class ConfluenceConnector(BaseConfluenceConnector):
    """Confluence REST API v2 커넥터"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        timeout: int = 30,
    ):
        self.base_url = (base_url or os.getenv("CONFLUENCE_URL", "")).rstrip("/")
        self.token = token or os.getenv("CONFLUENCE_TOKEN", "")
        self.timeout = timeout
        self._headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _get(self, path: str, params: dict = None) -> dict:
        url = f"{self.base_url}/rest/api{path}"
        with httpx.Client(timeout=self.timeout, verify=False) as client:
            resp = client.get(url, headers=self._headers, params=params or {})
            resp.raise_for_status()
            return resp.json()

    def _post(self, path: str, json: dict) -> dict:
        url = f"{self.base_url}/rest/api{path}"
        with httpx.Client(timeout=self.timeout, verify=False) as client:
            resp = client.post(url, headers=self._headers, json=json)
            resp.raise_for_status()
            return resp.json()

    def health_check(self) -> ConnectorResult:
        try:
            data = self._get("/space", params={"limit": 1})
            return ConnectorResult(success=True, data="connected", source=self.base_url)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    def search_pages(self, query: str, space_key: Optional[str] = None, top_k: int = 5) -> ConnectorResult:
        try:
            cql = f'text ~ "{query}" AND type = "page"'
            if space_key:
                cql += f' AND space = "{space_key}"'
            data = self._get("/content/search", params={"cql": cql, "limit": top_k, "expand": "body.storage"})
            pages = []
            for item in data.get("results", []):
                body = item.get("body", {}).get("storage", {}).get("value", "")
                pages.append(ConfluencePage(
                    page_id=item["id"],
                    title=item["title"],
                    content=body,
                    space_key=item.get("space", {}).get("key", ""),
                    url=f"{self.base_url}{item['_links'].get('webui', '')}",
                    last_modified=item.get("version", {}).get("when", ""),
                    labels=[l["name"] for l in item.get("metadata", {}).get("labels", {}).get("results", [])],
                ))
            return ConnectorResult(success=True, data=pages)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    def get_page(self, page_id: str) -> ConnectorResult:
        try:
            data = self._get(f"/content/{page_id}", params={"expand": "body.storage,version,space"})
            page = ConfluencePage(
                page_id=data["id"],
                title=data["title"],
                content=data["body"]["storage"]["value"],
                space_key=data["space"]["key"],
                url=f"{self.base_url}{data['_links']['webui']}",
                last_modified=data["version"]["when"],
            )
            return ConnectorResult(success=True, data=page, source=page.url)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    def get_template(self, template_name: str) -> ConnectorResult:
        """
        표준 산출물 템플릿 조회.
        Confluence에서 템플릿 페이지 제목 기반으로 검색.
        """
        try:
            result = self.search_pages(f"title:{template_name}", top_k=1)
            if result.success and result.data:
                return ConnectorResult(success=True, data=result.data[0].content)
            return ConnectorResult(success=False, error=f"Template '{template_name}' not found")
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    def create_page(
        self, space_key: str, title: str, content: str, parent_id: Optional[str] = None
    ) -> ConnectorResult:
        """페이지 생성 — HITL 승인 후에만 호출"""
        try:
            payload = {
                "type": "page",
                "title": title,
                "space": {"key": space_key},
                "body": {"storage": {"value": content, "representation": "storage"}},
            }
            if parent_id:
                payload["ancestors"] = [{"id": parent_id}]
            data = self._post("/content", json=payload)
            return ConnectorResult(
                success=True,
                data={"page_id": data["id"], "url": f"{self.base_url}{data['_links']['webui']}"},
            )
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))
```

---

### 4.3 JSM 커넥터

```python
# src/connectors/jsm_client.py
from __future__ import annotations
from typing import Optional
import httpx, os
from .base import BaseJSMConnector, ConnectorResult, CRRecord


class JSMConnector(BaseJSMConnector):
    """JSM (Jira Service Management) REST API 커넥터"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        project_key: Optional[str] = None,
        timeout: int = 30,
    ):
        self.base_url = (base_url or os.getenv("JSM_URL", "")).rstrip("/")
        self.token = token or os.getenv("JSM_TOKEN", "")
        self.project_key = project_key or os.getenv("JSM_PROJECT_KEY", "")
        self.timeout = timeout
        self._headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

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
        """
        CR 정보 기반 JSM 등록 입력값 초안 생성.
        실제 등록은 담당자가 검토 후 직접 수행 (HITL).
        """
        try:
            draft = {
                "project": {"key": self.project_key},
                "summary": f"[{cr_record.cr_type.upper()}] {cr_record.title}",
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [{
                        "type": "paragraph",
                        "content": [{"type": "text", "text": cr_record.description}]
                    }]
                },
                "issuetype": {"name": self._map_cr_type_to_issue(cr_record.cr_type)},
                "labels": cr_record.tags,
                "customfield_affected_systems": cr_record.affected_systems,
                "_meta": {
                    "note": "Agent가 생성한 초안입니다. 담당자 검토 후 등록하세요.",
                    "cr_id": cr_record.cr_id,
                }
            }
            return ConnectorResult(success=True, data=draft)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    @staticmethod
    def _map_cr_type_to_issue(cr_type: str) -> str:
        return {
            "new_dev": "새 기능",
            "feature_change": "개선",
            "db_change": "변경",
        }.get(cr_type, "작업")
```

---

### 4.4 두드림 커넥터

```python
# src/connectors/doodream_client.py
from __future__ import annotations
from typing import Optional
import httpx, os
from .base import BaseDoodreamConnector, ConnectorResult, CRRecord


class DoodreamConnector(BaseDoodreamConnector):
    """두드림 (삼성중공업 요청관리 시스템) REST API 커넥터"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        timeout: int = 30,
    ):
        self.base_url = (base_url or os.getenv("DOODREAM_URL", "")).rstrip("/")
        self.token = token or os.getenv("DOODREAM_TOKEN", "")
        self.timeout = timeout
        self._headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def _get(self, path: str, params: dict = None) -> dict:
        url = f"{self.base_url}/api/v1{path}"
        with httpx.Client(timeout=self.timeout, verify=False) as client:
            resp = client.get(url, headers=self._headers, params=params or {})
            resp.raise_for_status()
            return resp.json()

    def health_check(self) -> ConnectorResult:
        try:
            data = self._get("/health")
            return ConnectorResult(success=True, data="connected", source=self.base_url)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    def _parse_cr(self, item: dict) -> CRRecord:
        return CRRecord(
            cr_id=item.get("cr_id", ""),
            title=item.get("title", ""),
            description=item.get("description", ""),
            cr_type=item.get("cr_type", "new_dev"),
            status=item.get("status", ""),
            requester=item.get("requester", ""),
            assignee=item.get("assignee", ""),
            created_at=item.get("created_at", ""),
            closed_at=item.get("closed_at"),
            actual_hours=item.get("actual_hours"),
            estimated_hours=item.get("estimated_hours"),
            affected_systems=item.get("affected_systems", []),
            tags=item.get("tags", []),
        )

    def get_cr(self, cr_id: str) -> ConnectorResult:
        try:
            data = self._get(f"/cr/{cr_id}")
            return ConnectorResult(success=True, data=self._parse_cr(data))
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    def search_cr_history(
        self, query: str, cr_type: Optional[str] = None, top_k: int = 10
    ) -> ConnectorResult:
        try:
            params = {"q": query, "limit": top_k}
            if cr_type:
                params["cr_type"] = cr_type
            data = self._get("/cr/search", params=params)
            records = [self._parse_cr(item) for item in data.get("results", [])]
            return ConnectorResult(success=True, data=records)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    def get_recent_crs(self, days: int = 90, status: Optional[str] = None) -> ConnectorResult:
        try:
            params = {"days": days}
            if status:
                params["status"] = status
            data = self._get("/cr/recent", params=params)
            records = [self._parse_cr(item) for item in data.get("results", [])]
            return ConnectorResult(success=True, data=records)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))
```

---

### 4.5 Oracle 19c 딕셔너리 커넥터

```python
# src/connectors/oracle_client.py
from __future__ import annotations
from typing import List, Optional
import os
from .base import BaseOracleConnector, ConnectorResult, OracleTableInfo

# cx_Oracle 또는 python-oracledb 사용 (사내 드라이버 설치 필요)
try:
    import oracledb as cx_Oracle          # python-oracledb (신규 권장)
    ORACLE_DRIVER = "oracledb"
except ImportError:
    try:
        import cx_Oracle                  # 구 cx_Oracle
        ORACLE_DRIVER = "cx_Oracle"
    except ImportError:
        cx_Oracle = None
        ORACLE_DRIVER = None


class Oracle19cConnector(BaseOracleConnector):
    """
    Oracle 19c 딕셔너리 Read-only 커넥터.
    ALL_DEPENDENCIES, USER_TABLES, ALL_TAB_COLUMNS 뷰 활용.
    """

    # ── 영향도 분석용 딕셔너리 쿼리 ──────────────────────────

    SQL_TABLE_INFO = """
        SELECT
            t.table_name,
            t.owner,
            t.num_rows,
            c.comments AS table_comments
        FROM all_tables t
        LEFT JOIN all_tab_comments c
            ON c.table_name = t.table_name AND c.owner = t.owner
        WHERE t.table_name = UPPER(:table_name)
          AND t.owner = UPPER(:owner)
    """

    SQL_COLUMNS = """
        SELECT
            col.column_name,
            col.data_type,
            col.data_length,
            col.nullable,
            col.data_default,
            com.comments
        FROM all_tab_columns col
        LEFT JOIN all_col_comments com
            ON com.table_name = col.table_name
           AND com.column_name = col.column_name
           AND com.owner = col.owner
        WHERE col.table_name = UPPER(:table_name)
          AND col.owner = UPPER(:owner)
        ORDER BY col.column_id
    """

    SQL_DEPENDENCIES = """
        SELECT DISTINCT
            d.name        AS object_name,
            d.type        AS object_type,
            d.owner       AS object_owner
        FROM all_dependencies d
        WHERE d.referenced_name = UPPER(:object_name)
          AND d.referenced_type = UPPER(:object_type)
          AND d.referenced_owner = UPPER(:owner)
        ORDER BY d.type, d.name
    """

    SQL_AFFECTED_PROGRAMS = """
        SELECT DISTINCT
            d.name AS program_name,
            d.type AS program_type,
            d.owner
        FROM all_dependencies d
        WHERE d.referenced_name = UPPER(:table_name)
          AND d.referenced_type = 'TABLE'
          AND d.type IN ('PROCEDURE', 'FUNCTION', 'PACKAGE', 'PACKAGE BODY', 'TRIGGER', 'VIEW')
        ORDER BY d.type, d.name
    """

    def __init__(
        self,
        dsn: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        default_owner: Optional[str] = None,
    ):
        if cx_Oracle is None:
            raise ImportError(
                "Oracle 드라이버가 설치되지 않았습니다. "
                "'pip install oracledb' 또는 'pip install cx_Oracle'을 실행하세요."
            )
        self.dsn = dsn or os.getenv("ORACLE_DSN", "")
        self.user = user or os.getenv("ORACLE_USER", "")
        self.password = password or os.getenv("ORACLE_PASSWORD", "")
        self.default_owner = default_owner or os.getenv("ORACLE_DEFAULT_OWNER", self.user.upper())
        self._conn = None

    def _get_connection(self):
        if self._conn is None:
            self._conn = cx_Oracle.connect(
                user=self.user,
                password=self.password,
                dsn=self.dsn,
            )
        return self._conn

    def _execute(self, sql: str, params: dict) -> list:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(sql, params)
        columns = [col[0].lower() for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def health_check(self) -> ConnectorResult:
        try:
            rows = self._execute("SELECT 1 FROM dual", {})
            return ConnectorResult(success=True, data="connected", source=self.dsn)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    def get_table_info(self, table_name: str, owner: Optional[str] = None) -> ConnectorResult:
        try:
            owner = (owner or self.default_owner).upper()
            # 테이블 기본 정보
            tbl_rows = self._execute(self.SQL_TABLE_INFO, {"table_name": table_name, "owner": owner})
            if not tbl_rows:
                return ConnectorResult(success=False, error=f"Table {owner}.{table_name} not found")
            tbl = tbl_rows[0]
            # 컬럼 정보
            col_rows = self._execute(self.SQL_COLUMNS, {"table_name": table_name, "owner": owner})
            table_info = OracleTableInfo(
                table_name=table_name.upper(),
                owner=owner,
                row_count=tbl.get("num_rows"),
                comments=tbl.get("table_comments"),
                columns=col_rows,
                dependencies=[],
            )
            return ConnectorResult(success=True, data=table_info)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    def get_dependencies(self, object_name: str, object_type: str = "TABLE") -> ConnectorResult:
        try:
            rows = self._execute(self.SQL_DEPENDENCIES, {
                "object_name": object_name,
                "object_type": object_type,
                "owner": self.default_owner,
            })
            return ConnectorResult(success=True, data=rows)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    def get_affected_programs(self, table_name: str) -> ConnectorResult:
        try:
            rows = self._execute(self.SQL_AFFECTED_PROGRAMS, {"table_name": table_name})
            programs = [r["program_name"] for r in rows]
            return ConnectorResult(success=True, data={"programs": programs, "detail": rows})
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    def check_consistency(self, table_names: List[str]) -> ConnectorResult:
        """Oracle 딕셔너리에 실존하는 테이블인지 확인 (테이블마스터 정합성 검증용)"""
        try:
            results = []
            for tname in table_names:
                rows = self._execute(
                    "SELECT COUNT(*) AS cnt FROM all_tables WHERE table_name = UPPER(:t) AND owner = UPPER(:o)",
                    {"t": tname, "o": self.default_owner},
                )
                exists = rows[0]["cnt"] > 0 if rows else False
                results.append({"table_name": tname, "exists_in_oracle": exists})
            return ConnectorResult(success=True, data=results)
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))
```

---

### 4.6 프로그램마스터·테이블마스터 커넥터

```python
# src/connectors/master_client.py
from __future__ import annotations
from typing import Any, Dict, Optional
import httpx, os
from .base import BaseMasterConnector, ConnectorResult, OracleTableInfo, ProgramMasterRecord


class MasterSystemConnector(BaseMasterConnector):
    """
    프로그램마스터·테이블마스터 자체 개발 관리 시스템 커넥터.
    두 시스템이 동일 베이스 URL에서 경로로 분기되는 구조 가정.
    (실제 API 스펙에 따라 경로 조정 필요)
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        timeout: int = 30,
    ):
        self.base_url = (base_url or os.getenv("MASTER_SYSTEM_URL", "")).rstrip("/")
        self.token = token or os.getenv("MASTER_SYSTEM_TOKEN", "")
        self.timeout = timeout
        self._headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

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
                program_id=data.get("program_id", ""),
                program_name=data.get("program_name", ""),
                system_code=data.get("system_code", ""),
                menu_path=data.get("menu_path", ""),
                dev_language=data.get("dev_language", ""),
                status=data.get("status", ""),
                created_at=data.get("created_at", ""),
                related_tables=data.get("related_tables", []),
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
        """
        CR 컨텍스트 기반 프로그램마스터 등록 입력값 초안.
        실제 등록은 담당자가 검토 후 직접 수행 (HITL).
        """
        draft = {
            "program_id": context.get("program_id", ""),
            "program_name": context.get("program_name", ""),
            "system_code": context.get("system_code", ""),
            "menu_path": context.get("menu_path", ""),
            "dev_language": context.get("dev_language", "Java"),
            "description": context.get("description", ""),
            "related_tables": context.get("affected_tables", []),
            "_meta": {
                "note": "Agent가 생성한 초안입니다. 담당자 검토 후 등록하세요.",
                "cr_id": context.get("cr_id", ""),
            }
        }
        return ConnectorResult(success=True, data=draft)

    def build_table_master_draft(self, table_info: OracleTableInfo) -> ConnectorResult:
        """Oracle 딕셔너리 정보 기반 테이블마스터 등록 입력값 초안"""
        draft = {
            "table_name": table_info.table_name,
            "owner": table_info.owner,
            "description": table_info.comments or "",
            "columns": [
                {
                    "column_name": col.get("column_name", ""),
                    "data_type": col.get("data_type", ""),
                    "nullable": col.get("nullable", "Y"),
                    "description": col.get("comments", ""),
                }
                for col in table_info.columns
            ],
            "_meta": {
                "note": "Oracle 딕셔너리 기반 자동 생성 초안입니다. 담당자 검토 후 등록하세요.",
                "row_count": table_info.row_count,
            }
        }
        return ConnectorResult(success=True, data=draft)
```

---

### 4.7 용어사전·단어사전 커넥터

```python
# src/connectors/dictionary_client.py
from __future__ import annotations
from typing import List, Optional
import httpx, os, re
from .base import BaseDictionaryConnector, ConnectorResult, TermRecord


class DictionaryConnector(BaseDictionaryConnector):
    """용어사전·단어사전 자체 개발 관리 시스템 커넥터"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        timeout: int = 30,
    ):
        self.base_url = (base_url or os.getenv("DICTIONARY_URL", "")).rstrip("/")
        self.token = token or os.getenv("DICTIONARY_TOKEN", "")
        self.timeout = timeout
        self._headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

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

    def check_term_registered(self, term: str) -> ConnectorResult:
        try:
            data = self._get(f"/terms/search", params={"q": term, "exact": True})
            results = data.get("results", [])
            if results:
                t = results[0]
                record = TermRecord(
                    term_id=t.get("term_id", ""),
                    term_ko=t.get("term_ko", ""),
                    term_en=t.get("term_en", ""),
                    abbreviation=t.get("abbreviation", ""),
                    definition=t.get("definition", ""),
                    domain=t.get("domain", ""),
                    status=t.get("status", "approved"),
                )
                return ConnectorResult(success=True, data={"registered": True, "record": record})
            return ConnectorResult(success=True, data={"registered": False, "record": None})
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    def detect_unregistered_terms(self, text: str) -> ConnectorResult:
        """
        텍스트 내 한글 명사 추출 후 사전 미등록 여부 확인.
        간단한 구현: 2글자 이상 한글 단어 추출 후 배치 조회.
        """
        try:
            # 2글자 이상 한글 단어 추출 (형태소 분석기 없이 단순 패턴)
            korean_words = list(set(re.findall(r'[가-힣]{2,}', text)))
            unregistered = []
            for word in korean_words:
                result = self.check_term_registered(word)
                if result.success and not result.data.get("registered"):
                    unregistered.append(word)
            return ConnectorResult(
                success=True,
                data={"unregistered_terms": unregistered, "total_checked": len(korean_words)},
            )
        except Exception as e:
            return ConnectorResult(success=False, error=str(e))

    def build_term_draft(self, term_ko: str, context: str) -> ConnectorResult:
        """신규 용어 등록 입력값 초안 (담당자 검토 후 등록)"""
        draft = {
            "term_ko": term_ko,
            "term_en": "",           # 담당자 입력 필요
            "abbreviation": "",      # 담당자 입력 필요
            "definition": f"'{term_ko}'에 대한 정의를 입력하세요.",
            "domain": "",            # 담당자 선택 필요
            "context_sample": context[:200],
            "_meta": {
                "note": "Agent가 생성한 초안입니다. 담당자 검토 후 등록하세요.",
            }
        }
        return ConnectorResult(success=True, data=draft)
```

---

## 5. Mock 커넥터 구현 (T3 선행 개발용)

Mock 커넥터는 실 시스템 없이 T3 Skill 개발을 선행할 수 있도록 **고정된 현실적 데이터**를 반환한다.  
`ConnectorFactory`가 환경변수 `USE_MOCK_CONNECTORS=true` 일 때 자동으로 Mock을 주입한다.

```python
# src/connectors/mock/github_mock.py
from __future__ import annotations
from ..base import BaseGitHubConnector, ConnectorResult, CodeFile
from typing import Optional


class GitHubMockConnector(BaseGitHubConnector):
    """GitHub Enterprise Mock — T3 Skill 선행 개발용"""
    is_mock = True

    _CODE_SAMPLES = [
        CodeFile(
            path="src/program/ProgramMasterService.java",
            content="""
public class ProgramMasterService {
    public ProgramMaster findByProgramId(String programId) {
        return programMasterRepository.findById(programId)
            .orElseThrow(() -> new ProgramNotFoundException(programId));
    }
    public void registerProgram(ProgramMasterDto dto) {
        // 프로그램마스터 등록 로직
        programMasterRepository.save(dto.toEntity());
    }
}""",
            repo="org/shic-app",
            branch="main",
            sha="abc123def",
            url="https://github.internal/org/shic-app/blob/main/src/program/ProgramMasterService.java",
            language="Java",
        ),
        CodeFile(
            path="src/table/TableMasterMapper.xml",
            content="""
<select id="selectTableList" parameterType="String">
    SELECT TABLE_ID, TABLE_NAME, TABLE_DESC
    FROM TBL_TABLE_MASTER
    WHERE SYSTEM_CODE = #{systemCode}
    AND USE_YN = 'Y'
</select>""",
            repo="org/shic-app",
            branch="main",
            sha="def456ghi",
            url="https://github.internal/org/shic-app/blob/main/src/table/TableMasterMapper.xml",
            language="XML",
        ),
    ]

    def health_check(self) -> ConnectorResult:
        return ConnectorResult(success=True, data="mock-connected")

    def search_code(self, query: str, repo: Optional[str] = None, top_k: int = 5) -> ConnectorResult:
        return ConnectorResult(success=True, data=self._CODE_SAMPLES[:top_k], source="mock")

    def get_file(self, repo: str, path: str, ref: str = "main") -> ConnectorResult:
        for f in self._CODE_SAMPLES:
            if f.path == path:
                return ConnectorResult(success=True, data=f)
        return ConnectorResult(success=False, error=f"Mock: file '{path}' not found")

    def list_repos(self, org: str) -> ConnectorResult:
        return ConnectorResult(success=True, data=["org/shic-app", "org/shic-batch", "org/shic-common"])

    def create_pr_draft(self, repo: str, title: str, body: str, head: str, base: str = "main") -> ConnectorResult:
        return ConnectorResult(
            success=True,
            data={"pr_number": 999, "pr_url": f"https://github.internal/{repo}/pull/999"},
            source="mock",
        )
```

```python
# src/connectors/mock/doodream_mock.py
from __future__ import annotations
from ..base import BaseDoodreamConnector, ConnectorResult, CRRecord
from typing import Optional


class DoodreamMockConnector(BaseDoodreamConnector):
    """두드림 Mock — 실제 CR 데이터 유사 샘플"""
    is_mock = True

    _CR_SAMPLES = [
        CRRecord(
            cr_id="CR-2026-0312",
            title="선박 수주 현황 조회 화면 신규 개발",
            description="영업팀 요청으로 선박 수주 현황을 조회하는 화면 개발 필요. "
                        "수주번호, 선박명, 발주처, 납기일 등 기본 정보 표시.",
            cr_type="new_dev",
            status="closed",
            requester="홍길동",
            assignee="김담당",
            created_at="2026-03-10T09:00:00",
            closed_at="2026-03-25T18:00:00",
            actual_hours=24.0,
            estimated_hours=20.0,
            affected_systems=["SHIP_ORDER", "PROGRAM_MASTER"],
            tags=["신규화면", "조회", "영업"],
        ),
        CRRecord(
            cr_id="CR-2026-0287",
            title="자재 입출고 테이블 스키마 변경",
            description="자재관리 개선으로 MATERIAL_INOUT 테이블에 LOT_NO 컬럼 추가 필요.",
            cr_type="db_change",
            status="closed",
            requester="이자재",
            assignee="박담당",
            created_at="2026-02-20T10:30:00",
            closed_at="2026-03-05T17:00:00",
            actual_hours=16.0,
            estimated_hours=12.0,
            affected_systems=["MATERIAL_INOUT", "TABLE_MASTER"],
            tags=["DB변경", "자재관리"],
        ),
        CRRecord(
            cr_id="CR-2026-0198",
            title="공정 진행률 화면 기능 변경",
            description="기존 공정 진행률 조회 화면에 부서별 필터 기능 추가.",
            cr_type="feature_change",
            status="closed",
            requester="최공정",
            assignee="김담당",
            created_at="2026-01-15T11:00:00",
            closed_at="2026-01-28T16:00:00",
            actual_hours=12.0,
            estimated_hours=10.0,
            affected_systems=["PROCESS_STATUS"],
            tags=["기능변경", "공정관리"],
        ),
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
```

```python
# src/connectors/mock/oracle_mock.py
from __future__ import annotations
from typing import List, Optional
from ..base import BaseOracleConnector, ConnectorResult, OracleTableInfo


class OracleMockConnector(BaseOracleConnector):
    """Oracle 19c 딕셔너리 Mock"""
    is_mock = True

    _TABLE_SAMPLES = {
        "SHIP_ORDER": OracleTableInfo(
            table_name="SHIP_ORDER",
            owner="SHIC",
            row_count=15420,
            comments="선박 수주 마스터 테이블",
            columns=[
                {"column_name": "ORDER_NO", "data_type": "VARCHAR2", "nullable": "N", "comments": "수주번호"},
                {"column_name": "SHIP_NAME", "data_type": "VARCHAR2", "nullable": "Y", "comments": "선박명"},
                {"column_name": "CLIENT_NM", "data_type": "VARCHAR2", "nullable": "Y", "comments": "발주처명"},
                {"column_name": "DELIVERY_DT", "data_type": "DATE", "nullable": "Y", "comments": "납기일"},
            ],
            dependencies=["PKG_SHIP_ORDER", "V_SHIP_STATUS", "TRG_SHIP_ORDER_AI"],
        ),
        "MATERIAL_INOUT": OracleTableInfo(
            table_name="MATERIAL_INOUT",
            owner="SHIC",
            row_count=203450,
            comments="자재 입출고 이력 테이블",
            columns=[
                {"column_name": "INOUT_SEQ", "data_type": "NUMBER", "nullable": "N", "comments": "입출고일련번호"},
                {"column_name": "MATERIAL_CD", "data_type": "VARCHAR2", "nullable": "N", "comments": "자재코드"},
                {"column_name": "INOUT_QTY", "data_type": "NUMBER", "nullable": "Y", "comments": "입출고수량"},
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
        results = [
            {"table_name": t, "exists_in_oracle": t.upper() in self._TABLE_SAMPLES}
            for t in table_names
        ]
        return ConnectorResult(success=True, data=results)
```

> **나머지 Mock (Confluence, JSM, Master, Dictionary)**  
> 위 패턴과 동일하게 `src/connectors/mock/` 디렉토리에 구현.  
> 각각 3~5건의 현실적 샘플 데이터 포함.

---

## 6. ConnectorFactory 구현

Skill 코드가 환경(실/Mock)에 무관하게 동일하게 동작하도록 팩토리 패턴을 적용한다.

```python
# src/connectors/factory.py
from __future__ import annotations
import os
from .base import (
    BaseGitHubConnector, BaseConfluenceConnector, BaseJSMConnector,
    BaseDoodreamConnector, BaseOracleConnector, BaseMasterConnector,
    BaseDictionaryConnector,
)


def _use_mock() -> bool:
    """환경변수 USE_MOCK_CONNECTORS=true 이면 Mock 사용"""
    return os.getenv("USE_MOCK_CONNECTORS", "false").lower() == "true"


class ConnectorFactory:
    """
    환경변수 기반으로 실 커넥터 또는 Mock 커넥터를 반환.

    사용 예:
        github = ConnectorFactory.github()
        result = github.search_code("프로그램마스터 등록")
    """

    @staticmethod
    def github() -> BaseGitHubConnector:
        if _use_mock():
            from .mock.github_mock import GitHubMockConnector
            return GitHubMockConnector()
        from .github_client import GitHubEnterpriseConnector
        return GitHubEnterpriseConnector()

    @staticmethod
    def confluence() -> BaseConfluenceConnector:
        if _use_mock():
            from .mock.confluence_mock import ConfluenceMockConnector
            return ConfluenceMockConnector()
        from .confluence_client import ConfluenceConnector
        return ConfluenceConnector()

    @staticmethod
    def jsm() -> BaseJSMConnector:
        if _use_mock():
            from .mock.jsm_mock import JSMMockConnector
            return JSMMockConnector()
        from .jsm_client import JSMConnector
        return JSMConnector()

    @staticmethod
    def doodream() -> BaseDoodreamConnector:
        if _use_mock():
            from .mock.doodream_mock import DoodreamMockConnector
            return DoodreamMockConnector()
        from .doodream_client import DoodreamConnector
        return DoodreamConnector()

    @staticmethod
    def oracle() -> BaseOracleConnector:
        if _use_mock():
            from .mock.oracle_mock import OracleMockConnector
            return OracleMockConnector()
        from .oracle_client import Oracle19cConnector
        return Oracle19cConnector()

    @staticmethod
    def master() -> BaseMasterConnector:
        if _use_mock():
            from .mock.master_mock import MasterMockConnector
            return MasterMockConnector()
        from .master_client import MasterSystemConnector
        return MasterSystemConnector()

    @staticmethod
    def dictionary() -> BaseDictionaryConnector:
        if _use_mock():
            from .mock.dictionary_mock import DictionaryMockConnector
            return DictionaryMockConnector()
        from .dictionary_client import DictionaryConnector
        return DictionaryConnector()

    @staticmethod
    def all_health_check() -> dict:
        """모든 커넥터 연결 상태 일괄 확인"""
        results = {}
        connectors = {
            "github": ConnectorFactory.github,
            "confluence": ConnectorFactory.confluence,
            "jsm": ConnectorFactory.jsm,
            "doodream": ConnectorFactory.doodream,
            "oracle": ConnectorFactory.oracle,
            "master": ConnectorFactory.master,
            "dictionary": ConnectorFactory.dictionary,
        }
        for name, factory_fn in connectors.items():
            try:
                connector = factory_fn()
                result = connector.health_check()
                results[name] = {
                    "status": "ok" if result.success else "error",
                    "is_mock": connector.is_mock,
                    "error": result.error,
                }
            except Exception as e:
                results[name] = {"status": "exception", "error": str(e)}
        return results
```

---

## 7. 연동 테스트

### 7.1 Mock 기반 통합 테스트 (항상 실행 가능)

```python
# tests/connectors/test_factory.py
"""
Mock 기반 통합 테스트 — 사내 시스템 연결 없이 실행 가능.
T3 Skill 개발 전 커넥터 인터페이스 검증용.
"""
import os
import pytest

os.environ["USE_MOCK_CONNECTORS"] = "true"

from src.connectors.factory import ConnectorFactory


def test_all_health_checks():
    """전체 커넥터 health check (Mock)"""
    results = ConnectorFactory.all_health_check()
    for name, result in results.items():
        assert result["status"] == "ok", f"{name} health check failed: {result.get('error')}"
        assert result["is_mock"] is True
    print(f"✅ 전체 커넥터 health check 통과: {list(results.keys())}")


def test_github_search_code():
    github = ConnectorFactory.github()
    result = github.search_code("프로그램마스터 등록", top_k=2)
    assert result.success
    assert len(result.data) > 0
    assert result.data[0].path.endswith(".java") or result.data[0].path.endswith(".xml")
    print(f"✅ GitHub 코드 검색: {result.data[0].path}")


def test_doodream_search_history():
    doodream = ConnectorFactory.doodream()
    result = doodream.search_cr_history("신규 화면 개발", cr_type="new_dev", top_k=5)
    assert result.success
    assert len(result.data) > 0
    cr = result.data[0]
    assert cr.cr_type == "new_dev"
    assert cr.actual_hours is not None
    print(f"✅ 두드림 CR 검색: {cr.cr_id} - {cr.title}")


def test_oracle_table_info():
    oracle = ConnectorFactory.oracle()
    result = oracle.get_table_info("SHIP_ORDER")
    assert result.success
    tbl = result.data
    assert tbl.table_name == "SHIP_ORDER"
    assert len(tbl.columns) > 0
    print(f"✅ Oracle 테이블 조회: {tbl.table_name} ({len(tbl.columns)}개 컬럼)")


def test_oracle_affected_programs():
    oracle = ConnectorFactory.oracle()
    result = oracle.get_affected_programs("SHIP_ORDER")
    assert result.success
    programs = result.data["programs"]
    assert isinstance(programs, list)
    print(f"✅ Oracle 영향 프로그램: {programs}")


def test_master_build_program_draft():
    master = ConnectorFactory.master()
    result = master.build_program_master_draft({
        "program_id": "SHI_SHIP_ORDER_01",
        "program_name": "선박 수주 현황 조회",
        "system_code": "SHIP",
        "menu_path": "영업관리 > 수주관리",
        "cr_id": "CR-2026-0001",
        "affected_tables": ["SHIP_ORDER"],
    })
    assert result.success
    draft = result.data
    assert draft["program_id"] == "SHI_SHIP_ORDER_01"
    assert "_meta" in draft
    print(f"✅ 프로그램마스터 초안: {draft['program_name']}")


def test_dictionary_detect_unregistered():
    dictionary = ConnectorFactory.dictionary()
    result = dictionary.detect_unregistered_terms(
        "선박 수주 현황 조회 화면에서 납기일과 발주처명을 표시합니다."
    )
    assert result.success
    print(f"✅ 미등록 용어 감지: {result.data['unregistered_terms']}")


def test_jsm_build_issue_draft():
    from src.connectors.base import CRRecord
    jsm = ConnectorFactory.jsm()
    cr = CRRecord(
        cr_id="CR-2026-0001",
        title="선박 수주 현황 조회 화면 신규 개발",
        description="영업팀 요청 화면",
        cr_type="new_dev",
        status="open",
        requester="홍길동",
        assignee="김담당",
        created_at="2026-06-01",
        closed_at=None,
        actual_hours=None,
        estimated_hours=20.0,
        affected_systems=["SHIP_ORDER"],
        tags=["신규화면"],
    )
    result = jsm.build_issue_draft(cr)
    assert result.success
    draft = result.data
    assert "summary" in draft
    assert "_meta" in draft
    print(f"✅ JSM 초안: {draft['summary']}")
```

### 7.2 실 시스템 연동 테스트 (시스템별 선택 실행)

```bash
# 실 커넥터 테스트 (환경변수 설정 후 실행)
export USE_MOCK_CONNECTORS=false

# GitHub Enterprise 연동 테스트
pytest tests/connectors/test_github_real.py -v -k "health"

# Confluence 연동 테스트
pytest tests/connectors/test_confluence_real.py -v -k "health"

# Oracle 연동 테스트 (Read-only 계정 필요)
pytest tests/connectors/test_oracle_real.py -v -k "health or table_info"
```

```python
# tests/connectors/test_github_real.py
"""GitHub Enterprise 실 연동 테스트 — USE_MOCK_CONNECTORS=false 필요"""
import os, pytest

@pytest.mark.skipif(os.getenv("USE_MOCK_CONNECTORS","true")=="true", reason="Mock 모드")
def test_github_real_health():
    from src.connectors.github_client import GitHubEnterpriseConnector
    gh = GitHubEnterpriseConnector()
    result = gh.health_check()
    assert result.success, f"GitHub 연결 실패: {result.error}"
    print(f"✅ GitHub Enterprise 연결 성공: {result.data}")
```

---

## 8. .env 추가 항목

T1-1 `.env`에 아래 항목을 추가한다.

```dotenv
# ── GitHub Enterprise ─────────────────────────
GITHUB_ENTERPRISE_URL=https://<사내-github-url>
GITHUB_TOKEN=<github-pat>
GITHUB_ORG=<조직명>

# ── Confluence ────────────────────────────────
CONFLUENCE_URL=https://<confluence-url>
CONFLUENCE_TOKEN=<api-token>
CONFLUENCE_DEFAULT_SPACE=<기본-스페이스-키>

# ── JSM ──────────────────────────────────────
JSM_URL=https://<jsm-url>
JSM_TOKEN=<api-token>
JSM_PROJECT_KEY=<프로젝트-키>

# ── 두드림 ───────────────────────────────────
DOODREAM_URL=https://<두드림-url>
DOODREAM_TOKEN=<api-token>

# ── Oracle 19c (Read-only) ───────────────────
ORACLE_DSN=<host>:<port>/<service_name>
ORACLE_USER=<readonly-user>
ORACLE_PASSWORD=<password>
ORACLE_DEFAULT_OWNER=<스키마-오너>

# ── 자체 관리 시스템 ──────────────────────────
MASTER_SYSTEM_URL=https://<master-system-url>
MASTER_SYSTEM_TOKEN=<api-token>
DICTIONARY_URL=https://<dictionary-url>
DICTIONARY_TOKEN=<api-token>

# ── 개발 모드 설정 ────────────────────────────
USE_MOCK_CONNECTORS=true    # T3 Skill 개발 중에는 true, 실 연동 테스트 시 false
```

---

## 9. 트러블슈팅

| 증상 | 원인 | 조치 |
|------|------|------|
| GitHub API 403 Forbidden | PAT 권한 부족 또는 만료 | GitHub Enterprise → Settings → Personal Access Tokens에서 `repo`, `read:org` 권한 재발급 |
| Confluence API 401 | API Token 만료 | Confluence → 사용자 설정 → API Token 재발급, `.env` 업데이트 |
| JSM API 404 | 프로젝트 키 오류 | `JSM_PROJECT_KEY` 값 JSM 포털에서 확인 후 수정 |
| 두드림 API 경로 오류 | 두드림 API 스펙 미확인 | 두드림 담당팀에 API 명세 요청. 경로 미확인 시 DB 직접 조회(Read-only) 방식으로 전환 |
| Oracle `ORA-01017` | 계정 또는 비밀번호 오류 | DBA팀에 Read-only 계정 재발급 요청 |
| Oracle `cx_Oracle` ImportError | Oracle Instant Client 미설치 | Oracle Instant Client 설치 후 `LD_LIBRARY_PATH` 설정. 또는 `pip install oracledb` (Thin 모드, 클라이언트 불필요) 사용 |
| 자체 시스템 API 스펙 불명확 | 내부 개발팀 API 문서 미정비 | 담당팀에 Swagger/OpenAPI 문서 요청. 미제공 시 DB 직접 조회 방식으로 구현 후 API 준비 시 교체 |
| SSL 인증서 오류 | 사내 자체 서명 인증서 | `verify=False` 임시 적용 후 보안팀에 사내 CA 인증서 파일 요청 → `verify="path/to/ca.crt"` 교체 |
| Mock 데이터 부족 | 실제 도메인 데이터와 다름 | `src/connectors/mock/` 파일에 실제 업무 데이터 기반 샘플 추가 |

---

## 10. Task 완료 체크리스트

```
T1-2 완료 기준

[ ] BaseConnector ABC 및 7개 하위 추상 클래스 정의 완료
[ ] 공통 데이터 모델 (CodeFile, ConfluencePage, CRRecord, OracleTableInfo 등) 확정

[ ] 실 커넥터 8개 구현 완료
    [ ] GitHubEnterpriseConnector
    [ ] ConfluenceConnector
    [ ] JSMConnector
    [ ] DoodreamConnector
    [ ] Oracle19cConnector
    [ ] MasterSystemConnector
    [ ] DictionaryConnector

[ ] Mock 커넥터 7개 구현 완료 (현실적 샘플 데이터 포함)
    [ ] GitHubMockConnector
    [ ] ConfluenceMockConnector
    [ ] JSMMockConnector
    [ ] DoodreamMockConnector
    [ ] OracleMockConnector
    [ ] MasterMockConnector
    [ ] DictionaryMockConnector

[ ] ConnectorFactory 구현 및 USE_MOCK_CONNECTORS 전환 동작 확인

[ ] Mock 기반 통합 테스트 전원 통과 (pytest tests/connectors/test_factory.py -v)
[ ] 실 연동 가능 시스템 최소 3개 health_check 통과

[ ] .env 추가 항목 입력 완료
[ ] src/connectors/ GitHub Enterprise push 완료

→ 전원 체크 완료 시 T1-3 (전체 아키텍처 설계)으로 진행
→ T3 Skill 개발 시 USE_MOCK_CONNECTORS=true 설정 후 ConnectorFactory 활용
```

---

*작성일: 2026-06 | 버전: v1.0 | 담당: 중공업IT파트*  
*참고 문서: [T1-1_환경셋업_가이드.md](./T1-1_환경셋업_가이드.md) | [TASK_LIST.md](../TASK_LIST.md)*