# src/gate/validator.py
"""
게이트 규칙 개별 평가 함수 (T1-4)

check_type별 확정적 로직으로 AgentState 필드를 검사한다.
LLM 호출 없음 — 모든 판별은 Python 순수 로직으로만 처리.

지원 check_type (10종 + 1종):
    field_exists    : 필드가 None이 아님
    field_not_empty : 필드가 빈 문자열/리스트/딕셔너리가 아님
    min_length      : 문자열 최소 길이
    list_not_empty  : 리스트가 비어있지 않음
    list_max_count  : 리스트 길이 상한 (0이면 빈 리스트 = 통과)
    bool_true       : 필드가 True
    bool_false      : 필드가 False (또는 None)
    dict_has_keys   : 딕셔너리가 지정 키를 모두 포함
    numeric_gte     : 숫자 >= 기준값
    numeric_lte     : 숫자 <= 기준값
    one_of          : 필드 값이 허용 목록에 포함
"""
from __future__ import annotations

from typing import Any, Dict


def evaluate_rule(rule: Dict[str, Any], state: Dict[str, Any]) -> tuple[bool, str]:
    """
    단일 규칙을 AgentState에 적용하여 통과 여부와 이유를 반환.

    Args:
        rule : gate_rules.yaml의 규칙 dict
        state: AgentState dict (또는 dict-like 객체)

    Returns:
        (passed: bool, reason: str)
    """
    check_type = rule.get("check_type", "")
    field      = rule.get("field", "")

    # ── 특수 필드: 엔진 내부 집계값 ─────────────────────────────────
    if field == "_all_required_passed":
        # GateEngine에서 직접 처리 — validator에서는 항상 True 반환
        return True, "엔진 내부 집계 — GateEngine에서 처리"

    value = _get_nested(state, field)

    # ── check_type별 처리 ────────────────────────────────────────────

    if check_type == "field_exists":
        passed = value is not None
        reason = f"필드 '{field}' 존재함" if passed else f"필드 '{field}'가 None"
        return passed, reason

    if check_type == "field_not_empty":
        passed = value is not None and value != "" and value != [] and value != {}
        reason = f"필드 '{field}' 값 있음" if passed else f"필드 '{field}'가 비어있음"
        return passed, reason

    if check_type == "min_length":
        min_len = rule.get("min_length", 0)
        actual  = len(str(value)) if value is not None else 0
        passed  = actual >= min_len
        reason  = (
            f"길이 {actual}자 (최소 {min_len}자)" if passed
            else f"길이 부족: {actual}자 < {min_len}자"
        )
        return passed, reason

    if check_type == "list_not_empty":
        passed = isinstance(value, list) and len(value) > 0
        count  = len(value) if isinstance(value, list) else 0
        reason = f"목록 {count}건" if passed else f"목록이 비어있음 ({count}건)"
        return passed, reason

    if check_type == "list_max_count":
        max_count = rule.get("max_count", 0)
        count     = len(value) if isinstance(value, list) else (0 if value is None else 1)
        passed    = count <= max_count
        reason    = (
            f"항목 {count}건 (최대 {max_count}건 허용)" if passed
            else f"항목 초과: {count}건 > {max_count}건"
        )
        return passed, reason

    if check_type == "bool_true":
        passed = bool(value) is True
        reason = "True 확인" if passed else f"True가 아님 (현재값: {value})"
        return passed, reason

    if check_type == "bool_false":
        passed = not bool(value)
        reason = "False/None 확인" if passed else f"False가 아님 (현재값: {value})"
        return passed, reason

    if check_type == "dict_has_keys":
        required_keys = rule.get("required_keys", [])
        if not isinstance(value, dict):
            return False, f"딕셔너리가 아님 (타입: {type(value).__name__})"
        missing = [k for k in required_keys if k not in value]
        passed  = len(missing) == 0
        reason  = (
            f"필수 키 모두 존재: {required_keys}" if passed
            else f"누락된 키: {missing}"
        )
        return passed, reason

    if check_type == "numeric_gte":
        threshold = rule.get("threshold", 0)
        try:
            passed = float(value or 0) >= threshold
            reason = (
                f"값 {value} >= {threshold}" if passed
                else f"값 부족: {value} < {threshold}"
            )
        except (TypeError, ValueError):
            passed, reason = False, f"숫자 변환 불가: {value}"
        return passed, reason

    if check_type == "numeric_lte":
        threshold = rule.get("threshold", 0)
        try:
            passed = float(value or 0) <= threshold
            reason = (
                f"값 {value} <= {threshold}" if passed
                else f"값 초과: {value} > {threshold}"
            )
        except (TypeError, ValueError):
            passed, reason = False, f"숫자 변환 불가: {value}"
        return passed, reason

    if check_type == "one_of":
        allowed = rule.get("allowed_values", [])
        passed  = value in allowed
        reason  = (
            f"허용값 '{value}'" if passed
            else f"허용되지 않는 값: '{value}' (허용: {allowed})"
        )
        return passed, reason

    return False, f"알 수 없는 check_type: '{check_type}'"


def _get_nested(obj: Any, path: str) -> Any:
    """
    점(.) 구분 경로로 중첩 구조에서 값 추출.
    dataclass(속성 접근)·dict(키 접근) 모두 지원.

    Examples:
        _get_nested(state, "requirement_result.confirmed")
        _get_nested(state, "impact_result.oracle_consistency_issues")
    """
    if not path:
        return obj
    parts   = path.split(".")
    current = obj
    for part in parts:
        if current is None:
            return None
        if isinstance(current, dict):
            current = current.get(part)
        elif hasattr(current, part):
            current = getattr(current, part)
        else:
            return None
    return current
