# src/gate/mock/simulator.py
"""
사외 환경 게이트 Mock 시뮬레이터 (T1-4)

GATE_ENV=mock 일 때 GateEngine 대신 이 시뮬레이터를 사용.
실제 GateEngine을 내부적으로 호출하되, State를 Mock 시나리오로 채워서 전달.

사용 예:
    sim = GateMockSimulator()

    # 시나리오 실행
    result = sim.run_scenario(Scenario.ALL_PASS)
    print(result.summary)

    # 특정 시나리오 단계별 실행
    result = sim.run_scenario(Scenario.MISSING_PROGRAM_MASTER, step="registration")
"""
from __future__ import annotations

import os
from typing import Dict, Optional

from src.gate.engine import GateCheckResult, GateEngine
from src.gate.mock.scenarios import MockScenarioFactory, Scenario


class GateMockSimulator:
    """
    사외 환경 게이트 Mock 시뮬레이터.
    """

    def __init__(self, config_path: Optional[str] = None):
        self._engine  = GateEngine(config_path)
        self._factory = MockScenarioFactory()

    def run_scenario(
        self,
        scenario: Scenario,
        step: Optional[str] = None,
    ) -> GateCheckResult:
        """시나리오 이름으로 Mock State 생성 후 게이트 검사"""
        state = self._factory.build(scenario)
        return self._engine.check(state, step=step)

    def run_all_scenarios(self) -> Dict[str, GateCheckResult]:
        """모든 시나리오 일괄 실행"""
        results = {}
        for scenario in Scenario:
            try:
                results[scenario.value] = self.run_scenario(scenario)
            except Exception as e:
                print(f"⚠️  시나리오 오류: {scenario.value} — {e}")
        return results

    def interactive_demo(self) -> None:
        """CLI 대화형 데모 — 시나리오 선택 후 결과 출력"""
        from src.gate.reporter import GateReporter
        reporter = GateReporter()

        print("\n" + "=" * 60)
        print("  게이트 Config 체계 Mock 시뮬레이터")
        print("  GATE_ENV=mock | 사외 환경용")
        print("=" * 60)

        scenarios_list = list(Scenario)
        for i, s in enumerate(scenarios_list, 1):
            print(f"  [{i:2d}] {s.value}")
        print("  [ 0] 전체 시나리오 일괄 실행")
        print("  [ q] 종료")

        while True:
            choice = input("\n시나리오 번호 입력: ").strip()
            if choice == "q":
                break
            if choice == "0":
                results = self.run_all_scenarios()
                print("\n── 전체 시나리오 결과 ──")
                for name, result in results.items():
                    icon = "✅" if result.passed else "❌"
                    print(f"  {icon} {name}")
                continue
            try:
                idx      = int(choice) - 1
                scenario = scenarios_list[idx]
                result   = self.run_scenario(scenario)
                print(f"\n{reporter.format_detail(result)}")
                if not result.passed:
                    print(f"\n{reporter.format_failed_guidance(result)}")
            except (ValueError, IndexError):
                print("올바른 번호를 입력하세요.")


def get_gate_engine() -> GateEngine:
    """
    환경변수 GATE_ENV에 따라 실/Mock 게이트 엔진 반환.
    Skill s07_gate.py에서 이 함수를 호출.
    """
    gate_env = os.getenv("GATE_ENV", "mock").lower()
    if gate_env == "mock":
        # Mock 시뮬레이터가 내부적으로 실제 GateEngine을 사용
        return GateMockSimulator()._engine
    # real: 동일한 GateEngine (실 State가 들어오면 실제 판별)
    return GateEngine()
