# src/skills/s08_deploy.py
"""
배포 준비 지원 Skill — Stub (T3-10에서 완성 예정)

GitHub PR 본문 초안, 현업 테스트 요청 메일, Release 체크리스트를 생성한다.
"""
from __future__ import annotations

from src.agent.state import AgentState, DeployResult, StepName
from src.skills.base import BaseSkill, SkillResult, SkillStatus


class DeploySkill(BaseSkill):
    skill_name  = "deploy_skill"
    step        = StepName.DEPLOY
    max_retries = 1

    def execute(self, state: AgentState) -> SkillResult:
        # ① GitHub PR 본문 초안 생성 (T3-10에서 구현)
        # ② 현업 테스트 요청 메일 초안 생성 (T3-10에서 구현)
        # ③ Release 체크리스트 생성 (T3-10에서 구현)

        cr_id = state.get("cr_id", "")
        result_data = DeployResult(
            pr_body_draft           = f"[T3-10 구현 예정] PR 본문 — {cr_id}",
            test_request_mail_draft = f"[T3-10 구현 예정] 테스트 요청 메일 — {cr_id}",
            release_checklist       = {
                "요구사항 분석서 첨부": False,
                "테스트 정의서 첨부":   False,
                "현업 확인 메일 첨부":  False,
            },
            all_attachments_ready   = False,
            pr_url                  = None,
        )

        return SkillResult(
            status        = SkillStatus.SUCCESS,
            state_updates = {
                "deploy_result":   result_data,
                "current_step":    StepName.DEPLOY,
                "completed_steps": list(state.get("completed_steps", [])) + [StepName.DEPLOY],
                "step_count":      state.get("step_count", 0) + 1,
            },
            message    = "배포 준비 초안 생성 완료 (Stub)",
            confidence = 0.85,
        )
