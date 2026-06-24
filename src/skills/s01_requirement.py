# src/skills/s01_requirement.py
"""
요구사항 구체화 Skill — Stub (T3-3에서 완성 예정)

CR 정보와 유사 CR 이력·Confluence 문서를 참조하여
요구사항을 구조화된 형태로 정리한다.
"""
from __future__ import annotations

from src.agent.state import AgentState, RequirementResult, StepName
from src.skills.base import BaseSkill, SkillResult, SkillStatus


class RequirementSkill(BaseSkill):
    skill_name  = "requirement_skill"
    step        = StepName.REQUIREMENT
    max_retries = 2

    def execute(self, state: AgentState) -> SkillResult:
        cr_info = state.get("cr_info")

        # ① RAG 검색 (T3-3에서 구현)
        # github     = self._connectors.github()
        # confluence = self._connectors.confluence()
        # doodream   = self._connectors.doodream()
        # code_results = github.search_code(cr_info.title, top_k=3)
        # doc_results  = confluence.search_pages(cr_info.description[:100], top_k=3)
        # cr_history   = doodream.search_cr_history(cr_info.title, ...)

        # ② LLM으로 요구사항 구체화 (T3-3에서 구현)

        # ③ 결과 반환 (현재는 Stub)
        cr_id = state.get("cr_id", "")
        result_data = RequirementResult(
            structured_requirement  = f"[T3-3 구현 예정] CR {cr_id}에 대한 요구사항 구체화",
            clarification_questions = ["[T3-3에서 구현]"],
            similar_cr_ids          = [],
            related_docs            = [],
            confirmed               = False,
        )

        return SkillResult(
            status        = SkillStatus.SUCCESS,
            state_updates = {
                "requirement_result": result_data,
                "current_step":       StepName.REQUIREMENT,
                "completed_steps":    list(state.get("completed_steps", [])) + [StepName.REQUIREMENT],
                "step_count":         state.get("step_count", 0) + 1,
            },
            message    = "요구사항 구체화 완료 (Stub)",
            confidence = 0.85,
        )
