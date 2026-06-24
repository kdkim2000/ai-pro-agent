# src/rag/indexer.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List

from langchain_core.documents import Document

from src.vectordb.febrix_client import FebrixVectorStore
from src.vectordb.collections import COLLECTIONS
from src.llm.embedding_client import AiProEmbeddings
from src.utils.logger import get_logger

logger = get_logger(__name__)

SOURCE_TO_COLLECTION: Dict[str, str] = {
    "github": "github_code",
    "confluence": "confluence_docs",
    "doodream": "cr_history",
}


@dataclass
class IndexResult:
    """단일 컬렉션 적재 결과"""
    collection: str
    indexed_count: int
    success: bool
    error: str = ""


class Indexer:
    """LangChain Document → Febrix VectorStore 3-컬렉션 분류 적재"""

    def __init__(self) -> None:
        embedding = AiProEmbeddings()
        self._stores: Dict[str, FebrixVectorStore] = {
            col_key: FebrixVectorStore(
                collection_name=COLLECTIONS[col_key]["name"],
                embedding=embedding,
            )
            for col_key in SOURCE_TO_COLLECTION.values()
        }

    def ensure_collections(self) -> None:
        """3-컬렉션 존재 확인 후 없으면 자동 생성"""
        for col_key, store in self._stores.items():
            dim = COLLECTIONS[col_key]["dimension"]
            store.get_or_create_collection(dimension=dim)
            logger.info("collection_ready", collection=COLLECTIONS[col_key]["name"])

    def index_documents(self, docs: List[Document]) -> List[IndexResult]:
        """소스별 분류 후 해당 컬렉션에 적재"""
        buckets: Dict[str, List[Document]] = {k: [] for k in SOURCE_TO_COLLECTION.values()}

        for doc in docs:
            source = doc.metadata.get("source", "")
            col_key = SOURCE_TO_COLLECTION.get(source)
            if col_key:
                buckets[col_key].append(doc)
            else:
                logger.warning("unknown_source_skipped", source=source)

        results = []
        for col_key, col_docs in buckets.items():
            if not col_docs:
                continue
            results.append(self._index_to_collection(col_key, col_docs))

        total = sum(r.indexed_count for r in results if r.success)
        logger.info("index_complete", total=total, collections=len(results))
        return results

    def _index_to_collection(self, col_key: str, docs: List[Document]) -> IndexResult:
        store = self._stores[col_key]
        col_name = COLLECTIONS[col_key]["name"]
        try:
            texts = [doc.page_content for doc in docs]
            metadatas = [
                {k: v for k, v in doc.metadata.items() if k != "_vector"}
                for doc in docs
            ]
            store.add_texts(texts, metadatas=metadatas)
            logger.info("indexed", collection=col_name, count=len(docs))
            return IndexResult(collection=col_name, indexed_count=len(docs), success=True)
        except Exception as exc:
            logger.error("index_failed", collection=col_name, error=str(exc))
            return IndexResult(collection=col_name, indexed_count=0, success=False, error=str(exc))
