# src/vectordb/febrix_client.py
"""Febrix 사내 벡터DB — LangChain VectorStore 커스텀 래퍼

T1-1_GUIDE.md §6.1 기반 구현.
SDS 사내 승인 벡터 검색 서비스인 Febrix를 LangChain VectorStore 인터페이스로
래핑하여 RAG 파이프라인 및 Skill에서 표준 방식으로 사용.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
from langchain_core.vectorstores import VectorStore
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
import httpx
import os
import uuid


class FebrixVectorStore(VectorStore):
    """Febrix 사내 벡터DB — LangChain VectorStore 래퍼

    환경변수:
        FEBRIX_ENDPOINT: Febrix API 엔드포인트 URL
        FEBRIX_API_KEY: API 인증 토큰
    """

    def __init__(
        self,
        collection_name: str,
        embedding: Embeddings,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 30,
    ):
        self.collection_name = collection_name
        self.embedding = embedding
        self.endpoint = endpoint or os.getenv("FEBRIX_ENDPOINT", "")
        self.api_key = api_key or os.getenv("FEBRIX_API_KEY", "")
        self.timeout = timeout
        self._base_url = f"{self.endpoint}/api/v1"
        self._headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, **kwargs) -> dict:
        """Febrix API HTTP 요청 헬퍼"""
        url = f"{self._base_url}{path}"
        with httpx.Client(timeout=self.timeout, verify=False) as client:
            response = getattr(client, method)(url, headers=self._headers, **kwargs)
            response.raise_for_status()
            return response.json()

    # ── 컬렉션 관리 ──────────────────────────────────────────

    def create_collection(self, dimension: int = 1536) -> dict:
        """컬렉션 생성 (없을 경우 초기 1회 실행)"""
        return self._request(
            "post",
            "/collections",
            json={
                "name": self.collection_name,
                "dimension": dimension,
                "metric": "cosine",      # 코사인 유사도
            },
        )

    def get_or_create_collection(self, dimension: int = 1536) -> dict:
        """컬렉션 존재 여부 확인 후 없으면 생성"""
        try:
            return self._request("get", f"/collections/{self.collection_name}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return self.create_collection(dimension)
            raise

    # ── 벡터 적재 ────────────────────────────────────────────

    def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[dict]] = None,
        ids: Optional[List[str]] = None,
        **kwargs,
    ) -> List[str]:
        """텍스트 → 임베딩 → Febrix 적재"""
        if not ids:
            ids = [str(uuid.uuid4()) for _ in texts]
        if not metadatas:
            metadatas = [{} for _ in texts]

        vectors = self.embedding.embed_documents(texts)

        points = [
            {
                "id": id_,
                "vector": vector,
                "payload": {**meta, "text": text},
            }
            for id_, vector, text, meta in zip(ids, vectors, texts, metadatas)
        ]

        self._request(
            "post",
            f"/collections/{self.collection_name}/points",
            json={"points": points},
        )
        return ids

    def add_documents(self, documents: List[Document], **kwargs) -> List[str]:
        """Document 객체 리스트 적재"""
        texts = [doc.page_content for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        return self.add_texts(texts, metadatas=metadatas, **kwargs)

    # ── 벡터 검색 ────────────────────────────────────────────

    def similarity_search(
        self, query: str, k: int = 5, filter: Optional[dict] = None, **kwargs
    ) -> List[Document]:
        """코사인 유사도 기반 유사 문서 검색"""
        docs_and_scores = self.similarity_search_with_score(
            query, k=k, filter=filter, **kwargs
        )
        return [doc for doc, _ in docs_and_scores]

    def similarity_search_with_score(
        self, query: str, k: int = 5, filter: Optional[dict] = None, **kwargs
    ) -> List[Tuple[Document, float]]:
        """유사 문서 검색 (점수 포함)"""
        query_vector = self.embedding.embed_query(query)

        payload: Dict[str, Any] = {
            "vector": query_vector,
            "top": k,
            "with_payload": True,
        }
        if filter:
            payload["filter"] = filter

        result = self._request(
            "post",
            f"/collections/{self.collection_name}/points/search",
            json=payload,
        )

        docs_with_scores = []
        for hit in result.get("result", []):
            payload_data = hit.get("payload", {})
            text = payload_data.pop("text", "")
            doc = Document(page_content=text, metadata=payload_data)
            score = hit.get("score", 0.0)
            docs_with_scores.append((doc, score))

        return docs_with_scores

    @classmethod
    def from_texts(
        cls,
        texts: List[str],
        embedding: Embeddings,
        metadatas: Optional[List[dict]] = None,
        collection_name: str = "default",
        **kwargs,
    ) -> "FebrixVectorStore":
        """텍스트 리스트로부터 VectorStore 생성 (LangChain 표준 팩토리)"""
        store = cls(
            collection_name=collection_name,
            embedding=embedding,
            **kwargs,
        )
        store.get_or_create_collection()
        store.add_texts(texts, metadatas=metadatas)
        return store
