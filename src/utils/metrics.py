# src/utils/metrics.py
"""
완료 이력 기록 유틸리티 (T1-3)

CR 처리 완료 시 공수·산출물·재작업 여부를 기록한다.
현재는 logging 기반으로 구현하며, T2/T3에서 DB 저장으로 교체 예정.
"""
from __future__ import annotations

import datetime
import logging
from typing import Any, Dict

from src.agent.state import AgentState

logger = logging.getLogger(__name__)


def record_completion(state: AgentState) -> Dict[str, Any]:
    """
    CR 처리 완료 이력을 기록한다.

    Args:
        state: 최종 AgentState (done 노드에서 호출)

    Returns:
        기록된 메트릭 딕셔너리
    """
    cr_id      = state.get("cr_id", "UNKNOWN")
    cr_type    = state.get("cr_type")
    step_count = state.get("step_count", 0)
    gate_attempts = state.get("gate_attempts", 0)

    # 공수 메트릭
    estimation = state.get("estimation_result")
    estimated_hours = getattr(estimation, "estimated_hours", 0.0) if estimation else 0.0

    # 산출물 메트릭
    artifacts       = state.get("artifacts", {})
    artifact_count  = len(artifacts)

    # 재작업 여부 (게이트 재시도 2회 이상 or HITL rejected 기록)
    rework_needed = gate_attempts >= 2

    # 실행 로그 통계
    logs        = state.get("execution_logs", [])
    total_ms    = sum(getattr(log, "elapsed_ms", 0.0) for log in logs)
    failed_steps = [
        getattr(log, "step", "?")
        for log in logs
        if not getattr(log, "success", True)
    ]

    metrics = {
        "cr_id":            cr_id,
        "cr_type":          cr_type.value if hasattr(cr_type, "value") else cr_type,
        "completed_at":     datetime.datetime.now().isoformat(),
        "step_count":       step_count,
        "gate_attempts":    gate_attempts,
        "estimated_hours":  estimated_hours,
        "artifact_count":   artifact_count,
        "rework_needed":    rework_needed,
        "total_elapsed_ms": round(total_ms, 2),
        "failed_steps":     [str(s) for s in failed_steps],
    }

    logger.info(
        "CR 처리 완료",
        extra=metrics,
    )
    return metrics
