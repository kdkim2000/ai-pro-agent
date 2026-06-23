# tests/test_embedding.py
"""임베딩 모델 연동 테스트

T1-1_GUIDE.md §5.2 기반.
단건 쿼리 임베딩과 배치 문서 임베딩의 정상 반환을 확인한다.
※ 사내 API 연동 필요 — SCP/VDI 환경에서 실행.
"""
from src.llm.embedding_client import AiProEmbeddings


def test_embed_single():
    """단건 쿼리 임베딩 테스트"""
    emb = AiProEmbeddings()
    vector = emb.embed_query("CR 요구사항 분석")
    assert isinstance(vector, list)
    assert len(vector) > 0
    assert all(isinstance(v, float) for v in vector)
    print(f"✅ 임베딩 차원: {len(vector)}")


def test_embed_batch():
    """배치 문서 임베딩 테스트"""
    emb = AiProEmbeddings()
    texts = ["프로그램 마스터 등록", "테이블 스키마 변경", "Oracle 딕셔너리 조회"]
    vectors = emb.embed_documents(texts)
    assert len(vectors) == 3
    assert len(vectors[0]) == len(vectors[1])   # 차원 동일
    print(f"✅ 배치 임베딩 성공: {len(vectors)}건, 차원 {len(vectors[0])}")
