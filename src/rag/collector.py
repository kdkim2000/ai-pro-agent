# src/rag/collector.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from src.connectors.factory import ConnectorFactory
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RawDocument:
    """3-소스 수집 원시 문서 (전처리 전)"""
    source: str
    doc_type: str
    doc_id: str
    title: str
    content: str
    url: str
    date: str
    language: Optional[str] = None
    extra: dict = field(default_factory=dict)


class DataCollector:
    """GitHub · Confluence · 두드림 원시 데이터 수집"""

    def __init__(self) -> None:
        self._github = ConnectorFactory.github()
        self._confluence = ConnectorFactory.confluence()
        self._doodream = ConnectorFactory.doodream()

    # ── GitHub ───────────────────────────────────────────────────────

    def collect_github_code(self, query: str, top_k: int = 20) -> List[RawDocument]:
        """GitHub Enterprise 코드 검색 + RawDocument 변환"""
        result = self._github.search_code(query, top_k=top_k)
        if not result.success:
            logger.warning("github_collect_failed", error=result.error)
            return []

        docs = []
        for code_file in (result.data or []):
            docs.append(RawDocument(
                source="github",
                doc_type="code",
                doc_id=f"{code_file.repo}/{code_file.path}",
                title=code_file.path,
                content=code_file.content,
                url=code_file.url,
                date="",
                language=code_file.language,
                extra={
                    "repo": code_file.repo,
                    "branch": code_file.branch,
                    "sha": code_file.sha,
                },
            ))

        logger.info("github_collected", count=len(docs), query=query)
        return docs

    # ── Confluence ───────────────────────────────────────────────────

    def collect_confluence_docs(
        self, query: str, space_key: Optional[str] = None, top_k: int = 20
    ) -> List[RawDocument]:
        """Confluence 페이지 검색 + RawDocument 변환"""
        result = self._confluence.search_pages(query, space_key=space_key, top_k=top_k)
        if not result.success:
            logger.warning("confluence_collect_failed", error=result.error)
            return []

        docs = []
        for page in (result.data or []):
            docs.append(RawDocument(
                source="confluence",
                doc_type="document",
                doc_id=page.page_id,
                title=page.title,
                content=page.content,
                url=page.url,
                date=page.last_modified,
                language="ko",
                extra={"space_key": page.space_key, "labels": page.labels},
            ))

        logger.info("confluence_collected", count=len(docs), query=query)
        return docs

    # ── 두드림 ───────────────────────────────────────────────────────

    def collect_cr_history(
        self,
        query: str = "",
        cr_type: Optional[str] = None,
        top_k: int = 50,
        since_days: Optional[int] = None,
        status: Optional[str] = None,
    ) -> List[RawDocument]:
        """두드림 CR 이력 검색 + 자연어 텍스트 통합 + RawDocument 변환.

        두드림이 실제로 관리하는 필드만 직렬화한다(=신뢰 가능):
        cr_id · title · description · cr_type · status · requester · assignee · created_at.
        affected_systems · tags · actual_hours · estimated_hours 는 두드림 미관리 항목이므로
        RAG 본문/메타데이터에 포함하지 않는다. (영향 시스템 → Oracle 영향분석에서,
        실적/예상 공수 → T3-5 별도 실적 소스에서 보강한다.)

        Args:
            query: 검색어 (빈 문자열이면 전체).
            cr_type: new_dev | feature_change | db_change 필터.
            top_k: 검색 결과 상한.
            since_days: 지정 시 최근 N일만 수집(증분 동기화 경로 — get_recent_crs 사용).
            status: 상태 필터(예: "closed"). 증분/품질 필터에 사용.
        """
        if since_days is not None:
            # 증분 경로: 최근 N일 내 (선택적으로 특정 상태) CR만 폴링
            result = self._doodream.get_recent_crs(days=since_days, status=status)
        else:
            result = self._doodream.search_cr_history(query, cr_type=cr_type, top_k=top_k)
        if not result.success:
            logger.warning("doodream_collect_failed", error=result.error)
            return []

        docs = []
        for cr in (result.data or []):
            # 상태 필터(증분 외 경로에서도 품질 필터로 적용 가능)
            if status and cr.status != status:
                continue
            content = (
                f"CR ID: {cr.cr_id}\n"
                f"제목: {cr.title}\n"
                f"설명: {cr.description}\n"
                f"유형: {cr.cr_type}\n"
                f"상태: {cr.status}\n"
                f"요청자: {cr.requester}\n"
                f"담당자: {cr.assignee}"
            )
            docs.append(RawDocument(
                source="doodream",
                doc_type="cr_record",
                doc_id=cr.cr_id,
                title=cr.title,
                content=content,
                url=f"doodream://cr/{cr.cr_id}",
                date=cr.created_at,
                language="ko",
                extra={
                    "cr_type": cr.cr_type,
                    "status": cr.status,
                    "requester": cr.requester,
                    "assignee": cr.assignee,
                },
            ))

        logger.info("doodream_collected", count=len(docs), cr_type=cr_type, since_days=since_days)
        return docs

    # ── 전체 수집 ────────────────────────────────────────────────────

    def collect_all(self, query: str = "") -> Dict[str, List[RawDocument]]:
        """3-소스 일괄 수집. 소스별 독립 실행 — 일부 실패해도 계속 진행."""
        github_docs = self.collect_github_code(query)
        confluence_docs = self.collect_confluence_docs(query)
        cr_docs = self.collect_cr_history(query)

        total = len(github_docs) + len(confluence_docs) + len(cr_docs)
        logger.info(
            "collect_all_complete",
            github=len(github_docs),
            confluence=len(confluence_docs),
            doodream=len(cr_docs),
            total=total,
        )
        return {
            "github": github_docs,
            "confluence": confluence_docs,
            "doodream": cr_docs,
        }
