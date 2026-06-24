# src/gate/mock/scenarios.py
"""
Mock 시나리오 정의 (T1-4)

사외 환경에서 검증할 8가지 대표 시나리오를 정의한다.
각 시나리오는 _full_state()에서 특정 필드를 변경하여 생성한다.
"""
from __future__ import annotations

import datetime
from enum import Enum
from typing import Any, Dict


class Scenario(str, Enum):
    ALL_PASS               = "all_pass"               # 모든 조건 충족 → 게이트 통과
    MISSING_REQUIREMENT    = "missing_requirement"    # 요구사항 미완료
    SHORT_REQUIREMENT      = "short_requirement"      # 요구사항 길이 부족
    ORACLE_ISSUE           = "oracle_issue"           # Oracle 정합성 이슈
    MISSING_ARTIFACT       = "missing_artifact"       # 산출물 미생성
    ARTIFACT_NOT_CONFIRMED = "artifact_not_confirmed" # 산출물 담당자 미확인
    MISSING_PROGRAM_MASTER = "missing_program_master" # 프로그램마스터 초안 미생성
    DEPLOY_NOT_READY       = "deploy_not_ready"       # 배포 준비 미완료


class MockScenarioFactory:
    """시나리오 이름에 따라 Mock AgentState dict 생성"""

    def build(self, scenario: Scenario) -> Dict[str, Any]:
        builder = getattr(self, f"_build_{scenario.value.replace('-', '_')}", None)
        if builder is None:
            raise ValueError(f"알 수 없는 시나리오: {scenario}")
        return builder()

    # ── 공통 완전 완료 State ────────────────────────────────────────────

    @staticmethod
    def _full_state() -> Dict[str, Any]:
        """모든 단계가 완료된 기준 State"""

        class _Obj:
            """dict를 속성 접근으로 사용하기 위한 헬퍼"""
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)

            def get(self, key, default=None):
                return getattr(self, key, default)

        return {
            "cr_id":   "CR-2026-MOCK-001",
            "cr_type": "new_dev",

            "requirement_result": _Obj(
                structured_requirement=(
                    "선박 수주 현황 조회 화면 개발. 수주번호, 선박명, 발주처, 납기일 기본 정보를 표시하며 "
                    "부서별 필터 기능을 제공한다."
                ),
                clarification_questions=[
                    "납기일 기준이 계약일인지 실제 납기일인지 확인 필요",
                    "부서 코드 체계 확인 필요",
                ],
                similar_cr_ids=["CR-2026-0312", "CR-2025-0198"],
                related_docs=["https://confluence.internal/pages/12345"],
                confirmed=True,
            ),

            "impact_result": _Obj(
                affected_tables=["SHIP_ORDER", "DEPT_MASTER"],
                affected_programs=["PKG_SHIP_ORDER", "V_SHIP_STATUS"],
                has_db_schema_change=False,
                oracle_consistency_issues=[],   # 이슈 없음
                impact_summary=(
                    "SHIP_ORDER 테이블 조회, DEPT_MASTER 필터 조건 추가. "
                    "기존 PKG_SHIP_ORDER 패키지 재사용 가능."
                ),
            ),

            "estimation_result": _Obj(
                estimated_screens=2,
                estimated_hours=24.0,
                db_extra_hours=0.0,
                basis_cr_ids=["CR-2026-0312"],
                confidence="medium",
                breakdown={"분석": 4.0, "개발": 16.0, "테스트": 4.0},
            ),

            "task_breakdown_result": _Obj(
                tasks=[
                    {"id": "T1", "title": "요구사항 분석서 작성", "done": False},
                    {"id": "T2", "title": "화면 설계", "done": False},
                    {"id": "T3", "title": "코드 개발", "done": False},
                    {"id": "T4", "title": "단위 테스트", "done": False},
                ],
                checklist_url="https://confluence.internal/pages/99999",
            ),

            "artifact_result": _Obj(
                requirement_doc="# 요구사항 분석서\n## 개요\n선박 수주 현황 조회 화면...",
                impact_doc="# 영향도 분석서\n## 영향 테이블\n- SHIP_ORDER: 조회 전용...",
                test_definition_doc="# 테스트 정의서\n## 테스트 케이스\nTC-001: 수주 목록 조회...",
                confluence_pages={
                    "requirement": "https://conf/123",
                    "impact":      "https://conf/124",
                },
                confirmed=True,
            ),

            "registration_result": _Obj(
                jsm_draft={"summary": "[NEW_DEV] 선박 수주 현황 조회", "issuetype": "새 기능"},
                program_master_draft={
                    "program_id":   "SHI_SHIP_ORDER_01",
                    "program_name": "선박 수주 현황 조회",
                },
                table_master_drafts=[],
                unregistered_terms=["납기일"],
                term_drafts=[{"term_ko": "납기일", "term_en": "delivery_date"}],
            ),

            "gate_result": None,

            "deploy_result": _Obj(
                pr_body_draft="## 변경 개요\n선박 수주 현황 조회 화면 신규 개발...",
                test_request_mail_draft="안녕하세요. 현업 테스트 요청드립니다...",
                release_checklist={
                    "요구사항 분석서": True,
                    "테스트 정의서":   True,
                    "현업 확인 메일":  True,
                },
                all_attachments_ready=True,
                pr_url="https://github.internal/org/shic-app/pull/42",
            ),
        }

    # ── 시나리오별 State ─────────────────────────────────────────────

    def _build_all_pass(self) -> Dict[str, Any]:
        """모든 조건 충족 — 게이트 통과"""
        return self._full_state()

    def _build_missing_requirement(self) -> Dict[str, Any]:
        """요구사항 구체화 미실행"""
        state = self._full_state()
        state["requirement_result"] = None   # Skill 미실행
        return state

    def _build_short_requirement(self) -> Dict[str, Any]:
        """요구사항 길이 부족 (50자 미만)"""
        state = self._full_state()
        state["requirement_result"].structured_requirement = "선박 수주 조회"  # 9자
        return state

    def _build_oracle_issue(self) -> Dict[str, Any]:
        """Oracle 정합성 이슈 발생"""
        state = self._full_state()
        state["impact_result"].oracle_consistency_issues = [
            "SHIP_ORDER 테이블: 테이블마스터 미등록",
            "DEPT_MASTER 테이블: Oracle 컬럼 수 불일치",
        ]
        return state

    def _build_missing_artifact(self) -> Dict[str, Any]:
        """산출물 초안 미생성"""
        state = self._full_state()
        state["artifact_result"].impact_doc          = None   # 영향도 분석서 미생성
        state["artifact_result"].test_definition_doc = None   # 테스트 정의서 미생성
        state["artifact_result"].confirmed           = False
        return state

    def _build_artifact_not_confirmed(self) -> Dict[str, Any]:
        """산출물 생성됐으나 담당자 미확인"""
        state = self._full_state()
        state["artifact_result"].confirmed = False  # HITL 미완료
        return state

    def _build_missing_program_master(self) -> Dict[str, Any]:
        """프로그램마스터 등록 초안 미생성"""
        state = self._full_state()
        state["registration_result"].program_master_draft = None
        return state

    def _build_deploy_not_ready(self) -> Dict[str, Any]:
        """배포 준비 미완료"""
        state = self._full_state()
        state["deploy_result"].all_attachments_ready = False
        state["deploy_result"].pr_url                = None
        return state
