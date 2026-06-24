# src/agent/state.py
"""
프로그램 개발 전주기 지원 AI Agent — 전역 상태 스키마 (T1-3)

AgentState는 Agent의 모든 정보를 담는 단일 진실 공급원(Single Source of Truth).
Skill은 이 State를 읽고 업데이트하며, LangGraph가 노드 간 전달을 자동 관리한다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Annotated, Any, Dict, List, Optional

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


# ── Enum 정의 ─────────────────────────────────────────────────────────────────


class CRType(str, Enum):
    """CR(Change Request) 유형"""
    NEW_DEV        = "new_dev"         # 신규 화면 개발
    FEATURE_CHANGE = "feature_change"  # 기능 변경
    DB_CHANGE      = "db_change"       # DB 스키마 변경


class StepName(str, Enum):
    """Agent 처리 단계 이름 — 게이트·로그에서 참조"""
    INIT             = "init"
    REQUIREMENT      = "requirement"       # 요구사항 구체화
    IMPACT_ANALYSIS  = "impact_analysis"   # 영향도 분석
    ESTIMATION       = "estimation"        # 공수 산정
    TASK_BREAKDOWN   = "task_breakdown"    # Task 분해
    ARTIFACT         = "artifact"          # 산출물 초안 생성
    REGISTRATION     = "registration"      # 시스템 등록 지원
    GATE_CHECK       = "gate_check"        # 관리 포인트 게이트
    DEPLOY           = "deploy"            # 배포 준비 지원
    DONE             = "done"              # 완료


class HITLStatus(str, Enum):
    """HITL(Human-In-The-Loop) 중단점 상태"""
    NOT_REACHED = "not_reached"
    WAITING     = "waiting"    # 담당자 확인 대기 중
    APPROVED    = "approved"   # 담당자 승인
    REJECTED    = "rejected"   # 담당자 반려 → 재수행


# ── 하위 데이터 모델 ──────────────────────────────────────────────────────────


@dataclass
class CRInfo:
    """두드림 CR 원본 정보"""
    cr_id:            str
    title:            str
    description:      str
    cr_type:          CRType
    requester:        str
    assignee:         str
    created_at:       str
    affected_systems: List[str]       = field(default_factory=list)
    tags:             List[str]       = field(default_factory=list)
    raw_data:         Dict[str, Any]  = field(default_factory=dict)


@dataclass
class RequirementResult:
    """요구사항 구체화 Skill 결과"""
    structured_requirement:  str         # 구체화된 요구사항 본문
    clarification_questions: List[str]   # 담당자 확인 질문 목록
    similar_cr_ids:          List[str]   # 참조한 유사 CR ID
    related_docs:            List[str]   # 참조한 Confluence 문서 URL
    confirmed:               bool = False  # 담당자 확인 완료 여부


@dataclass
class ImpactAnalysisResult:
    """영향도 분석 Skill 결과"""
    affected_tables:           List[str]  # 영향받는 테이블 목록
    affected_programs:         List[str]  # 영향받는 프로그램 목록
    has_db_schema_change:      bool       # DB 스키마 변경 포함 여부
    oracle_consistency_issues: List[str]  # Oracle 정합성 이슈
    impact_summary:            str        # 영향도 요약 텍스트


@dataclass
class EstimationResult:
    """공수 산정 Skill 결과"""
    estimated_screens: int              # 화면 본수 추정
    estimated_hours:   float            # 총 개발 시간 추정
    db_extra_hours:    float            # DB 작업 추가 공수
    basis_cr_ids:      List[str]        # 산정 근거 유사 CR ID
    confidence:        str              # "high" | "medium" | "low"
    breakdown:         Dict[str, float] # {"분석": 4.0, "개발": 16.0, "테스트": 4.0}


@dataclass
class TaskBreakdownResult:
    """Task 분해 Skill 결과"""
    tasks:         List[Dict[str, Any]]  # [{id, title, description, estimated_hours, done}]
    checklist_url: Optional[str]         # Confluence 저장 URL


@dataclass
class ArtifactResult:
    """산출물 초안 Skill 결과"""
    requirement_doc:    Optional[str]       # 요구사항 분석서 (마크다운/HTML)
    impact_doc:         Optional[str]       # 영향도 분석서
    test_definition_doc: Optional[str]     # 테스트 정의서
    confluence_pages:   Dict[str, str]     # {doc_type: page_url}
    confirmed:          bool = False


@dataclass
class RegistrationResult:
    """시스템 등록 지원 Skill 결과"""
    jsm_draft:            Optional[Dict[str, Any]]    # JSM 등록 초안
    program_master_draft: Optional[Dict[str, Any]]    # 프로그램마스터 초안
    table_master_drafts:  List[Dict[str, Any]]        # 테이블마스터 초안 목록
    unregistered_terms:   List[str]                   # 미등록 용어 목록
    term_drafts:          List[Dict[str, Any]]        # 용어 등록 초안


@dataclass
class GateResult:
    """관리 포인트 게이트 결과"""
    passed:       bool
    checked_at:   str
    passed_items: List[str]  # 통과한 점검 항목
    failed_items: List[str]  # 미충족 항목 (빈 리스트 = 전체 통과)
    gate_version: str        # gate_rules.yaml 버전


@dataclass
class DeployResult:
    """배포 준비 지원 Skill 결과"""
    pr_body_draft:           Optional[str]        # PR 본문 초안
    test_request_mail_draft: Optional[str]        # 현업 테스트 요청 메일 초안
    release_checklist:       Dict[str, bool]      # {항목: 완료여부}
    all_attachments_ready:   bool                 # Release 첨부물 3종 완비 여부
    pr_url:                  Optional[str] = None  # PR 생성 후 URL (HITL 승인 후 채움)


@dataclass
class SkillExecutionLog:
    """Skill 실행 감사 로그 단건"""
    step:           StepName
    started_at:     str
    ended_at:       str
    elapsed_ms:     float
    success:        bool
    error:          Optional[str]
    input_summary:  str   # LLM 전달 전 민감정보 마스킹된 입력 요약
    output_summary: str   # 출력 요약


# ── AgentState TypedDict (LangGraph 핵심) ────────────────────────────────────


class AgentState(TypedDict):
    """
    프로그램 개발 전주기 지원 AI Agent 전역 상태.

    LangGraph가 노드(Skill) 실행 시 이 TypedDict를 전달하고,
    각 노드가 반환한 업데이트를 누적·병합한다.

    ⚠️  규칙:
    - Skill은 자신이 담당하는 필드만 업데이트한다
    - messages 필드는 add_messages reducer로 누적 (덮어쓰지 않음)
    - cr_info, cr_id, cr_type 은 초기 입력 후 변경 금지
    """

    # ── 기본 메시지 이력 (LangGraph 표준) ──────────────────────────────────────
    messages: Annotated[List[BaseMessage], add_messages]

    # ── CR 기본 정보 (초기 설정 후 불변) ───────────────────────────────────────
    cr_id:   str
    cr_type: CRType
    cr_info: Optional[CRInfo]

    # ── 처리 단계 추적 ──────────────────────────────────────────────────────────
    current_step:    StepName
    completed_steps: List[StepName]
    step_count:      int          # 무한루프 방지 카운터

    # ── HITL 상태 ───────────────────────────────────────────────────────────────
    hitl_status:   HITLStatus
    hitl_point:    Optional[str]  # 현재 중단된 HITL 지점 이름
    hitl_feedback: Optional[str]  # 담당자 피드백 메시지

    # ── Skill 결과 누적 ─────────────────────────────────────────────────────────
    requirement_result:    Optional[RequirementResult]
    impact_result:         Optional[ImpactAnalysisResult]
    estimation_result:     Optional[EstimationResult]
    task_breakdown_result: Optional[TaskBreakdownResult]
    artifact_result:       Optional[ArtifactResult]
    registration_result:   Optional[RegistrationResult]
    gate_result:           Optional[GateResult]
    deploy_result:         Optional[DeployResult]

    # ── 게이트 이력 (재시도 추적) ───────────────────────────────────────────────
    gate_attempts: int           # 게이트 재시도 횟수
    gate_history:  List[GateResult]

    # ── 오류 상태 ───────────────────────────────────────────────────────────────
    error_step:    Optional[StepName]  # 오류 발생 단계
    error_message: Optional[str]
    retry_count:   int

    # ── 감사 로그 ───────────────────────────────────────────────────────────────
    execution_logs: List[SkillExecutionLog]

    # ── 최종 산출물 레지스트리 ──────────────────────────────────────────────────
    artifacts: Dict[str, Any]     # {artifact_type: content_or_url}


def create_initial_state(
    cr_id:   str,
    cr_type: CRType,
    cr_info: Optional[CRInfo] = None,
) -> AgentState:
    """
    AgentState 초기값 생성 헬퍼.
    두드림에서 CR 수신 시 이 함수로 초기 State를 만든다.

    사용 예:
        state = create_initial_state(
            cr_id="CR-2026-0001",
            cr_type=CRType.NEW_DEV,
            cr_info=CRInfo(...),
        )
        result = app.invoke(state)
    """
    from langchain_core.messages import HumanMessage

    return AgentState(
        messages=[HumanMessage(content=f"CR 처리 시작: {cr_id}")],
        cr_id=cr_id,
        cr_type=cr_type,
        cr_info=cr_info,
        current_step=StepName.INIT,
        completed_steps=[],
        step_count=0,
        hitl_status=HITLStatus.NOT_REACHED,
        hitl_point=None,
        hitl_feedback=None,
        requirement_result=None,
        impact_result=None,
        estimation_result=None,
        task_breakdown_result=None,
        artifact_result=None,
        registration_result=None,
        gate_result=None,
        deploy_result=None,
        gate_attempts=0,
        gate_history=[],
        error_step=None,
        error_message=None,
        retry_count=0,
        execution_logs=[],
        artifacts={},
    )
