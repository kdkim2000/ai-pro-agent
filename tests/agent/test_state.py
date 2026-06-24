# tests/agent/test_state.py
"""
AgentState 스키마 상세 검증 테스트.
"""
import datetime
import os

import pytest

os.environ["USE_MOCK_CONNECTORS"] = "true"

from src.agent.state import (
    ArtifactResult,
    CRInfo,
    CRType,
    DeployResult,
    EstimationResult,
    GateResult,
    HITLStatus,
    ImpactAnalysisResult,
    RegistrationResult,
    RequirementResult,
    SkillExecutionLog,
    StepName,
    TaskBreakdownResult,
    create_initial_state,
)


def test_cr_type_enum_values():
    assert CRType.NEW_DEV.value        == "new_dev"
    assert CRType.FEATURE_CHANGE.value == "feature_change"
    assert CRType.DB_CHANGE.value      == "db_change"
    print("✅ CRType Enum 값 정상")


def test_step_name_enum_values():
    expected = [
        "init", "requirement", "impact_analysis", "estimation",
        "task_breakdown", "artifact", "registration", "gate_check",
        "deploy", "done",
    ]
    for v in expected:
        assert any(s.value == v for s in StepName), f"StepName 누락: {v}"
    print(f"✅ StepName Enum {len(expected)}개 확인")


def test_hitl_status_enum_values():
    assert HITLStatus.NOT_REACHED.value == "not_reached"
    assert HITLStatus.WAITING.value     == "waiting"
    assert HITLStatus.APPROVED.value    == "approved"
    assert HITLStatus.REJECTED.value    == "rejected"
    print("✅ HITLStatus Enum 값 정상")


def test_requirement_result_dataclass():
    r = RequirementResult(
        structured_requirement  = "테스트 요구사항",
        clarification_questions = ["질문1"],
        similar_cr_ids          = ["CR-001"],
        related_docs            = ["http://confluence/page"],
        confirmed               = False,
    )
    assert r.structured_requirement == "테스트 요구사항"
    assert r.confirmed is False
    print("✅ RequirementResult dataclass 정상")


def test_impact_analysis_result_dataclass():
    r = ImpactAnalysisResult(
        affected_tables           = ["TB_USER"],
        affected_programs         = ["PGM001"],
        has_db_schema_change      = True,
        oracle_consistency_issues = [],
        impact_summary            = "테스트 영향도 요약",
    )
    assert r.has_db_schema_change is True
    assert r.oracle_consistency_issues == []
    print("✅ ImpactAnalysisResult dataclass 정상")


def test_gate_result_dataclass():
    r = GateResult(
        passed       = True,
        checked_at   = datetime.datetime.now().isoformat(),
        passed_items = ["requirement_confirmed"],
        failed_items = [],
        gate_version = "1.0.0",
    )
    assert r.passed is True
    assert len(r.passed_items) == 1
    print("✅ GateResult dataclass 정상")


def test_cr_info_dataclass():
    cr = CRInfo(
        cr_id      = "CR-2026-001",
        title      = "신규 화면 개발",
        description = "테스트 설명",
        cr_type    = CRType.NEW_DEV,
        requester  = "홍길동",
        assignee   = "김철수",
        created_at = datetime.datetime.now().isoformat(),
    )
    assert cr.cr_id == "CR-2026-001"
    assert cr.affected_systems == []
    assert cr.tags == []
    print("✅ CRInfo dataclass 정상")


def test_initial_state_messages():
    """초기 State messages 필드에 HumanMessage 포함"""
    from langchain_core.messages import HumanMessage
    state = create_initial_state("CR-001", CRType.NEW_DEV)
    assert len(state["messages"]) == 1
    assert isinstance(state["messages"][0], HumanMessage)
    assert "CR-001" in state["messages"][0].content
    print("✅ 초기 State messages HumanMessage 포함 정상")


def test_initial_state_with_cr_info():
    """cr_info 포함 초기 State 생성"""
    cr_info = CRInfo(
        cr_id      = "CR-001",
        title      = "테스트",
        description = "설명",
        cr_type    = CRType.NEW_DEV,
        requester  = "테스터",
        assignee   = "담당자",
        created_at = datetime.datetime.now().isoformat(),
    )
    state = create_initial_state("CR-001", CRType.NEW_DEV, cr_info=cr_info)
    assert state["cr_info"] is not None
    assert state["cr_info"].title == "테스트"
    print("✅ cr_info 포함 초기 State 생성 정상")
