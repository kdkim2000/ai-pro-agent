# src/skills/s04_task_breakdown.py
"""
Task 분해 Skill — Stub (T3-6에서 완성 예정)

LLM으로 개발 작업을 세부 Task로 분해하고
Confluence 체크리스트를 생성한다.
"""
from __future__ import annotations

from src.agent.state import AgentState, StepName, TaskBreakdownResult
from src.skills.base import BaseSkill, SkillResult, SkillStatus


class TaskBreakdownSkill(BaseSkill):
    skill_name  = "task_breakdown_skill"
    step        = StepName.TASK_BREAKDOWN
    max_retries = 1

    def execute(self, state: AgentState) -> SkillResult:
        # ① LLM 기반 Task 분해 (T3-6에서 구현)
        # ② Confluence 체크리스트 생성 (T3-6에서 구현)

        result_data = TaskBreakdownResult(
            tasks         = [
                {"id": "T-001", "title": "[T3-6 구현 예정]", "estimated_hours": 4.0, "done": False},
            ],
            checklist_url = None,
        )

        return SkillResult(
            status        = SkillStatus.SUCCESS,
            state_updates = {
                "task_breakdown_result": result_data,
                "current_step":          StepName.TASK_BREAKDOWN,
                "completed_steps":       list(state.get("completed_steps", [])) + [StepName.TASK_BREAKDOWN],
                "step_count":            state.get("step_count", 0) + 1,
            },
            message    = "Task 분해 완료 (Stub)",
            confidence = 0.85,
        )
