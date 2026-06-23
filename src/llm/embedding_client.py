# src/llm/embedding_client.py
"""AI Pro 임베딩 엔드포인트 클라이언트

T1-1_GUIDE.md §5.1 기반 구현.
LangChain Embeddings 인터페이스를 구현하여
Febrix VectorStore 및 RAG 파이프라인에서 표준 방식으로 사용.
"""
from __future__ import annotations
from typing import List
from langchain_core.embeddings import Embeddings
import httpx
import os


class AiProEmbeddings(Embeddings):
    """AI Pro 임베딩 엔드포인트 클라이언트

    환경변수:
        AIPRO_ENDPOINT: AI Pro API 엔드포인트 URL
        AIPRO_API_KEY: API 인증 키
        AIPRO_EMBEDDING_MODEL: 임베딩 모델명 (기본: aiPro-embedding)
    """

    endpoint: str = ""
    api_key: str = ""
    model_name: str = "aiPro-embedding"
    batch_size: int = 32     # 사내 API 배치 제한에 맞게 조정
    timeout: int = 30

    def __init__(self, **kwargs):
        # pydantic v2 호환
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.endpoint = os.getenv("AIPRO_ENDPOINT", self.endpoint)
        self.api_key = os.getenv("AIPRO_API_KEY", self.api_key)
        self.model_name = os.getenv("AIPRO_EMBEDDING_MODEL", self.model_name)

    def _call_api(self, texts: List[str]) -> List[List[float]]:
        """AI Pro 임베딩 API 호출"""
        payload = {"model": self.model_name, "input": texts}
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=self.timeout, verify=False) as client:
            response = client.post(
                f"{self.endpoint}/v1/embeddings",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
        # OpenAI 호환 포맷 가정: data["data"][i]["embedding"]
        return [item["embedding"] for item in data["data"]]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """문서 임베딩 (배치 처리)

        batch_size 단위로 분할하여 API 호출 횟수를 최적화한다.
        """
        results = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i: i + self.batch_size]
            results.extend(self._call_api(batch))
        return results

    def embed_query(self, text: str) -> List[float]:
        """쿼리 임베딩 (단건)"""
        return self._call_api([text])[0]
