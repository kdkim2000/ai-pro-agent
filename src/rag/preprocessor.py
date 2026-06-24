# src/rag/preprocessor.py
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import List, Optional

from .collector import RawDocument
from src.utils.logger import get_logger

logger = get_logger(__name__)

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg",
    ".pdf", ".zip", ".tar", ".gz", ".jar", ".class",
    ".exe", ".dll", ".so", ".pyc", ".pyo", ".bin",
}


@dataclass
class CleanDocument:
    """전처리 완료 문서"""
    source: str
    doc_type: str
    doc_id: str
    title: str
    content: str
    url: str
    date: str
    language: str
    char_count: int = 0
    extra: dict = field(default_factory=dict)


class Preprocessor:
    """소스 유형별 노이즈 제거 + 메타데이터 정규화"""

    MIN_CONTENT_LENGTH = 50

    def process(self, doc: RawDocument) -> Optional[CleanDocument]:
        """단일 문서 전처리. 필터 대상이면 None 반환."""
        if doc.doc_type == "code":
            return self._process_code(doc)
        elif doc.doc_type == "document":
            return self._process_document(doc)
        elif doc.doc_type == "cr_record":
            return self._process_cr(doc)
        return None

    def process_all(self, docs: List[RawDocument]) -> List[CleanDocument]:
        """문서 목록 전처리. 필터링된 문서는 결과에서 제외."""
        clean_docs = []
        skip_count = 0
        for doc in docs:
            result = self.process(doc)
            if result:
                clean_docs.append(result)
            else:
                skip_count += 1
        logger.info(
            "preprocess_complete",
            input=len(docs),
            output=len(clean_docs),
            skipped=skip_count,
        )
        return clean_docs

    # ── 소스별 전처리 ────────────────────────────────────────────────

    def _process_code(self, doc: RawDocument) -> Optional[CleanDocument]:
        # 바이너리 확장자 필터
        if "." in doc.doc_id:
            ext = "." + doc.doc_id.rsplit(".", 1)[-1].lower()
            if ext in BINARY_EXTENSIONS:
                return None

        content = doc.content or ""
        if not content.strip():
            return None

        # shebang, 인코딩 선언 제거 (파이썬)
        if doc.language == "python" or doc.doc_id.endswith(".py"):
            content = self._remove_shebangs(content)

        content = re.sub(r'\n{3,}', '\n\n', content).strip()

        if len(content) < self.MIN_CONTENT_LENGTH:
            return None

        return CleanDocument(
            source=doc.source,
            doc_type=doc.doc_type,
            doc_id=doc.doc_id,
            title=doc.title,
            content=content,
            url=doc.url,
            date=self._normalize_date(doc.date),
            language=doc.language or "unknown",
            char_count=len(content),
            extra=doc.extra or {},
        )

    def _process_document(self, doc: RawDocument) -> Optional[CleanDocument]:
        content = doc.content or ""

        # HTML 태그 제거
        content = re.sub(r'<[^>]+>', ' ', content)
        # HTML 엔티티 변환
        content = (
            content
            .replace('&nbsp;', ' ')
            .replace('&lt;', '<')
            .replace('&gt;', '>')
            .replace('&amp;', '&')
            .replace('&quot;', '"')
            .replace('&#39;', "'")
        )
        content = re.sub(r'[ \t]{2,}', ' ', content)
        content = re.sub(r'\n{3,}', '\n\n', content).strip()

        if len(content) < self.MIN_CONTENT_LENGTH:
            return None

        return CleanDocument(
            source=doc.source,
            doc_type=doc.doc_type,
            doc_id=doc.doc_id,
            title=doc.title,
            content=content,
            url=doc.url,
            date=self._normalize_date(doc.date),
            language=doc.language or "ko",
            char_count=len(content),
            extra=doc.extra or {},
        )

    def _process_cr(self, doc: RawDocument) -> Optional[CleanDocument]:
        content = doc.content or ""
        content = re.sub(r'[ \t]{2,}', ' ', content).strip()

        if len(content) < self.MIN_CONTENT_LENGTH:
            return None

        return CleanDocument(
            source=doc.source,
            doc_type=doc.doc_type,
            doc_id=doc.doc_id,
            title=doc.title,
            content=content,
            url=doc.url,
            date=self._normalize_date(doc.date),
            language=doc.language or "ko",
            char_count=len(content),
            extra=doc.extra or {},
        )

    # ── 공통 헬퍼 ────────────────────────────────────────────────────

    @staticmethod
    def _remove_shebangs(code: str) -> str:
        lines = code.split('\n')
        while lines and (lines[0].startswith('#!') or '# -*-' in lines[0]):
            lines.pop(0)
        return '\n'.join(lines)

    @staticmethod
    def _normalize_date(date_str: str) -> str:
        """ISO 8601 형식이면 그대로, 아니면 빈 문자열 반환."""
        if not date_str:
            return ""
        if re.match(r'\d{4}-\d{2}-\d{2}', date_str):
            return date_str
        return ""
