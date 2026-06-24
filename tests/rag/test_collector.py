# tests/rag/test_collector.py
import os
os.environ["USE_MOCK_CONNECTORS"] = "true"

from src.rag.collector import DataCollector, RawDocument


def test_collect_github_returns_raw_docs():
    collector = DataCollector()
    docs = collector.collect_github_code("프로그램마스터")
    assert isinstance(docs, list)
    assert len(docs) > 0
    doc = docs[0]
    assert isinstance(doc, RawDocument)
    assert doc.source == "github"
    assert doc.doc_type == "code"
    assert doc.content


def test_collect_confluence_returns_raw_docs():
    collector = DataCollector()
    docs = collector.collect_confluence_docs("선박 관리")
    assert isinstance(docs, list)
    assert len(docs) > 0
    doc = docs[0]
    assert doc.source == "confluence"
    assert doc.doc_type == "document"
    assert doc.content


def test_collect_cr_history_returns_raw_docs():
    collector = DataCollector()
    docs = collector.collect_cr_history()
    assert isinstance(docs, list)
    assert len(docs) > 0
    doc = docs[0]
    assert doc.source == "doodream"
    assert doc.doc_type == "cr_record"
    assert "CR ID:" in doc.content


def test_collect_cr_content_has_required_fields():
    collector = DataCollector()
    docs = collector.collect_cr_history()
    content = docs[0].content
    for field_name in ["CR ID:", "제목:", "설명:", "유형:", "담당자:"]:
        assert field_name in content, f"'{field_name}' 필드 누락"


def test_collect_cr_history_filter_by_type():
    collector = DataCollector()
    docs = collector.collect_cr_history(cr_type="new_dev")
    assert all(doc.extra.get("cr_type") == "new_dev" for doc in docs)


def test_collect_cr_omits_unmanaged_fields():
    """두드림 미관리 항목(영향 시스템·태그·공수)은 직렬화되지 않아야 한다."""
    collector = DataCollector()
    docs = collector.collect_cr_history()
    content = docs[0].content
    for absent in ["영향 시스템", "태그", "실제 공수", "예상 공수"]:
        assert absent not in content, f"미관리 필드 '{absent}' 가 직렬화됨"
    for absent_key in ["actual_hours", "estimated_hours", "affected_systems", "tags"]:
        assert absent_key not in docs[0].extra, f"미관리 키 '{absent_key}' 가 extra 에 존재"


def test_collect_cr_extra_has_managed_fields():
    """두드림 실제 관리 필드는 extra 에 보존되어야 한다."""
    collector = DataCollector()
    docs = collector.collect_cr_history()
    for key in ["cr_type", "status", "requester", "assignee"]:
        assert key in docs[0].extra, f"관리 필드 '{key}' 누락"


def test_collect_cr_incremental_by_status():
    """since_days + status 증분 경로 — 완료(closed) 건만 수집."""
    collector = DataCollector()
    docs = collector.collect_cr_history(since_days=90, status="closed")
    assert len(docs) > 0
    assert all(doc.extra.get("status") == "closed" for doc in docs)


def test_collect_all_returns_all_sources():
    collector = DataCollector()
    result = collector.collect_all("test")
    assert set(result.keys()) == {"github", "confluence", "doodream"}
    assert sum(len(v) for v in result.values()) > 0
