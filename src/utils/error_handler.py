# src/utils/error_handler.py
"""
오류 처리 및 에스컬레이션 유틸리티 (T1-3)

Skill별 재시도 정책과 신뢰도 기반 에스컬레이션 임계값을 정의한다.
"""
from __future__ import annotations

import logging
from typing import Dict

from src.agent.state import AgentState, StepName

logger = logging.getLogger(__name__)

# ── 재시도 정책: Skill별 최대 재시도 횟수 ─────────────────────────────────────
RETRY_POLICY: Dict[StepName, int] = {
    StepName.REQUIREMENT:     2,
    StepName.IMPACT_ANALYSIS: 3,  # Oracle 일시 장애 대비
    StepName.ESTIMATION:      2,
    StepName.TASK_BREAKDOWN:  1,
    StepName.ARTIFACT:        2,
    StepName.REGISTRATION:    2,
    StepName.GATE_CHECK:      0,  # 게이트는 재시도 없음 (Config Rule 기반)
    StepName.DEPLOY:          1,
}

# ── 에스컬레이션 임계값 (신뢰도) ─────────────────────────────────────────────
CONFIDENCE_THRESHOLD: float = 0.5


def should_escalate(confidence: float) -> bool:
    """신뢰도가 임계값 미만이면 HITL 에스컬레이션을 권장한다."""
    return confidence < CONFIDENCE_THRESHOLD


def build_error_context(state: AgentState) -> dict:
    """에스컬레이션 알림용 컨텍스트 생성"""
    return {
        "cr_id":         state.get("cr_id"),
        "error_step":    state.get("error_step"),
        "error_message": state.get("error_message"),
        "step_count":    state.get("step_count"),
        "retry_count":   state.get("retry_count"),
        "completed":     [s.value for s in state.get("completed_steps", [])],
    }


def log_error_context(state: AgentState) -> None:
    """에러 컨텍스트를 로깅한다."""
    ctx = build_error_context(state)
    logger.error(
        "Agent 오류 발생",
        extra=ctx,
    )
