# tests/gate/test_engine.py
"""
게이트 Rule Engine 전체 테스트 (T1-4)
GATE_ENV=mock으로 실행 — 사내 시스템 연결 불필요.
"""
import os

import pytest

os.environ["GATE_ENV"]              = "mock"
os.environ["USE_MOCK_CONNECTORS"]   = "true"

from src.gate.engine import GateCheckResult, GateEngine
from src.gate.loader import GateRulesLoader
from src.gate.mock.scenarios import MockScenarioFactory, Scenario
from src.gate.mock.simulator import GateMockSimulator
from src.gate.reporter import GateReporter


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def engine():
    return GateEngine()


@pytest.fixture
def sim():
    return GateMockSimulator()


@pytest.fixture
def factory():
    return MockScenarioFactory()


# ── 시나리오 기반 통합 테스트 ─────────────────────────────────────────────────


def test_scenario_all_pass(sim):
    """ALL_PASS 시나리오 — 모든 필수 규칙 통과"""
    result = sim.run_scenario(Scenario.ALL_PASS)
    assert result.passed, (
        f"전체 통과 시나리오에서 실패: {[r.rule_id for r in result.failed_required]}"
    )
    assert isinstance(result, GateCheckResult)
    print(f"✅ all_pass: {result.summary}")


def test_scenario_missing_requirement(sim):
    """MISSING_REQUIREMENT — REQ-001 실패 (requirement_result=None)"""
    result = sim.run_scenario(Scenario.MISSING_REQUIREMENT)
    assert not result.passed
    failed_ids = [r.rule_id for r in result.failed_required]
    assert "REQ-001" in failed_ids, f"REQ-001 실패 예상, 실제: {failed_ids}"
    print(f"✅ missing_requirement: {result.summary}")


def test_scenario_short_requirement(sim):
    """SHORT_REQUIREMENT — REQ-002 실패 (요구사항 50자 미만)"""
    result = sim.run_scenario(Scenario.SHORT_REQUIREMENT)
    assert not result.passed
    failed_ids = [r.rule_id for r in result.failed_required]
    assert "REQ-002" in failed_ids, f"REQ-002 실패 예상, 실제: {failed_ids}"
    print(f"✅ short_requirement: {result.summary}")


def test_scenario_oracle_issue(sim):
    """ORACLE_ISSUE — IMP-004 실패 (정합성 이슈 있음)"""
    result = sim.run_scenario(Scenario.ORACLE_ISSUE)
    assert not result.passed
    failed_ids = [r.rule_id for r in result.failed_required]
    assert "IMP-004" in failed_ids, f"IMP-004 실패 예상, 실제: {failed_ids}"
    print(f"✅ oracle_issue: {result.summary}")


def test_scenario_missing_artifact(sim):
    """MISSING_ARTIFACT — ART-* 실패 (산출물 미생성)"""
    result = sim.run_scenario(Scenario.MISSING_ARTIFACT)
    assert not result.passed
    failed_ids = [r.rule_id for r in result.failed_required]
    assert any(r.startswith("ART-") for r in failed_ids), (
        f"ART-* 실패 예상, 실제: {failed_ids}"
    )
    print(f"✅ missing_artifact: {result.summary}")


def test_scenario_artifact_not_confirmed(sim):
    """ARTIFACT_NOT_CONFIRMED — ART-004 실패 (HITL 미완료)"""
    result = sim.run_scenario(Scenario.ARTIFACT_NOT_CONFIRMED)
    assert not result.passed
    failed_ids = [r.rule_id for r in result.failed_required]
    assert "ART-004" in failed_ids, (
        f"ART-004 실패 예상 (HITL 미완료), 실제: {failed_ids}"
    )
    print(f"✅ artifact_not_confirmed: {result.summary}")


def test_scenario_missing_program_master(sim):
    """MISSING_PROGRAM_MASTER — REG-002 실패 (프로그램마스터 초안 없음)"""
    result = sim.run_scenario(Scenario.MISSING_PROGRAM_MASTER)
    assert not result.passed
    failed_ids = [r.rule_id for r in result.failed_required]
    assert "REG-002" in failed_ids, f"REG-002 실패 예상, 실제: {failed_ids}"
    print(f"✅ missing_program_master: {result.summary}")


