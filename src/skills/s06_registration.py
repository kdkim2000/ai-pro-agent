# src/skills/s06_registration.py
"""
시스템 등록 지원 Skill — Stub (T3-8에서 완성 예정)

JSM·프로그램마스터·테이블마스터·용어사전 등록 초안을 생성한다.
실제 등록은 HITL 승인 후 수행한다.
"""
from __future__ import annotations

from src.agent.state import AgentState, RegistrationResult, StepName
from src.skills.base import BaseSkill, SkillResult, SkillStatus


class RegistrationSkill(BaseSkill):
    skill_name  = "registration_skill"
    step        = StepName.REGISTRATION
    max_retries = 2

    def execute(self, state: AgentState) -> SkillResult:
        # ① JSM 등록 초안 생성 (T3-8에서 구현)
        # ② 프로그램마스터 초안 생성 (T3-8에서 구현)
        # ③ 용어사전 미등록 용어 검사 (T3-8에서 구현)

        result_data = RegistrationResult(
            jsm_draft            = {"title": "[T3-8 구현 예정]"},
            program_master_draft = {"program_id": "[T3-8 구현 예정]"},
            table_master_drafts  = [],
            unregistered_terms   = [],
            term_drafts          = [],
        )

        return SkillResult(
            status        = SkillStatus.SUCCESS,
            state_updates = {
                "registration_result": result_data,
                "current_step":        StepName.REGISTRATION,
                "completed_steps":     list(state.get("completed_steps", [])) + [StepName.REGISTRATION],
                "step_count":          state.get("step_count", 0) + 1,
            },
            message    = "시스템 등록 초안 생성 완료 (Stub)",
            confidence = 0.85,
        )
