# src/rag/embedder.py
from __future__ import annotations
import hashlib
import time
from typing import Dict, List, Optional, Tuple

from langchain_core.documents import Document

from .chunker import TextChunk
from src.llm.embedding_client import AiProEmbeddings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class EmbeddingCache:
    """TTL 기반 인메모리 임베딩 캐시"""

    def __init__(self, ttl_seconds: int = 3600) -> None:
        self._store: Dict[str, Tuple[List[float], float]] = {}
        self._ttl = ttl_seconds

    def get(self, key: str) -> Optional[List[float]]:
        if key not in self._store:
            return None
        vector, ts = self._store[key]
        if time.time() - ts > self._ttl:
            del self._store[key]
            return None
        return vector

    def set(self, key: str, vector: List[float]) -> None:
        self._store[key] = (vector, time.time())

    @staticmethod
    def make_key(text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()


class Embedder:
    """TextChunk → LangChain Document (AI Pro 임베딩 + TTL 캐시)"""

    def __init__(self, batch_size: int = 32, ttl_seconds: int = 3600) -> None:
        self._model = AiProEmbeddings()
        self._cache = EmbeddingCache(ttl_seconds=ttl_seconds)
        self._batch_size = batch_size

    def embed_chunks(self, chunks: List[TextChunk]) -> List[Document]:
        """TextChunk 리스트를 임베딩하여 LangChain Document로 반환."""
        if not chunks:
            return []

        texts = [c.text for c in chunks]
        vectors = self._embed_with_cache(texts)

        docs = []
        for chunk, vector in zip(chunks, vectors):
            meta = dict(chunk.metadata)
            meta["_vector"] = vector
            docs.append(Document(page_content=chunk.text, metadata=meta))

        logger.info("embed_complete", chunks=len(chunks))
        return docs

    def _embed_with_cache(self, texts: List[str]) -> List[List[float]]:
        keys = [EmbeddingCache.make_key(t) for t in texts]
        result_map: Dict[int, List[float]] = {}
        miss_indices: List[int] = []
        miss_texts: List[str] = []

        for i, (key, text) in enumerate(zip(keys, texts)):
            cached = self._cache.get(key)
            if cached is not None:
                result_map[i] = cached
            else:
                miss_indices.append(i)
                miss_texts.append(text)

        if miss_texts:
            all_vectors: List[List[float]] = []
            for bs in range(0, len(miss_texts), self._batch_size):
                batch = miss_texts[bs: bs + self._batch_size]
                all_vectors.extend(self._model.embed_documents(batch))

            for idx, vector, text in zip(miss_indices, all_vectors, miss_texts):
                self._cache.set(keys[idx], vector)
                result_map[idx] = vector

        logger.info(
            "embed_cache_stats",
            total=len(texts),
            cache_hits=len(texts) - len(miss_texts),
            api_calls=len(miss_texts),
        )
        return [result_map[i] for i in range(len(texts))]
