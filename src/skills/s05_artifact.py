# src/skills/s05_artifact.py
"""
산출물 초안 생성 Skill — Stub (T3-7에서 완성 예정)

LLM과 템플릿으로 요구사항 분석서·영향도 분석서·테스트 정의서를 생성하고
Confluence에 업로드한다.
"""
from __future__ import annotations

from src.agent.state import AgentState, ArtifactResult, StepName
from src.skills.base import BaseSkill, SkillResult, SkillStatus


class ArtifactSkill(BaseSkill):
    skill_name  = "artifact_skill"
    step        = StepName.ARTIFACT
    max_retries = 2

    def execute(self, state: AgentState) -> SkillResult:
        # ① LLM + 템플릿으로 산출물 초안 생성 (T3-7에서 구현)
        # ② Confluence 페이지 업로드 (T3-7에서 구현)

        cr_id = state.get("cr_id", "")
        result_data = ArtifactResult(
            requirement_doc     = f"[T3-7 구현 예정] 요구사항 분석서 — {cr_id}",
            impact_doc          = f"[T3-7 구현 예정] 영향도 분석서 — {cr_id}",
            test_definition_doc = f"[T3-7 구현 예정] 테스트 정의서 — {cr_id}",
            confluence_pages    = {},
            confirmed           = False,
        )

        return SkillResult(
            status        = SkillStatus.SUCCESS,
            state_updates = {
                "artifact_result": result_data,
                "current_step":    StepName.ARTIFACT,
                "completed_steps": list(state.get("completed_steps", [])) + [StepName.ARTIFACT],
                "step_count":      state.get("step_count", 0) + 1,
            },
            message    = "산출물 초안 생성 완료 (Stub)",
            confidence = 0.85,
        )
