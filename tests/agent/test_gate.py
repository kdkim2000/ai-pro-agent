# tests/agent/test_gate.py
"""
GateEngine 규칙별 개별 검증 테스트.
T1-4 기준으로 업데이트 — 규칙 id 기반 검증.
"""
import datetime
import os

import pytest

os.environ["USE_MOCK_CONNECTORS"] = "true"
os.environ["GATE_ENV"]            = "mock"

from src.agent.state import (
    ArtifactResult,
    CRType,
    DeployResult,
    ImpactAnalysisResult,
    RegistrationResult,
    RequirementResult,
    create_initial_state,
)
from src.gate.engine import GateEngine


@pytest.fixture
def engine():
    return GateEngine(config_path="config/gate_rules.yaml")


def test_empty_state_fails_all_required(engine):
    """빈 State는 모든 필수 게이트 실패"""
    state  = create_initial_state("CR-TEST", CRType.NEW_DEV)
    result = engine.check(state)
    assert result.passed is False
    assert len(result.failed_items) > 0
    print(f"✅ 빈 State 게이트 실패: {len(result.failed_items)}개 미충족")


def test_requirement_confirmed_gate(engine):
    """REQ-004 — confirmed=True 시 통과"""
    state = create_initial_state("CR-TEST", CRType.NEW_DEV)

    # confirmed=False → REQ-004 실패
    state["requirement_result"] = RequirementResult(
        structured_requirement  = "요구사항 " * 10,  # 50자 이상
        clarification_questions = [],
        similar_cr_ids          = [],
        related_docs            = [],
        confirmed               = False,
    )
    result = engine.check(state)
    assert "REQ-004" in result.failed_items

    # confirmed=True → REQ-004 통과
    state["requirement_result"].confirmed = True
    result2 = engine.check(state)
    assert "REQ-004" not in result2.failed_items
    print("✅ REQ-004 (담당자 확인 완료) 게이트 정상")


def test_requirement_min_length_gate(engine):
    """REQ-002 — 50자 이상 시 통과"""
    state = create_initial_state("CR-TEST", CRType.NEW_DEV)

    # 짧음 → REQ-002 실패
    state["requirement_result"] = RequirementResult(
        structured_requirement  = "짧음",
        clarification_questions = [],
        similar_cr_ids          = [],
        related_docs            = [],
        confirmed               = True,
    )
    result = engine.check(state)
    assert "REQ-002" in result.failed_items

    # 50자 이상 → REQ-002 통과
    state["requirement_result"].structured_requirement = "요구사항 상세 내용 " * 6  # 60자+
    result2 = engine.check(state)
    assert "REQ-002" not in result2.failed_items
    print("✅ REQ-002 (최소 길이) 게이트 정상")


def test_impact_analysis_done_gate(engine):
    """IMP-001 — impact_result 존재 시 통과"""
    state  = create_initial_state("CR-TEST", CRType.NEW_DEV)
    result = engine.check(state)
    assert "IMP-001" in result.failed_items

    state["impact_result"] = ImpactAnalysisResult(
        affected_tables           = ["TB_TEST"],
        affected_programs         = [],
        has_db_schema_change      = False,
        oracle_consistency_issues = [],
        impact_summary            = "영향도 요약 테스트입니다",
    )
    result2 = engine.check(state)
    assert "IMP-001" not in result2.failed_items
    print("✅ IMP-001 (영향도 분석 결과 존재) 게이트 정상")


def test_artifact_confirmed_gate(engine):
    """ART-004 — confirmed=True 시 통과"""
    state = create_initial_state("CR-TEST", CRType.NEW_DEV)

    state["artifact_result"] = ArtifactResult(
        requirement_doc     = "요구사항 분석서 내용",
        impact_doc          = "영향도 분석서 내용",
        test_definition_doc = "테스트 정의서 내용",
        confluence_pages    = {},
        confirmed           = False,
    )
    result = engine.check(state)
    assert "ART-004" in result.failed_items

    state["artifact_result"].confirmed = True
    result2 = engine.check(state)
    assert "ART-004" not in result2.failed_items
    print("✅ ART-004 (산출물 담당자 확인) 게이트 정상")


def test_gate_version_in_result(engine):
    """GateCheckResult에 gate_version 포함 — T1-4 버전"""
    state  = create_initial_state("CR-TEST", CRType.NEW_DEV)
    result = engine.check(state)
    assert result.gate_version == "1.2.0"
    print("✅ gate_version 정상")


def test_gate_checked_at_is_iso(engine):
    """GateCheckResult checked_at이 ISO 형식"""
    state  = create_initial_state("CR-TEST", CRType.NEW_DEV)
    result = engine.check(state)
    datetime.datetime.fromisoformat(result.checked_at)
    print("✅ checked_at ISO 형식 정상")


def test_deploy_all_attachments_gate(engine):
    """DEP-003 — all_attachments_ready=True 시 통과"""
    state = create_initial_state("CR-TEST", CRType.NEW_DEV)
    state["deploy_result"] = DeployResult(
        pr_body_draft           = "PR 본문",
        test_request_mail_draft = "메일 내용",
        release_checklist       = {},
        all_attachments_ready   = False,
    )
    result = engine.check(state)
    assert "DEP-003" in result.failed_items

    state["deploy_result"].all_attachments_ready = True
    result2 = engine.check(state)
    assert "DEP-003" not in result2.failed_items
    print("✅ DEP-003 (Release 첨부물 완비) 게이트 정상")
