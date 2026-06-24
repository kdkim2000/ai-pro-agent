# src/skills/s07_gate.py
"""
관리 포인트 게이트 Skill (T1-4 업데이트)

GateEngine을 호출하여 Config 규칙 기반 게이트 판별을 수행한다.
T1-4에서 GateEngine이 GateCheckResult를 반환하도록 변경되었으므로,
AgentState에 저장하는 GateResult 형식으로 변환한다.
"""
from __future__ import annotations

import datetime

from src.agent.state import AgentState, GateResult, StepName
from src.gate.loader import get_gate_engine
from src.skills.base import BaseSkill, SkillResult, SkillStatus


class GateSkill(BaseSkill):
    skill_name  = "gate_skill"
    step        = StepName.GATE_CHECK
    max_retries = 0  # 게이트는 재시도 없음 (Config Rule 기반)

    def execute(self, state: AgentState) -> SkillResult:
        engine     = get_gate_engine()
        check_result = engine.check(state)  # GateCheckResult 반환

        # GateCheckResult → AgentState 호환 GateResult 변환
        gate_result = GateResult(
            passed       = check_result.passed,
            checked_at   = check_result.checked_at,
            passed_items = check_result.passed_items,   # rule_id 목록
            failed_items = check_result.failed_items,   # rule_id 목록
            gate_version = check_result.gate_version,
        )

        # 게이트 이력 갱신
        gate_history  = list(state.get("gate_history", []))
        gate_attempts = state.get("gate_attempts", 0) + 1
        gate_history.append(gate_result)

        return SkillResult(
            status        = SkillStatus.SUCCESS,
            state_updates = {
                "gate_result":   gate_result,
                "gate_attempts": gate_attempts,
                "gate_history":  gate_history,
                "current_step":  StepName.GATE_CHECK,
                "completed_steps": list(state.get("completed_steps", [])) + [StepName.GATE_CHECK],
                "step_count":    state.get("step_count", 0) + 1,
            },
            message    = (
                f"게이트 통과: {gate_result.passed_items}"
                if gate_result.passed
                else f"게이트 미충족: {gate_result.failed_items}"
            ),
            confidence = 1.0,  # Config Rule 기반 — LLM 신뢰도 불필요
        )
