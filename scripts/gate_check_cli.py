#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/gate_check_cli.py
게이트 Config 체계 CLI 도구.
사외 환경에서 Mock으로 전체 시나리오를 실행하고 결과를 확인한다.

사용법:
    # 대화형 데모
    python scripts/gate_check_cli.py

    # 특정 시나리오 실행
    python scripts/gate_check_cli.py --scenario all_pass
    python scripts/gate_check_cli.py --scenario oracle_issue

    # 전체 시나리오 일괄 실행
    python scripts/gate_check_cli.py --all

    # 특정 step 규칙만 검사
    python scripts/gate_check_cli.py --scenario all_pass --step artifact

    # Config 리로드 후 버전 확인
    python scripts/gate_check_cli.py --reload

    # 현재 gate_rules.yaml 규칙 목록 출력
    python scripts/gate_check_cli.py --list-rules
"""
import argparse
import io
import os
import sys

# Windows cp949 환경에서 한글/이모지 출력 깨짐 방지
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("GATE_ENV", "mock")
os.environ.setdefault("USE_MOCK_CONNECTORS", "true")


def main():
    parser = argparse.ArgumentParser(
        description="게이트 Config 체계 CLI 도구 (사외 Mock 환경)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--scenario", "-s", type=str, help="실행할 시나리오 이름")
    parser.add_argument("--step",     "-t", type=str, help="검사할 단계 (생략 시 전체)")
    parser.add_argument("--all",      "-a", action="store_true", help="전체 시나리오 일괄 실행")
    parser.add_argument("--reload",   "-r", action="store_true", help="Config 리로드")
    parser.add_argument("--list-rules", "-l", action="store_true", help="규칙 목록 출력")
    parser.add_argument("--detail",   "-d", action="store_true", help="상세 결과 출력")
    args = parser.parse_args()

    from src.gate.mock.simulator import GateMockSimulator
    from src.gate.mock.scenarios import Scenario
    from src.gate.loader import GateRulesLoader
    from src.gate.reporter import GateReporter

    sim      = GateMockSimulator()
    loader   = GateRulesLoader()
    reporter = GateReporter()

    # ── Config 리로드 ──────────────────────────────────────────────────
    if args.reload:
        version = loader.reload()
        print(f"✅ Config 리로드 완료 — 버전: {version}")
        return

    # ── 규칙 목록 출력 ────────────────────────────────────────────────
    if args.list_rules:
        rules = loader.get_rules(step=args.step)
        step_label = f"[{args.step}]" if args.step else "[전체]"
        print(f"\n게이트 규칙 목록 {step_label} (v{loader.get_version()})\n")
        current_step = None
        for rule in rules:
            if rule.get("step") != current_step:
                current_step = rule.get("step")
                print(f"\n── {current_step} ──")
            req = "필수" if rule.get("required", True) else "권고"
            print(f"  [{rule['id']}][{req}] {rule['name']}")
            print(f"    check_type: {rule['check_type']}  field: {rule['field']}")
        return

    # ── 전체 시나리오 실행 ────────────────────────────────────────────
    if args.all:
        results = sim.run_all_scenarios()
        print(f"\n{'='*60}")
        print(f"  전체 시나리오 결과 (v{loader.get_version()})")
        print(f"{'='*60}")
        pass_count = sum(1 for r in results.values() if r.passed)
        for name, result in results.items():
            icon = "✅" if result.passed else "❌"
            failed_ids = [r.rule_id for r in result.failed_required]
            suffix = f"  (실패 규칙: {failed_ids})" if failed_ids else ""
            print(f"  {icon} {name}{suffix}")
        print(f"\n{'='*60}")
        print(f"  통과: {pass_count}/{len(results)}")
        return

    # ── 특정 시나리오 실행 ────────────────────────────────────────────
    if args.scenario:
        try:
            scenario = Scenario(args.scenario)
        except ValueError:
            valid = [s.value for s in Scenario]
            print(f"❌ 알 수 없는 시나리오: '{args.scenario}'")
            print(f"   사용 가능: {valid}")
            sys.exit(1)

        result     = sim.run_scenario(scenario, step=args.step)
        step_label = f" [step={args.step}]" if args.step else ""
        print(f"\n시나리오: {scenario.value}{step_label}")
        print(f"Config 버전: {result.version}")
        print(f"\n{reporter.format_summary(result)}")

        if args.detail or not result.passed:
            print(f"\n{reporter.format_detail(result)}")
        if not result.passed:
            print(f"\n{reporter.format_failed_guidance(result)}")
        return

    # ── 기본: 대화형 데모 ─────────────────────────────────────────────
    sim.interactive_demo()


if __name__ == "__main__":
    main()
