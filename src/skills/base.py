# src/skills/base.py
"""
프로그램 개발 전주기 지원 AI Agent — Skill 표준 인터페이스 (T1-3)

모든 T3 Skill이 구현해야 하는 BaseSkill ABC와 SkillResult 데이터 모델을 정의한다.
LangGraph 노드 함수는 BaseSkill.run()을 호출하는 얇은 래퍼로 구성된다.
"""
from __future__ import annotations

import logging
import time
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

from src.agent.state import AgentState, SkillExecutionLog, StepName

logger = logging.getLogger(__name__)


# ── SkillStatus ───────────────────────────────────────────────────────────────


class SkillStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"   # 일부 성공 (재시도 불필요)
    RETRY   = "retry"     # 재시도 권장
    FAILED  = "failed"    # 실패 (에스컬레이션 필요)


# ── SkillResult ───────────────────────────────────────────────────────────────


@dataclass
class SkillResult:
    """
    모든 Skill의 반환 타입.
    state_updates: AgentState에 병합할 dict
    """
    status:        SkillStatus
    state_updates: Dict[str, Any]
    message:       str   = ""
    confidence:    float = 1.0     # 0.0 ~ 1.0 (낮으면 에스컬레이션)
    elapsed_ms:    float = 0.0


# ── BaseSkill ABC ─────────────────────────────────────────────────────────────


class BaseSkill(ABC):
    """
    프로그램 개발 전주기 지원 AI Agent — Skill 표준 인터페이스.

    구현 규칙:
    1. execute() 내에서 외부 시스템 쓰기 작업 금지 (읽기만 허용)
    2. 반환값은 SkillResult — state_updates에 담당 필드만 포함
    3. 오류 발생 시 예외를 던지지 말고 SkillResult(status=FAILED) 반환
    4. 신뢰도(confidence) 0.5 미만 시 에스컬레이션 처리됨
    """

    # 서브클래스에서 반드시 정의
    skill_name:  str      = ""
    step:        StepName = StepName.INIT
    max_retries: int      = 2

    def __init__(self):
        # 환경 변수로 Mock 사용 여부 결정 (테스트 지원)
        import os
        use_mock = os.environ.get("USE_MOCK_CONNECTORS", "false").lower() == "true"

        if use_mock:
            self._llm        = None
            self._embeddings = None
            self._connectors = None
        else:
            try:
                from src.connectors.factory import ConnectorFactory
                from src.llm.aiPro_client import AiProChatModel
                from src.llm.embedding_client import AiProEmbeddings
                self._llm        = AiProChatModel()
                self._embeddings = AiProEmbeddings()
                self._connectors = ConnectorFactory()
            except Exception as e:
                logger.warning(f"[{self.skill_name}] 커넥터 초기화 실패 (Mock 사용): {e}")
                self._llm        = None
                self._embeddings = None
                self._connectors = None

    @abstractmethod
    def execute(self, state: AgentState) -> SkillResult:
        """
        핵심 Skill 로직. 서브클래스에서 구현.

        Args:
            state: 현재 AgentState (읽기 전용으로 취급)

        Returns:
            SkillResult: state_updates에 변경할 필드만 포함
        """
        ...

    def run(self, state: AgentState) -> dict:
        """
        LangGraph 노드 함수에서 호출하는 진입점.
        - 실행 시간 측정
        - 재시도 로직
        - 신뢰도 기반 에스컬레이션
        - 감사 로그 기록
        """
        started_at = _now_iso()
        start_time = time.monotonic()
        result: Optional[SkillResult] = None

        for attempt in range(self.max_retries + 1):
            try:
                result = self.execute(state)
                if result.status != SkillStatus.RETRY:
                    break
                logger.warning(f"[{self.skill_name}] Retry {attempt + 1}/{self.max_retries}")
            except Exception as e:
                logger.error(
                    f"[{self.skill_name}] Exception: {e}\n{traceback.format_exc()}"
                )
                result = SkillResult(
                    status        = SkillStatus.FAILED,
                    state_updates = {},
                    message       = str(e),
                    confidence    = 0.0,
                )
                break

        elapsed_ms = (time.monotonic() - start_time) * 1000
        ended_at   = _now_iso()

        if result is None:
            result = SkillResult(
                status        = SkillStatus.FAILED,
                state_updates = {},
                message       = "재시도 초과",
                confidence    = 0.0,
            )

        result.elapsed_ms = elapsed_ms

        # 신뢰도 기반 에스컬레이션 처리
        if result.confidence < 0.5:
            result.state_updates["hitl_status"]   = "waiting"
            result.state_updates["hitl_point"]    = f"{self.skill_name}_low_confidence"
            result.state_updates["hitl_feedback"] = None
            logger.warning(
                f"[{self.skill_name}] 저신뢰도 에스컬레이션: {result.confidence:.2f}"
            )

        # 오류 상태 기록
        if result.status == SkillStatus.FAILED:
            result.state_updates["error_step"]    = self.step
            result.state_updates["error_message"] = result.message

        # 감사 로그 추가
        log_entry = SkillExecutionLog(
            step           = self.step,
            started_at     = started_at,
            ended_at       = ended_at,
            elapsed_ms     = elapsed_ms,
            success        = result.status in (SkillStatus.SUCCESS, SkillStatus.PARTIAL),
            error          = result.message if result.status == SkillStatus.FAILED else None,
            input_summary  = _summarize_state_input(state, self.step),
            output_summary = result.message[:200],
        )
        existing_logs = list(state.get("execution_logs", []))
        result.state_updates["execution_logs"] = existing_logs + [log_entry]

        return result.state_updates


# ── 유틸리티 ──────────────────────────────────────────────────────────────────


def _now_iso() -> str:
    import datetime
    return datetime.datetime.now().isoformat()


def _summarize_state_input(state: AgentState, step: StepName) -> str:
    """감사 로그용 입력 요약 — 민감정보 마스킹"""
    cr_id  = state.get("cr_id", "")
    title  = ""
    cr_info = state.get("cr_info")
    if cr_info:
        raw_title = getattr(cr_info, "title", "")
        title = raw_title[:50] if raw_title else ""
    return f"cr_id={cr_id}, step={step}, title={title}"
