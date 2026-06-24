# src/gate/engine.py
"""
게이트 Rule Engine — Config 기반 완전 구현 (T1-4)

핵심 원칙:
  - LLM 호출 금지 — 모든 판별은 validator.py의 확정적 로직으로만 처리
  - 규칙 변경은 gate_rules.yaml 편집으로만 — 코드 수정 불필요
  - required=true 규칙 1개 이상 실패 시 passed=False 반환
"""
from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.gate.loader import GateRulesLoader
from src.gate.reporter import GateReporter
from src.gate.validator import evaluate_rule

logger = logging.getLogger(__name__)


@dataclass
class RuleCheckResult:
    """단일 규칙 검사 결과"""
    rule_id:    str
    rule_name:  str
    step:       str
    passed:     bool
    required:   bool
    reason:     str
    check_type: str
    field:      str


@dataclass
class GateCheckResult:
    """전체 게이트 검사 결과"""
    passed:        bool
    version:       str
    checked_at:    str
    total_rules:   int
    passed_rules:  List[RuleCheckResult] = field(default_factory=list)
    failed_rules:  List[RuleCheckResult] = field(default_factory=list)
    warning_rules: List[RuleCheckResult] = field(default_factory=list)  # required=false 실패

    @property
    def failed_required(self) -> List[RuleCheckResult]:
        """필수 규칙 실패 목록 (required=true 이고 passed=False)"""
        return [r for r in self.failed_rules if r.required]

    @property
    def summary(self) -> str:
        """한 줄 요약"""
        total   = self.total_rules
        passed  = len(self.passed_rules)
        failed  = len(self.failed_required)
        warning = len(self.warning_rules)
        status  = "✅ 통과" if self.passed else "❌ 차단"
        return (
            f"{status} | 전체 {total}개 규칙 | "
            f"통과 {passed}개 | 필수 실패 {failed}개 | 권고 미충족 {warning}개"
        )

    # ── AgentState 호환 속성 (T1-3 GateResult 대체) ─────────────────
    @property
    def passed_items(self) -> List[str]:
        return [r.rule_id for r in self.passed_rules]

    @property
    def failed_items(self) -> List[str]:
        return [r.rule_id for r in self.failed_required]

    @property
    def gate_version(self) -> str:
        return self.version


class GateEngine:
    """
    Config 기반 게이트 Rule Engine.

    ⚠️  핵심 원칙:
    - LLM 호출 금지 — 모든 판별은 validator.py의 확정적 로직으로만 처리
    - 규칙 변경은 gate_rules.yaml 편집으로만 — 코드 수정 불필요
    - required=true 규칙 1개 이상 실패 시 passed=False 반환
    """

    def __init__(self, config_path: Optional[str] = None):
        self._loader   = GateRulesLoader(config_path)
        self._reporter = GateReporter()

    def check(
        self,
        state: Dict[str, Any],
        step: Optional[str] = None,
    ) -> GateCheckResult:
        """
        AgentState 전체(또는 특정 step)에 대해 게이트 규칙 검사.

        Args:
            state: AgentState dict
            step:  None이면 전체 규칙, 지정하면 해당 step 규칙만

        Returns:
            GateCheckResult
        """
        rules    = self._loader.get_rules(step=step)
        settings = self._loader.get_settings()
        version  = self._loader.get_version()

        passed_rules:  List[RuleCheckResult] = []
        failed_rules:  List[RuleCheckResult] = []
        warning_rules: List[RuleCheckResult] = []

        for rule in rules:
            rule_id    = rule.get("id", "UNKNOWN")
            rule_name  = rule.get("name", "")
            rule_step  = rule.get("step", "")
            required   = rule.get("required", True)
            check_type = rule.get("check_type", "")
            field_path = rule.get("field", "")

            # _all_required_passed 특수 규칙 처리
            if field_path == "_all_required_passed":
                # 이 시점까지 수집된 failed_rules 기준으로 판별
                all_req_passed = len(failed_rules) == 0
                passed = all_req_passed
                reason = "모든 필수 규칙 통과" if passed else f"필수 규칙 {len(failed_rules)}개 미충족"
            else:
                try:
                    passed, reason = evaluate_rule(rule, state)
                except Exception as e:
                    logger.error(f"규칙 평가 예외: {rule_id} — {e}")
                    passed, reason = False, f"평가 오류: {e}"

            result = RuleCheckResult(
                rule_id    = rule_id,
                rule_name  = rule_name,
                step       = rule_step,
                passed     = passed,
                required   = required,
                reason     = reason,
                check_type = check_type,
                field      = field_path,
            )

            if passed:
                passed_rules.append(result)
            elif required:
                failed_rules.append(result)
                logger.warning(f"게이트 필수 규칙 실패: [{rule_id}] {rule_name} — {reason}")
            else:
                warning_rules.append(result)
                logger.info(f"게이트 권고 미충족: [{rule_id}] {rule_name} — {reason}")

        # strict_mode: required=true 하나라도 실패 시 전체 차단
        strict_mode    = settings.get("strict_mode", True)
        overall_passed = len(failed_rules) == 0 if strict_mode else True

        return GateCheckResult(
            passed        = overall_passed,
            version       = version,
            checked_at    = datetime.datetime.now().isoformat(),
            total_rules   = len(rules),
            passed_rules  = passed_rules,
            failed_rules  = failed_rules,
            warning_rules = warning_rules,
        )

    def check_step(self, state: Dict[str, Any], step: str) -> GateCheckResult:
        """특정 단계의 규칙만 검사"""
        return self.check(state, step=step)

    def get_failed_guidance(self, result: GateCheckResult) -> str:
        """
        미충족 항목에 대한 담당자 안내 메시지 생성.
        (LLM 없이 rule_name과 description만으로 구성)
        """
        return self._reporter.format_failed_guidance(result)

    def reload_config(self) -> str:
        """gate_rules.yaml 강제 리로드. 반환값: 새 버전"""
        return self._loader.reload()