def test_scenario_deploy_not_ready(sim):
    """DEPLOY_NOT_READY — DEP-* 실패 (배포 준비 미완료)"""
    result = sim.run_scenario(Scenario.DEPLOY_NOT_READY)
    assert not result.passed
    failed_ids = [r.rule_id for r in result.failed_required]
    assert any(r.startswith("DEP-") for r in failed_ids), (
        f"DEP-* 실패 예상, 실제: {failed_ids}"
    )
    print(f"✅ deploy_not_ready: {result.summary}")


# ── 단계별 검사 테스트 ─────────────────────────────────────────────────────────


def test_step_check_requirement_only(sim):
    """단계별 검사: requirement 단계만"""
    result = sim.run_scenario(Scenario.ALL_PASS, step="requirement")
    assert result.passed
    assert all(r.step == "requirement" for r in result.passed_rules)
    assert result.total_rules == 4  # REQ-001~004
    print(f"✅ 단계별 검사 (requirement): {result.summary}")


def test_step_check_deploy_only(sim):
    """단계별 검사: deploy 단계만"""
    result = sim.run_scenario(Scenario.ALL_PASS, step="deploy")
    assert result.passed
    assert result.total_rules == 4  # DEP-001~004
    print(f"✅ 단계별 검사 (deploy): {result.summary}")


# ── 규칙 수 검증 ───────────────────────────────────────────────────────────────


def test_rule_count(engine):
    """gate_rules.yaml의 규칙 수 기준 검증"""
    loader = GateRulesLoader()
    rules  = loader.get_rules()
    assert len(rules) >= 15, f"규칙 수 부족: {len(rules)}개 (최소 15개 필요)"
    required_count = sum(1 for r in rules if r.get("required", True))
    assert required_count >= 10, f"필수 규칙 수 부족: {required_count}개"
    print(f"✅ 전체 규칙 {len(rules)}개, 필수 {required_count}개")


def test_rule_ids_unique(engine):
    """모든 규칙 id가 고유함을 검증"""
    loader = GateRulesLoader()
    rules  = loader.get_rules()
    ids    = [r.get("id") for r in rules]
    assert len(ids) == len(set(ids)), f"중복 규칙 id 존재: {ids}"
    print(f"✅ 규칙 id 고유성 확인: {len(ids)}개")


# ── Config 핫리로드 테스트 ─────────────────────────────────────────────────────


def test_config_reload(engine):
    """Config 강제 리로드 후 동일 버전 반환"""
    version1 = engine._loader.get_version()
    version2 = engine.reload_config()
    assert version1 == version2   # 파일 미변경 시 동일 버전
    assert version1 == "1.2.0"
    print(f"✅ Config 리로드: v{version1} → v{version2}")


# ── 리포터 테스트 ──────────────────────────────────────────────────────────────


def test_reporter_failed_guidance(sim):
    """미충족 안내 메시지 — 실패 규칙 ID 포함"""
    result   = sim.run_scenario(Scenario.ORACLE_ISSUE)
    guidance = sim._engine.get_failed_guidance(result)
    assert "IMP-004" in guidance
    assert "처리한 후" in guidance
    print(f"✅ 미충족 안내 메시지 생성 완료")


def test_reporter_json_format(sim):
    """JSON 포맷 — 구조 및 실패 목록 확인"""
    result   = sim.run_scenario(Scenario.MISSING_REQUIREMENT)
    reporter = GateReporter()
    json_out = reporter.format_json(result)
    assert "passed" in json_out
    assert "failed" in json_out
    assert "warnings" in json_out
    assert len(json_out["failed"]) > 0
    assert json_out["passed"] is False
    print(f"✅ JSON 포맷: {json_out['summary']}")


def test_reporter_all_pass_guidance(sim):
    """전체 통과 시 안내 메시지 — 성공 메시지 출력"""
    result   = sim.run_scenario(Scenario.ALL_PASS)
    guidance = sim._engine.get_failed_guidance(result)
    assert "모든 필수 조건" in guidance
    print(f"✅ 전체 통과 안내 메시지: {guidance[:30]}")


# ── GateCheckResult 속성 테스트 ────────────────────────────────────────────────


def test_gate_check_result_properties(sim):
    """GateCheckResult 호환 속성 검증"""
    result = sim.run_scenario(Scenario.ALL_PASS)
    # AgentState GateResult 호환 속성
    assert isinstance(result.passed_items, list)
    assert isinstance(result.failed_items, list)
    assert isinstance(result.gate_version, str)
    assert result.gate_version == "1.2.0"
    print(f"✅ GateCheckResult 호환 속성 확인")
