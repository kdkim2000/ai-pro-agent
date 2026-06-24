# src/rag/chunker.py
from __future__ import annotations
import ast
import re
from dataclasses import dataclass, field
from typing import List

from langchain_core.documents import Document

from .preprocessor import CleanDocument
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TextChunk:
    """단일 청크 — text + metadata"""
    text: str
    metadata: dict = field(default_factory=dict)

    def to_langchain_doc(self) -> Document:
        return Document(page_content=self.text, metadata=self.metadata)


# ── 소스별 청커 ──────────────────────────────────────────────────────


class CodeChunker:
    """Python 코드 → AST 함수/클래스 단위 청킹"""

    def __init__(self, max_chars: int = 1500, overlap: int = 100) -> None:
        self.max_chars = max_chars
        self.overlap = overlap

    def chunk(self, doc: CleanDocument) -> List[TextChunk]:
        meta_base = _base_meta(doc)
        code = doc.content

        if doc.language == "python" or doc.doc_id.endswith(".py"):
            chunks = self._chunk_python(code, meta_base)
            if chunks:
                return chunks

        # fallback: 고정 크기 분할
        return self._chunk_by_size(code, meta_base)

    def _chunk_python(self, code: str, meta_base: dict) -> List[TextChunk]:
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return []

        lines = code.split('\n')
        chunks = []
        seen_ranges: set = set()

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if not hasattr(node, 'end_lineno'):
                continue

            start, end = node.lineno - 1, node.end_lineno
            key = (start, end)
            if key in seen_ranges:
                continue
            seen_ranges.add(key)

            snippet = '\n'.join(lines[start:end]).strip()
            if len(snippet) < 10:
                continue

            if len(snippet) > self.max_chars:
                for i, part in enumerate(_split_by_size(snippet, self.max_chars, self.overlap)):
                    chunks.append(TextChunk(
                        text=part,
                        metadata={**meta_base, "chunk_type": "code_block", "chunk_index": i},
                    ))
            else:
                chunks.append(TextChunk(
                    text=snippet,
                    metadata={
                        **meta_base,
                        "chunk_type": "code_block",
                        "symbol": getattr(node, 'name', ''),
                        "lineno": node.lineno,
                    },
                ))

        return chunks

    def _chunk_by_size(self, text: str, meta_base: dict) -> List[TextChunk]:
        return [
            TextChunk(
                text=part,
                metadata={**meta_base, "chunk_type": "fixed_size", "chunk_index": i},
            )
            for i, part in enumerate(_split_by_size(text, self.max_chars, self.overlap))
        ]


class DocumentChunker:
    """Confluence 문서 → 헤딩(# ~ ###) 기준 섹션 청킹"""

    def __init__(self, max_chars: int = 1000, overlap: int = 100) -> None:
        self.max_chars = max_chars
        self.overlap = overlap

    def chunk(self, doc: CleanDocument) -> List[TextChunk]:
        meta_base = _base_meta(doc)
        sections = self._split_by_heading(doc.content)

        chunks = []
        for i, section in enumerate(sections):
            section = section.strip()
            if not section:
                continue
            if len(section) <= self.max_chars:
                chunks.append(TextChunk(
                    text=section,
                    metadata={**meta_base, "chunk_type": "section", "section_index": i},
                ))
            else:
                for j, part in enumerate(_split_by_size(section, self.max_chars, self.overlap)):
                    chunks.append(TextChunk(
                        text=part,
                        metadata={
                            **meta_base,
                            "chunk_type": "section",
                            "section_index": i,
                            "part_index": j,
                        },
                    ))

        if not chunks:
            # 헤딩 없음: 크기 기반 분할
            chunks = [
                TextChunk(
                    text=part,
                    metadata={**meta_base, "chunk_type": "fixed_size", "chunk_index": i},
                )
                for i, part in enumerate(_split_by_size(doc.content, self.max_chars, self.overlap))
            ]

        return chunks

    @staticmethod
    def _split_by_heading(text: str) -> List[str]:
        """# ~ ### 헤딩을 구분자로 분할"""
        pattern = r'(?=^#{1,3} )'
        sections = re.split(pattern, text, flags=re.MULTILINE)
        return [s for s in sections if s.strip()]


class CRChunker:
    """CR 레코드 → 1건 1청크"""

    def chunk(self, doc: CleanDocument) -> List[TextChunk]:
        meta = _base_meta(doc)
        meta["chunk_type"] = "cr_record"
        if "cr_type" in doc.extra:
            meta["cr_type"] = doc.extra["cr_type"]
        if "actual_hours" in doc.extra:
            meta["actual_hours"] = doc.extra["actual_hours"]
        if "affected_systems" in doc.extra:
            meta["affected_systems"] = doc.extra["affected_systems"]
        return [TextChunk(text=doc.content, metadata=meta)]


class Chunker:
    """소스 유형별 청킹 전략 디스패처"""

    def __init__(
        self,
        chunk_size_code: int = 1500,
        chunk_size_doc: int = 1000,
        overlap: int = 100,
    ) -> None:
        self._code = CodeChunker(max_chars=chunk_size_code, overlap=overlap)
        self._doc = DocumentChunker(max_chars=chunk_size_doc, overlap=overlap)
        self._cr = CRChunker()

    def chunk(self, doc: CleanDocument) -> List[TextChunk]:
        if doc.doc_type == "code":
            return self._code.chunk(doc)
        elif doc.doc_type == "document":
            return self._doc.chunk(doc)
        elif doc.doc_type == "cr_record":
            return self._cr.chunk(doc)
        return []

    def chunk_all(self, docs: List[CleanDocument]) -> List[TextChunk]:
        all_chunks: List[TextChunk] = []
        for doc in docs:
            all_chunks.extend(self.chunk(doc))
        logger.info("chunk_complete", input_docs=len(docs), output_chunks=len(all_chunks))
        return all_chunks


# ── 공통 헬퍼 ────────────────────────────────────────────────────────


def _base_meta(doc: CleanDocument) -> dict:
    return {
        "source": doc.source,
        "type": doc.doc_type,
        "doc_id": doc.doc_id,
        "title": doc.title,
        "url": doc.url,
        "date": doc.date,
        "language": doc.language,
    }


def _split_by_size(text: str, max_chars: int, overlap: int) -> List[str]:
    """고정 크기 분할 with overlap"""
    if len(text) <= max_chars:
        return [text]
    parts = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        parts.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return parts
