# tests/test_smoke.py
"""T1-1 완료 기준 검증 스모크 테스트

T1-1_GUIDE.md §9 기반.
모든 컴포넌트가 정상 설치·연동되었는지 한 번에 확인하는 통합 테스트.
모든 테스트 통과 시 T1-2(시스템 연동 인터페이스 설계)로 진행.

※ test_01 ~ test_04는 사내 API 연동 필요 — SCP/VDI 환경에서 실행.
※ test_05는 로컬에서 즉시 실행 가능.
"""
import pytest
from langchain_core.messages import HumanMessage


def test_01_aiPro_llm():
    """AI Pro LLM 호출 성공"""
    from src.llm.aiPro_client import AiProChatModel
    llm = AiProChatModel()
    result = llm._generate([HumanMessage(content="ping")])
    assert result.generations[0].message.content
    print("✅ [1/5] AI Pro LLM 정상")


def test_02_embedding():
    """임베딩 모델 벡터 반환"""
    from src.llm.embedding_client import AiProEmbeddings
    emb = AiProEmbeddings()
    vec = emb.embed_query("테스트")
    assert len(vec) > 0
    print(f"✅ [2/5] 임베딩 정상 (dim={len(vec)})")


def test_03_febrix_collection():
    """Febrix 컬렉션 생성·확인"""
    from src.vectordb.febrix_client import FebrixVectorStore
    from src.llm.embedding_client import AiProEmbeddings
    store = FebrixVectorStore("smoke_test_collection", AiProEmbeddings())
    result = store.get_or_create_collection()
    assert result is not None
    print("✅ [3/5] Febrix 컬렉션 정상")


def test_04_febrix_search():
    """Febrix 적재·검색 왕복"""
    from src.vectordb.febrix_client import FebrixVectorStore
    from src.llm.embedding_client import AiProEmbeddings
    from langchain_core.documents import Document
    store = FebrixVectorStore("smoke_test_collection", AiProEmbeddings())
    store.add_documents([Document(page_content="스모크 테스트 문서")])
    results = store.similarity_search("스모크 테스트", k=1)
    assert len(results) > 0
    print("✅ [4/5] Febrix 검색 정상")


def test_05_langgraph_scaffold():
    """LangGraph 뼈대 DAG 실행"""
    from src.agent.scaffold import build_scaffold_graph, AgentState
    app = build_scaffold_graph()
    result = app.invoke({
        "messages": [HumanMessage(content="테스트")],
        "cr_id": "SMOKE-001",
        "cr_type": "new_dev",
        "current_step": "start",
        "gate_results": {},
        "artifacts": {},
    })
    assert result["gate_results"].get("gate_check") is True
    print("✅ [5/5] LangGraph DAG 정상")
