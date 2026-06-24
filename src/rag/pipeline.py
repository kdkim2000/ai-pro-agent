# src/rag/pipeline.py
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .collector import DataCollector, RawDocument
from .preprocessor import Preprocessor, CleanDocument
from .chunker import Chunker, TextChunk
from .embedder import Embedder
from .indexer import Indexer, IndexResult
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PipelineResult:
    """파이프라인 전체 실행 결과 요약"""
    collected: Dict[str, int] = field(default_factory=dict)
    preprocessed: int = 0
    chunked: int = 0
    indexed: List[IndexResult] = field(default_factory=list)
    elapsed_sec: float = 0.0
    errors: List[str] = field(default_factory=list)


class RAGPipeline:
    """수집 → 전처리 → 청킹 → 임베딩 → 적재 전 단계 오케스트레이터"""

    def __init__(
        self,
        chunk_size_code: int = 1500,
        chunk_size_doc: int = 1000,
        overlap: int = 100,
        batch_size: int = 32,
        cache_ttl: int = 3600,
    ) -> None:
        self._collector = DataCollector()
        self._preprocessor = Preprocessor()
        self._chunker = Chunker(
            chunk_size_code=chunk_size_code,
            chunk_size_doc=chunk_size_doc,
            overlap=overlap,
        )
        self._embedder = Embedder(batch_size=batch_size, ttl_seconds=cache_ttl)
        self._indexer = Indexer()

    def run(
        self,
        query: str = "",
        source: Optional[str] = None,
    ) -> PipelineResult:
        """전체 파이프라인 실행.

        Args:
            query: 수집 검색어 (빈 문자열이면 기본 검색)
            source: "github" | "confluence" | "doodream" | None (전체)
        """
        start_t = time.monotonic()
        result = PipelineResult()
        logger.info("pipeline_start", query=query, source=source)

        # 1. 수집
        try:
            raw_map = self._collector.collect_all(query)
            if source:
                raw_map = {k: v for k, v in raw_map.items() if k == source}
            result.collected = {k: len(v) for k, v in raw_map.items()}
            raw_docs: List[RawDocument] = [doc for docs in raw_map.values() for doc in docs]
            logger.info("collect_done", counts=result.collected)
        except Exception as exc:
            result.errors.append(f"collect: {exc}")
            logger.error("collect_error", error=str(exc))
            return result

        # 2. 전처리
        try:
            clean_docs: List[CleanDocument] = self._preprocessor.process_all(raw_docs)
            result.preprocessed = len(clean_docs)
        except Exception as exc:
            result.errors.append(f"preprocess: {exc}")
            logger.error("preprocess_error", error=str(exc))
            return result

        # 3. 청킹
        try:
            chunks: List[TextChunk] = self._chunker.chunk_all(clean_docs)
            result.chunked = len(chunks)
        except Exception as exc:
            result.errors.append(f"chunk: {exc}")
            logger.error("chunk_error", error=str(exc))
            return result

        # 4. 임베딩 (네트워크 필요 — 실패 시 경고 후 계속)
        try:
            self._indexer.ensure_collections()
            lc_docs = self._embedder.embed_chunks(chunks)
        except Exception as exc:
            result.errors.append(f"embed: {exc}")
            logger.warning("embed_error_skipped", error=str(exc))
            lc_docs = [c.to_langchain_doc() for c in chunks]

        # 5. 적재
        try:
            index_results = self._indexer.index_documents(lc_docs)
            result.indexed = index_results
        except Exception as exc:
            result.errors.append(f"index: {exc}")
            logger.error("index_error", error=str(exc))

        result.elapsed_sec = time.monotonic() - start_t
        logger.info(
            "pipeline_complete",
            collected=sum(result.collected.values()),
            preprocessed=result.preprocessed,
            chunked=result.chunked,
            elapsed_sec=round(result.elapsed_sec, 2),
            errors=len(result.errors),
        )
        return result
