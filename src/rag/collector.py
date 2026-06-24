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
    ) -> List[RawDocument]:
        """두드림 CR 이력 검색 + 자연어 텍스트 통합 + RawDocument 변환"""
        result = self._doodream.search_cr_history(query, cr_type=cr_type, top_k=top_k)
        if not result.success:
            logger.warning("doodream_collect_failed", error=result.error)
            return []

        docs = []
        for cr in (result.data or []):
            content = (
                f"CR ID: {cr.cr_id}\n"
                f"제목: {cr.title}\n"
                f"설명: {cr.description}\n"
                f"유형: {cr.cr_type}\n"
                f"상태: {cr.status}\n"
                f"요청자: {cr.requester}\n"
                f"담당자: {cr.assignee}\n"
                f"영향 시스템: {', '.join(cr.affected_systems)}\n"
                f"태그: {', '.join(cr.tags)}\n"
                f"실제 공수: {cr.actual_hours}h / 예상 공수: {cr.estimated_hours}h"
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
                    "actual_hours": cr.actual_hours,
                    "estimated_hours": cr.estimated_hours,
                    "affected_systems": cr.affected_systems,
                    "tags": cr.tags,
                },
            ))

        logger.info("doodream_collected", count=len(docs), cr_type=cr_type)
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
