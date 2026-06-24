# src/agent/workflow.py
"""
LangGraph DAG 조립 (T1-3)

프로그램 개발 전주기 지원 AI Agent — 전체 워크플로우.

노드 구성 (13개):
    requirement       → 요구사항 구체화 (T3-3)
    impact_analysis   → 영향도 분석 (T3-4)
    estimation        → 공수 산정 (T3-5)
    task_breakdown    → Task 분해 (T3-6)
    artifact          → 산출물 초안 생성 (T3-7)
    hitl_artifact     → HITL 중단점 ① (산출물 담당자 확인)
    registration      → 시스템 등록 지원 (T3-8)
    gate_check        → 관리 포인트 게이트 (T3-9)
    hitl_gate         → HITL 중단점 ② (게이트 미충족 항목 처리)
    deploy            → 배포 준비 지원 (T3-10)
    hitl_deploy       → HITL 중단점 ③ (PR 발행·Release 상신)
    done              → 완료 처리 및 이력 축적
    error_handler     → 오류 처리 및 에스컬레이션
"""
from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from src.agent.nodes import (
    node_artifact,
    node_deploy,
    node_done,
    node_error_handler,
    node_estimation,
    node_gate_check,
    node_hitl_wait,
    node_impact_analysis,
    node_registration,
    node_requirement,
    node_task_breakdown,
)
from src.agent.router import check_gate_result, check_hitl_status, route_by_cr_type
from src.agent.state import AgentState

MAX_STEPS = 25  # 무한루프 방지


def build_workflow() -> StateGraph:
    """
    프로그램 개발 전주기 지원 AI Agent — LangGraph DAG 조립.
    컴파일 전 StateGraph를 반환한다 (테스트에서 직접 컴파일 가능).
    """
    graph = StateGraph(AgentState)

    # ── 노드 등록 ──────────────────────────────────────────────────────────────
    graph.add_node("requirement",     node_requirement)
    graph.add_node("impact_analysis", node_impact_analysis)
    graph.add_node("estimation",      node_estimation)
    graph.add_node("task_breakdown",  node_task_breakdown)
    graph.add_node("artifact",        node_artifact)
    graph.add_node("hitl_artifact",   node_hitl_wait("hitl_artifact"))
    graph.add_node("registration",    node_registration)
    graph.add_node("gate_check",      node_gate_check)
    graph.add_node("hitl_gate",       node_hitl_wait("hitl_gate"))
    graph.add_node("deploy",          node_deploy)
    graph.add_node("hitl_deploy",     node_hitl_wait("hitl_deploy"))
    graph.add_node("done",            node_done)
    graph.add_node("error_handler",   node_error_handler)

    # ── 진입점: CR 유형에 따라 첫 노드 결정 ───────────────────────────────────
    graph.set_conditional_entry_point(
        route_by_cr_type,
        {
            "requirement":     "requirement",
            "impact_analysis": "impact_analysis",
        },
    )

    # ── 분석 단계 엣지 ─────────────────────────────────────────────────────────
    # new_dev / feature_change: requirement → impact_analysis → estimation → task_breakdown
    graph.add_conditional_edges(
        "requirement",
        _check_error_or_next("impact_analysis"),
        {"impact_analysis": "impact_analysis", "error_handler": "error_handler"},
    )
    graph.add_conditional_edges(
        "impact_analysis",
        _check_error_or_next("estimation"),
        {"estimation": "estimation", "error_handler": "error_handler"},
    )
    graph.add_conditional_edges(
        "estimation",
        _check_error_or_next("task_breakdown"),
        {"task_breakdown": "task_breakdown", "error_handler": "error_handler"},
    )
    graph.add_conditional_edges(
        "task_breakdown",
        _check_error_or_next("artifact"),
        {"artifact": "artifact", "error_handler": "error_handler"},
    )

    # ── 산출물 단계 엣지 + HITL ① ──────────────────────────────────────────────
    graph.add_edge("artifact", "hitl_artifact")
    graph.add_conditional_edges(
        "hitl_artifact",
        check_hitl_status,
        {
            "approved": "registration",
            "rejected": "artifact",       # 반려 시 재생성
            "waiting":  "hitl_artifact",  # 계속 대기 (외부에서 resume)
        },
    )

    # ── 등록 단계 엣지 ─────────────────────────────────────────────────────────
    graph.add_conditional_edges(
        "registration",
        _check_error_or_next("gate_check"),
        {"gate_check": "gate_check", "error_handler": "error_handler"},
    )

    # ── 게이트 엣지 + HITL ② ───────────────────────────────────────────────────
    graph.add_conditional_edges(
        "gate_check",
        check_gate_result,
        {
            "passed": "deploy",
            "failed": "hitl_gate",        # 미충족 → 담당자 처리 대기
        },
    )
    graph.add_conditional_edges(
        "hitl_gate",
        check_hitl_status,
        {
            "approved": "gate_check",     # 처리 완료 → 게이트 재검사
            "rejected": "registration",   # 등록부터 재수행
            "waiting":  "hitl_gate",
        },
    )

    # ── 배포 단계 엣지 + HITL ③ ────────────────────────────────────────────────
    graph.add_edge("deploy", "hitl_deploy")
    graph.add_conditional_edges(
        "hitl_deploy",
        check_hitl_status,
        {
            "approved": "done",
            "rejected": "deploy",         # 배포 준비 재수행
            "waiting":  "hitl_deploy",
        },
    )

    # ── 완료 ───────────────────────────────────────────────────────────────────
    graph.add_edge("done",          END)
    graph.add_edge("error_handler", END)

    return graph


def build_app(use_checkpointer: bool = True):
    """
    컴파일된 LangGraph 앱 반환.
    use_checkpointer=True: 메모리 체크포인터 사용 (HITL resume 지원)
    """
    graph        = build_workflow()
    checkpointer = MemorySaver() if use_checkpointer else None
    return graph.compile(
        checkpointer   = checkpointer,
        interrupt_before = ["hitl_artifact", "hitl_gate", "hitl_deploy"],
    )


def _check_error_or_next(next_node: str):
    """오류 발생 여부에 따라 다음 노드를 결정하는 라우터 생성 함수"""
    def router(state: AgentState) -> str:
        if state.get("error_step") and state.get("error_message"):
            return "error_handler"
        if state.get("step_count", 0) >= MAX_STEPS:
            return "error_handler"
        return next_node
    return router
