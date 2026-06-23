# tests/test_febrix.py
"""Febrix 벡터DB 연동 테스트

T1-1_GUIDE.md §6.3 기반.
컬렉션 생성, 문서 적재, 유사도 검색, 필터 검색을 확인한다.
※ 사내 API 연동 필요 — SCP/VDI 환경에서 실행.
"""
import pytest
from src.vectordb.febrix_client import FebrixVectorStore
from src.llm.embedding_client import AiProEmbeddings
from langchain_core.documents import Document


@pytest.fixture
def store():
    """테스트용 VectorStore 인스턴스"""
    emb = AiProEmbeddings()
    s = FebrixVectorStore(
        collection_name="dev_agent_test",
        embedding=emb,
    )
    s.get_or_create_collection()
    return s


def test_add_and_search(store):
    """문서 적재 및 유사도 검색 왕복 테스트"""
    docs = [
        Document(
            page_content="프로그램마스터 등록 누락 시 운영 이관 오류 발생",
            metadata={"source": "cr_history", "cr_id": "CR-001", "type": "incident"},
        ),
        Document(
            page_content="테이블마스터 미등록으로 Oracle 딕셔너리 정합성 불일치",
            metadata={"source": "cr_history", "cr_id": "CR-002", "type": "incident"},
        ),
        Document(
            page_content="신규 화면 개발 시 통합용어사전 미등록 용어 사용",
            metadata={"source": "cr_history", "cr_id": "CR-003", "type": "standard"},
        ),
    ]
    ids = store.add_documents(docs)
    assert len(ids) == 3
    print(f"✅ 적재 완료: {ids}")

    # 유사 검색
    results = store.similarity_search("마스터 등록 누락 문제", k=2)
    assert len(results) > 0
    print(f"✅ 검색 결과: {results[0].page_content[:80]}")


def test_search_with_filter(store):
    """필터 조건 포함 검색 테스트"""
    results = store.similarity_search_with_score(
        "Oracle 딕셔너리",
        k=3,
        filter={"type": {"$eq": "incident"}},
    )
    assert isinstance(results, list)
    for doc, score in results:
        print(f"  score={score:.4f}: {doc.page_content[:60]}")
