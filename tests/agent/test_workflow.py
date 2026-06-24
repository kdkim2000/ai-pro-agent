# tests/agent/test_workflow.py
"""
T1-3 완료 기준 검증 테스트.
실 Skill 구현(T3) 없이 Stub으로 DAG 구조 전체를 검증한다.
"""
import datetime
import os

import pytest

os.environ["USE_MOCK_CONNECTORS"] = "true"

from langchain_core.messages import HumanMessage
from src.agent.router import check_gate_result, check_hitl_status, route_by_cr_type
from src.agent.state import (
    AgentState,
    CRType,
    GateResult,
    HITLStatus,
    StepName,
    create_initial_state,
)


# ── State 생성 테스트 ──────────────────────────────────────────────────────────


def test_create_initial_state():
    """초기 State 생성 검증"""
    state = create_initial_state(
        cr_id="CR-2026-TEST-001",
        cr_type=CRType.NEW_DEV,
    )
    assert state["cr_id"] == "CR-2026-TEST-001"
    assert state["cr_type"] == CRType.NEW_DEV
    assert state["current_step"] == StepName.INIT
    assert state["completed_steps"] == []
    assert state["step_count"] == 0
    assert state["hitl_status"] == HITLStatus.NOT_REACHED
    assert state["gate_attempts"] == 0
    assert state["execution_logs"] == []
    print("✅ 초기 State 생성 정상")


def test_state_all_fields_present():
    """AgentState 필수 필드 전체 존재 여부"""
    state = create_initial_state("CR-TEST", CRType.DB_CHANGE)
    required_fields = [
        "messages", "cr_id", "cr_type", "cr_info",
        "current_step", "completed_steps", "step_count",
        "hitl_status", "hitl_point", "hitl_feedback",
        "requirement_result", "impact_result", "estimation_result",
        "task_breakdown_result", "artifact_result",
        "registration_result", "gate_result", "deploy_result",
        "gate_attempts", "gate_history",
        "error_step", "error_message", "retry_count",
        "execution_logs", "artifacts",
    ]
    for field in required_fields:
        assert field in state, f"누락된 필드: {field}"
    print(f"✅ 전체 필드 존재 확인: {len(required_fields)}개")


# ── Routing 테스트 ─────────────────────────────────────────────────────────────


def test_route_new_dev():
    state = create_initial_state("CR-001", CRType.NEW_DEV)
    assert route_by_cr_type(state) == "requirement"
    print("✅ new_dev 라우팅: requirement")


def test_route_feature_change():
    state = create_initial_state("CR-002", CRType.FEATURE_CHANGE)
    assert route_by_cr_type(state) == "requirement"
    print("✅ feature_change 라우팅: requirement")


def test_route_db_change():
    state = create_initial_state("CR-003", CRType.DB_CHANGE)
    assert route_by_cr_type(state) == "impact_analysis"
    print("✅ db_change 라우팅: impact_analysis (영향도 먼저)")


# ── 게이트 라우터 테스트 ───────────────────────────────────────────────────────


def test_gate_passed():
    state = create_initial_state("CR-001", CRType.NEW_DEV)
    state["gate_result"] = GateResult(
        passed=True, checked_at=datetime.datetime.now().isoformat(),
        passed_items=["requirement_confirmed"], failed_items=[], gate_version="1.0"
    )
    state["gate_attempts"] = 0
    assert check_gate_result(state) == "passed"
    print("✅ 게이트 통과 라우팅")


def test_gate_failed():
    state = create_initial_state("CR-001", CRType.NEW_DEV)
    state["gate_result"] = GateResult(
        passed=False, checked_at=datetime.datetime.now().isoformat(),
        passed_items=[], failed_items=["program_master_draft_ready"], gate_version="1.0"
    )
    state["gate_attempts"] = 0
    assert check_gate_result(state) == "failed"
    print("✅ 게이트 실패 라우팅")


def test_gate_max_attempts():
    """게이트 재시도 3회 초과 → 강제 에스컬레이션"""
    state = create_initial_state("CR-001", CRType.NEW_DEV)
    state["gate_result"] = GateResult(
        passed=False, checked_at=datetime.datetime.now().isoformat(),
        passed_items=[], failed_items=["artifact_confirmed"], gate_version="1.0"
    )
    state["gate_attempts"] = 3
    assert check_gate_result(state) == "failed"
    print("✅ 게이트 최대 재시도 초과 → 에스컬레이션")


def test_gate_none_result():
    """gate_result가 None이면 failed"""
    state = create_initial_state("CR-001", CRType.NEW_DEV)
    assert check_gate_result(state) == "failed"
    print("✅ gate_result None → failed")


# ── HITL 라우터 테스트 ─────────────────────────────────────────────────────────


def test_hitl_approved():
    state = create_initial_state("CR-001", CRType.NEW_DEV)
    state["hitl_status"] = HITLStatus.APPROVED
    assert check_hitl_status(state) == "approved"
    print("✅ HITL 승인 라우팅")


