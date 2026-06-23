# src/agent/scaffold.py
"""LangGraph 기반 Agent 뼈대 (Scaffold)

T1-1_GUIDE.md §7.1 기반 구현.
T1-1 단계에서는 실제 Skill을 붙이기 전에 LangGraph 정상 동작을 확인하는
뼈대(Scaffold)를 구현한다. T3에서 실 Skill로 교체 예정.
"""
from __future__ import annotations
from typing import TypedDict, Annotated, List
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage


# ── State 정의 ──────────────────────────────────────────────
class AgentState(TypedDict):
    """Agent 전역 상태 — 각 Skill이 읽고 업데이트

    Attributes:
        messages: LangGraph 메시지 히스토리 (add_messages 리듀서)
        cr_id: CR 고유 식별자
        cr_type: CR 유형 ("new_dev" | "feature_change" | "db_change")
        current_step: 현재 처리 단계
        gate_results: 각 단계별 게이트 통과 결과
        artifacts: 생성된 산출물 모음
    """
    messages: Annotated[List[BaseMessage], add_messages]
    cr_id: str
    cr_type: str            # "new_dev" | "feature_change" | "db_change"
    current_step: str
    gate_results: dict      # {step_name: bool}
    artifacts: dict         # 생성된 산출물 모음


# ── 노드 함수 정의 (Scaffold — 실 Skill은 T3에서 구현) ─────
def route_by_cr_type(state: AgentState) -> str:
    """CR 유형에 따라 다음 노드 결정 (Conditional Routing)

    - new_dev / feature_change → 요구사항 구체화부터 시작
    - db_change → 영향도 분석부터 시작
    """
    cr_type = state.get("cr_type", "new_dev")
    routing_map = {
        "new_dev": "requirement_skill",
        "feature_change": "requirement_skill",
        "db_change": "impact_analysis_skill",
    }
    return routing_map.get(cr_type, "requirement_skill")


def requirement_skill_stub(state: AgentState) -> AgentState:
    """요구사항 구체화 Skill (Stub) — T3-3에서 실 구현으로 교체"""
    print(f"[T3-3 예정] 요구사항 구체화 실행: CR={state['cr_id']}")
    state["current_step"] = "requirement_done"
    state["gate_results"]["requirement"] = True
    return state


def impact_analysis_skill_stub(state: AgentState) -> AgentState:
    """영향도 분석 Skill (Stub) — T3-4에서 실 구현으로 교체"""
    print(f"[T3-4 예정] 영향도 분석 실행: CR={state['cr_id']}")
    state["current_step"] = "requirement_done"
    state["gate_results"]["requirement"] = True
    return state


def gate_check(state: AgentState) -> AgentState:
    """관리 포인트 게이트 점검 (Stub) — T3-9에서 실 구현으로 교체"""
    print(f"[T3-9 예정] 게이트 점검: {state['gate_results']}")
    all_passed = all(state["gate_results"].values())
    state["gate_results"]["gate_check"] = all_passed
    return state


def check_gate_result(state: AgentState) -> str:
    """게이트 결과에 따른 분기"""
    return "end" if state["gate_results"].get("gate_check") else "gate_failed"


# ── 그래프 조립 ─────────────────────────────────────────────
def build_scaffold_graph():
    """LangGraph DAG 뼈대 조립

    Returns:
        CompiledGraph: 컴파일된 LangGraph 실행 가능 객체
    """
    graph = StateGraph(AgentState)

    graph.add_node("requirement_skill", requirement_skill_stub)
    graph.add_node("impact_analysis_skill", impact_analysis_skill_stub)
    graph.add_node("gate_check", gate_check)

    # 진입점 → CR 유형 라우팅
    graph.set_conditional_entry_point(
        route_by_cr_type,
        {
            "requirement_skill": "requirement_skill",
            "impact_analysis_skill": "impact_analysis_skill",
        },
    )

    graph.add_edge("requirement_skill", "gate_check")
    graph.add_edge("impact_analysis_skill", "gate_check")
    graph.add_conditional_edges(
        "gate_check",
        check_gate_result,
        {"end": END, "gate_failed": END},  # T3에서 실패 분기 구체화
    )

    return graph.compile()


# ── 실행 예시 ────────────────────────────────────────────────
if __name__ == "__main__":
    app = build_scaffold_graph()
    initial_state: AgentState = {
        "messages": [HumanMessage(content="신규 화면 개발 요청")],
        "cr_id": "CR-2026-001",
        "cr_type": "new_dev",
        "current_step": "start",
        "gate_results": {},
        "artifacts": {},
    }
    result = app.invoke(initial_state)
    print("최종 State:", result)
