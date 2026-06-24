# src/skills/s02_impact.py
"""
영향도 분석 Skill — Stub (T3-4에서 완성 예정)

Oracle 딕셔너리 조회와 코드 정적 분석으로
변경 대상 테이블·프로그램 목록과 정합성 이슈를 도출한다.
"""
from __future__ import annotations

from src.agent.state import AgentState, ImpactAnalysisResult, StepName
from src.skills.base import BaseSkill, SkillResult, SkillStatus


class ImpactAnalysisSkill(BaseSkill):
    skill_name  = "impact_analysis_skill"
    step        = StepName.IMPACT_ANALYSIS
    max_retries = 3  # Oracle 일시 장애 대비

    def execute(self, state: AgentState) -> SkillResult:
        # ① Oracle 딕셔너리 조회 (T3-4에서 구현)
        # oracle = self._connectors.oracle()
        # tables = oracle.search_tables(...)

        # ② GitHub 코드 분석 (T3-4에서 구현)

        # ③ 결과 반환 (Stub)
        cr_id = state.get("cr_id", "")
        result_data = ImpactAnalysisResult(
            affected_tables           = ["[T3-4 구현 예정]"],
            affected_programs         = ["[T3-4 구현 예정]"],
            has_db_schema_change      = False,
            oracle_consistency_issues = [],
            impact_summary            = f"[T3-4 구현 예정] CR {cr_id} 영향도 분석",
        )

        return SkillResult(
            status        = SkillStatus.SUCCESS,
            state_updates = {
                "impact_result":   result_data,
                "current_step":    StepName.IMPACT_ANALYSIS,
                "completed_steps": list(state.get("completed_steps", [])) + [StepName.IMPACT_ANALYSIS],
                "step_count":      state.get("step_count", 0) + 1,
            },
            message    = "영향도 분석 완료 (Stub)",
            confidence = 0.85,
        )
