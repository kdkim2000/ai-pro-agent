# tests/test_scaffold.py
"""LangGraph 뼈대 DAG 테스트

T1-1_GUIDE.md §7.2 기반.
LangGraph 설치 및 기본 DAG 실행 정상 동작을 확인한다.
※ 사내 API 불필요 — 로컬에서 즉시 실행 가능.
"""
from src.agent.scaffold import build_scaffold_graph, AgentState
from langchain_core.messages import HumanMessage


def test_new_dev_routing():
    """신규 개발 CR 라우팅 테스트 — requirement_skill 경유"""
    app = build_scaffold_graph()
    state: AgentState = {
        "messages": [HumanMessage(content="신규 화면")],
        "cr_id": "CR-001",
        "cr_type": "new_dev",
        "current_step": "start",
        "gate_results": {},
        "artifacts": {},
    }
    result = app.invoke(state)
    assert result["gate_results"].get("requirement") is True
    assert result["gate_results"].get("gate_check") is True
    print("✅ 신규개발 라우팅 정상")


def test_db_change_routing():
    """DB 스키마 변경 CR 라우팅 테스트 — impact_analysis_skill 경유"""
    app = build_scaffold_graph()
    state: AgentState = {
        "messages": [HumanMessage(content="DB 스키마 변경")],
        "cr_id": "CR-002",
        "cr_type": "db_change",
        "current_step": "start",
        "gate_results": {},
        "artifacts": {},
    }
    result = app.invoke(state)
    assert result["current_step"] == "requirement_done"
    assert result["gate_results"].get("gate_check") is True
    print("✅ DB 변경 라우팅 정상")


def test_feature_change_routing():
    """기능 변경 CR 라우팅 테스트 — requirement_skill 경유"""
    app = build_scaffold_graph()
    state: AgentState = {
        "messages": [HumanMessage(content="기존 화면 기능 변경")],
        "cr_id": "CR-003",
        "cr_type": "feature_change",
        "current_step": "start",
        "gate_results": {},
        "artifacts": {},
    }
    result = app.invoke(state)
    assert result["gate_results"].get("requirement") is True
    print("✅ 기능변경 라우팅 정상")
