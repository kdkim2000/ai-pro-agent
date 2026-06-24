# src/skills/s03_estimation.py
"""
공수 산정 Skill — Stub (T3-5에서 완성 예정)

유사 CR 벡터 검색으로 개발 공수를 추정하고
DB 변경 추가 공수를 산정한다.
"""
from __future__ import annotations

from src.agent.state import AgentState, EstimationResult, StepName
from src.skills.base import BaseSkill, SkillResult, SkillStatus


class EstimationSkill(BaseSkill):
    skill_name  = "estimation_skill"
    step        = StepName.ESTIMATION
    max_retries = 2

    def execute(self, state: AgentState) -> SkillResult:
        # ① 유사 CR 벡터 검색 (T3-5에서 구현)
        # ② LLM 기반 공수 추정 (T3-5에서 구현)

        result_data = EstimationResult(
            estimated_screens = 1,
            estimated_hours   = 16.0,
            db_extra_hours    = 0.0,
            basis_cr_ids      = [],
            confidence        = "medium",
            breakdown         = {"분석": 4.0, "개발": 8.0, "테스트": 4.0},
        )

        return SkillResult(
            status        = SkillStatus.SUCCESS,
            state_updates = {
                "estimation_result": result_data,
                "current_step":      StepName.ESTIMATION,
                "completed_steps":   list(state.get("completed_steps", [])) + [StepName.ESTIMATION],
                "step_count":        state.get("step_count", 0) + 1,
            },
            message    = "공수 산정 완료 (Stub)",
            confidence = 0.75,
        )