def test_hitl_rejected():
    state = create_initial_state("CR-001", CRType.NEW_DEV)
    state["hitl_status"] = HITLStatus.REJECTED
    assert check_hitl_status(state) == "rejected"
    print("✅ HITL 반려 라우팅")


def test_hitl_waiting():
    state = create_initial_state("CR-001", CRType.NEW_DEV)
    state["hitl_status"] = HITLStatus.WAITING
    assert check_hitl_status(state) == "waiting"
    print("✅ HITL 대기 라우팅")


# ── BaseSkill 인터페이스 테스트 ────────────────────────────────────────────────


def test_base_skill_interface():
    """BaseSkill 구현체가 올바른 인터페이스를 가지는지 확인"""
    from src.skills.base import BaseSkill, SkillResult, SkillStatus

    class TestSkill(BaseSkill):
        skill_name  = "test_skill"
        step        = StepName.REQUIREMENT
        max_retries = 0

        def execute(self, state: AgentState) -> SkillResult:
            return SkillResult(
                status        = SkillStatus.SUCCESS,
                state_updates = {"current_step": StepName.REQUIREMENT},
                message       = "테스트 성공",
                confidence    = 0.9,
            )

    state  = create_initial_state("CR-TEST", CRType.NEW_DEV)
    skill  = TestSkill()
    result = skill.run(state)

    assert isinstance(result, dict)
    assert "current_step" in result
    assert "execution_logs" in result
    assert len(result["execution_logs"]) == 1
    print("✅ BaseSkill 인터페이스 정상")


def test_low_confidence_escalation():
    """신뢰도 낮으면 HITL 에스컬레이션 처리"""
    from src.skills.base import BaseSkill, SkillResult, SkillStatus

    class LowConfidenceSkill(BaseSkill):
        skill_name  = "low_conf"
        step        = StepName.REQUIREMENT
        max_retries = 0

        def execute(self, state: AgentState) -> SkillResult:
            return SkillResult(
                status        = SkillStatus.PARTIAL,
                state_updates = {},
                message       = "불확실한 결과",
                confidence    = 0.3,   # 임계값(0.5) 미만
            )

    state  = create_initial_state("CR-TEST", CRType.NEW_DEV)
    result = LowConfidenceSkill().run(state)

    assert result.get("hitl_status") == "waiting"
    assert result.get("hitl_point") == "low_conf_low_confidence"
    print("✅ 저신뢰도 HITL 에스컬레이션 정상")


def test_skill_failed_sets_error_fields():
    """Skill FAILED → error_step, error_message 설정"""
    from src.skills.base import BaseSkill, SkillResult, SkillStatus

    class FailingSkill(BaseSkill):
        skill_name  = "failing_skill"
        step        = StepName.ESTIMATION
        max_retries = 0

        def execute(self, state: AgentState) -> SkillResult:
            return SkillResult(
                status        = SkillStatus.FAILED,
                state_updates = {},
                message       = "테스트 오류",
                confidence    = 0.0,
            )

    state  = create_initial_state("CR-TEST", CRType.NEW_DEV)
    result = FailingSkill().run(state)

    assert result.get("error_step") == StepName.ESTIMATION
    assert result.get("error_message") == "테스트 오류"
    print("✅ Skill 실패 시 오류 필드 설정 정상")


# ── 게이트 엔진 테스트 ─────────────────────────────────────────────────────────


def test_gate_engine():
    """게이트 엔진 Config 기반 판별"""
    from src.gate.engine import GateEngine

    engine = GateEngine(config_path="config/gate_rules.yaml")
    state  = create_initial_state("CR-TEST", CRType.NEW_DEV)

    # 아무것도 완료 안 된 상태 → 게이트 실패
    result = engine.check(state)
    assert result.passed is False
    assert len(result.failed_items) > 0
    print(f"✅ 빈 State 게이트 실패: {result.failed_items[:3]}...")


# ── DAG 빌드 테스트 ────────────────────────────────────────────────────────────


def test_workflow_builds_without_error():
    """LangGraph DAG 빌드 오류 없음 확인"""
    from src.agent.workflow import build_app
    app = build_app(use_checkpointer=True)
    assert app is not None
    print("✅ LangGraph DAG 빌드 성공")


def test_workflow_graph_structure():
    """DAG 노드 구성 확인"""
    from src.agent.workflow import build_workflow
    graph    = build_workflow()
    compiled = graph.compile()

    # 그래프 노드 이름 목록 추출
    node_names = set(compiled.nodes.keys())
    expected_nodes = {
        "requirement", "impact_analysis", "estimation",
        "task_breakdown", "artifact", "hitl_artifact",
        "registration", "gate_check", "hitl_gate",
        "deploy", "hitl_deploy", "done", "error_handler",
    }
    for node in expected_nodes:
        assert node in node_names, f"누락된 노드: {node}"
    print(f"✅ DAG 노드 구성 확인: {len(expected_nodes)}개")
