# src/agent/nodes.py
"""
LangGraph 노드 함수 모음 (T1-3)

각 노드 함수는 Skill.run()을 호출하는 얇은 래퍼다.
T3에서 실 Skill 구현이 완성되면 import만 교체하면 된다.
"""
from __future__ import annotations

from typing import Callable

from langgraph.types import interrupt

from src.agent.state import AgentState, HITLStatus, StepName


# ── Skill 노드 함수 ────────────────────────────────────────────────────────────


def node_requirement(state: AgentState) -> dict:
    """요구사항 구체화 노드"""
    from src.skills.s01_requirement import RequirementSkill
    return RequirementSkill().run(state)


def node_impact_analysis(state: AgentState) -> dict:
    """영향도 분석 노드"""
    from src.skills.s02_impact import ImpactAnalysisSkill
    return ImpactAnalysisSkill().run(state)


def node_estimation(state: AgentState) -> dict:
    """공수 산정 노드"""
    from src.skills.s03_estimation import EstimationSkill
    return EstimationSkill().run(state)


def node_task_breakdown(state: AgentState) -> dict:
    """Task 분해 노드"""
    from src.skills.s04_task_breakdown import TaskBreakdownSkill
    return TaskBreakdownSkill().run(state)


def node_artifact(state: AgentState) -> dict:
    """산출물 초안 생성 노드"""
    from src.skills.s05_artifact import ArtifactSkill
    return ArtifactSkill().run(state)


def node_registration(state: AgentState) -> dict:
    """시스템 등록 지원 노드"""
    from src.skills.s06_registration import RegistrationSkill
    return RegistrationSkill().run(state)


def node_gate_check(state: AgentState) -> dict:
    """관리 포인트 게이트 노드"""
    from src.skills.s07_gate import GateSkill
    return GateSkill().run(state)


def node_deploy(state: AgentState) -> dict:
    """배포 준비 지원 노드"""
    from src.skills.s08_deploy import DeploySkill
    return DeploySkill().run(state)


# ── 특수 노드 함수 ─────────────────────────────────────────────────────────────


def node_done(state: AgentState) -> dict:
    """완료 처리 — 이력 저장, 메트릭 기록"""
    from src.utils.metrics import record_completion
    record_completion(state)
    return {
        "current_step":    StepName.DONE,
        "completed_steps": list(state.get("completed_steps", [])) + [StepName.DONE],
    }


def node_error_handler(state: AgentState) -> dict:
    """오류 처리 — 감사 로그 기록, 담당자 알림"""
    import logging
    logger = logging.getLogger(__name__)
    logger.error(
        "Agent 오류 발생",
        extra={
            "cr_id":         state.get("cr_id"),
            "error_step":    state.get("error_step"),
            "error_message": state.get("error_message"),
            "step_count":    state.get("step_count"),
        },
    )
    return {
        "current_step": StepName.DONE,
    }


def node_hitl_wait(hitl_point_name: str) -> Callable:
    """
    HITL 중단점 노드 생성 팩토리.
    interrupt()를 호출하여 흐름을 중단하고 담당자 입력을 기다린다.

    resume 방법:
        app.invoke(
            Command(resume="approved"),   # 또는 "rejected"
            config={"configurable": {"thread_id": thread_id}},
        )
    """
    def _node(state: AgentState) -> dict:
        if state.get("hitl_status") == HITLStatus.WAITING:
            # 이미 대기 중 — resume 값 확인
            return {}

        # 중단점 도달 → interrupt() 호출
        feedback = interrupt({
            "hitl_point":   hitl_point_name,
            "current_step": state.get("current_step"),
            "cr_id":        state.get("cr_id"),
            "message": (
                f"[{hitl_point_name}] 담당자 확인이 필요합니다. "
                "'approved' 또는 'rejected'를 입력하세요."
            ),
        })

        # resume 후 실행됨
        status = HITLStatus.APPROVED if feedback == "approved" else HITLStatus.REJECTED
        return {
            "hitl_status":   status,
            "hitl_point":    hitl_point_name,
            "hitl_feedback": str(feedback),
        }

    _node.__name__ = f"node_{hitl_point_name}"
    return _node
