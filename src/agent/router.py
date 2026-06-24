# src/agent/router.py
"""
CR 유형별 Conditional Routing 함수 (T1-3)

LangGraph 엣지의 분기 로직을 담당한다.
"""
from __future__ import annotations

from src.agent.state import AgentState, CRType, HITLStatus


def route_by_cr_type(state: AgentState) -> str:
    """
    진입점 라우터: CR 유형에 따라 첫 번째 실행 노드 결정.

    - new_dev / feature_change: 요구사항 구체화부터 시작
    - db_change:                영향도 분석부터 시작 (DB 변경 범위 먼저 파악)
    """
    cr_type = state.get("cr_type", CRType.NEW_DEV)

    if cr_type == CRType.DB_CHANGE:
        return "impact_analysis"

    # new_dev, feature_change
    return "requirement"


def check_gate_result(state: AgentState) -> str:
    """
    게이트 점검 결과에 따라 분기.
    gate_result.passed == True → 배포 단계 진행
    gate_result.passed == False → HITL 게이트 중단
    gate_attempts >= 3 → 강제 에스컬레이션 (무한 루프 방지)
    """
    gate_result   = state.get("gate_result")
    gate_attempts = state.get("gate_attempts", 0)

    # 게이트 미수행 또는 재시도 초과
    if gate_result is None:
        return "failed"
    if gate_attempts >= 3:
        return "failed"  # 에스컬레이션

    return "passed" if gate_result.passed else "failed"


def check_hitl_status(state: AgentState) -> str:
    """
    HITL 상태에 따라 분기.
    - approved: 다음 단계 진행
    - rejected: 현재 단계 재수행
    - waiting / not_reached: 계속 대기
    """
    status = state.get("hitl_status", HITLStatus.NOT_REACHED)

    if status == HITLStatus.APPROVED:
        return "approved"
    if status == HITLStatus.REJECTED:
        return "rejected"
    return "waiting"
