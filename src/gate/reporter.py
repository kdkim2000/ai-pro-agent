# src/gate/reporter.py
"""
게이트 결과 포매터 (T1-4)

CLI 출력·로그·API 응답 등 다양한 형식으로 GateCheckResult를 포매팅한다.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from src.gate.engine import GateCheckResult


class GateReporter:
    """게이트 결과를 다양한 형식으로 출력하는 포매터"""

    def format_summary(self, result: "GateCheckResult") -> str:
        """한 줄 요약"""
        return result.summary

    def format_failed_guidance(self, result: "GateCheckResult") -> str:
        """미충족 필수 규칙 안내 메시지 (담당자용)"""
        if result.passed:
            return "✅ 모든 필수 조건이 충족되었습니다."

        lines = ["❌ 다음 항목을 처리한 후 게이트를 재검사하세요.\n"]
        for i, rule in enumerate(result.failed_required, 1):
            lines.append(f"  [{i}] {rule.rule_name}")
            lines.append(f"       → {rule.reason}")
            lines.append(f"       (규칙 ID: {rule.rule_id})\n")

        if result.warning_rules:
            lines.append("⚠️  권고 미충족 항목 (차단하지 않음):")
            for rule in result.warning_rules:
                lines.append(f"  - {rule.rule_name}: {rule.reason}")

        return "\n".join(lines)

    def format_detail(self, result: "GateCheckResult") -> str:
        """전체 규칙 상세 결과"""
        lines = [
            f"게이트 검사 결과 v{result.version}",
            f"검사 시각: {result.checked_at}",
            f"전체: {result.summary}",
            "",
            "── 통과 규칙 ──",
        ]
        for r in result.passed_rules:
            lines.append(f"  ✅ [{r.rule_id}] {r.rule_name}")
        lines.append("")
        lines.append("── 실패 규칙 ──")
        for r in result.failed_required:
            req = "필수" if r.required else "권고"
            lines.append(f"  ❌ [{r.rule_id}][{req}] {r.rule_name}")
            lines.append(f"      {r.reason}")
        if result.warning_rules:
            lines.append("")
            lines.append("── 권고 미충족 ──")
            for r in result.warning_rules:
                lines.append(f"  ⚠️  [{r.rule_id}] {r.rule_name}: {r.reason}")
        return "\n".join(lines)

    def format_json(self, result: "GateCheckResult") -> Dict[str, Any]:
        """API 응답용 JSON 구조"""
        return {
            "passed":     result.passed,
            "version":    result.version,
            "checked_at": result.checked_at,
            "summary":    result.summary,
            "failed": [
                {"id": r.rule_id, "name": r.rule_name, "reason": r.reason}
                for r in result.failed_required
            ],
            "warnings": [
                {"id": r.rule_id, "name": r.rule_name, "reason": r.reason}
                for r in result.warning_rules
            ],
        }
