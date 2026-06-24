# src/gate/loader.py
"""
gate_rules.yaml 로더 — 싱글톤·핫리로드·자동 경로 탐색 (T1-4)
"""
from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class GateRulesLoader:
    """
    gate_rules.yaml 로더.
    - 파일 변경 감지 후 자동 리로드 (핫리로드)
    - 스레드 세이프 캐시
    - 사외 환경에서 기본 config 경로 자동 탐색
    """

    _instance: Optional["GateRulesLoader"] = None
    _lock = threading.Lock()

    def __new__(cls, config_path: Optional[str] = None):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_path: Optional[str] = None):
        if self._initialized:
            return
        self._config_path = Path(config_path or self._find_config())
        self._cache: Optional[Dict[str, Any]] = None
        self._last_mtime: float = 0.0
        self._initialized = True

    @classmethod
    def reset(cls) -> None:
        """테스트 환경에서 싱글톤 초기화용"""
        with cls._lock:
            cls._instance = None

    @staticmethod
    def _find_config() -> str:
        """프로젝트 루트에서 config/gate_rules.yaml 자동 탐색"""
        candidates = [
            "config/gate_rules.yaml",
            "../config/gate_rules.yaml",
            os.path.join(os.path.dirname(__file__), "../../config/gate_rules.yaml"),
        ]
        for path in candidates:
            if Path(path).exists():
                return path
        # 파일 없으면 기본 경로 반환 (최초 생성 전)
        return "config/gate_rules.yaml"

    def load(self, force_reload: bool = False) -> Dict[str, Any]:
        """
        gate_rules.yaml 로드 (변경 시 자동 리로드).
        파일이 없으면 기본 Config 반환.
        """
        with self._lock:
            try:
                mtime = self._config_path.stat().st_mtime
            except FileNotFoundError:
                return self._default_config()

            if force_reload or self._cache is None or mtime > self._last_mtime:
                with open(self._config_path, encoding="utf-8") as f:
                    self._cache = yaml.safe_load(f)
                self._last_mtime = mtime

            return self._cache

    def get_rules(self, step: Optional[str] = None) -> List[Dict[str, Any]]:
        """게이트 규칙 목록 반환. step 지정 시 해당 단계 규칙만"""
        config = self.load()
        rules  = config.get("gates", [])
        if step:
            rules = [r for r in rules if r.get("step") == step]
        return rules

    def get_settings(self) -> Dict[str, Any]:
        return self.load().get("settings", {})

    def get_version(self) -> str:
        return self.load().get("version", "unknown")

    def reload(self) -> str:
        """강제 리로드 후 버전 반환"""
        config = self.load(force_reload=True)
        return config.get("version", "unknown")

    @staticmethod
    def _default_config() -> Dict[str, Any]:
        """gate_rules.yaml 미생성 시 사용할 최소 기본 Config"""
        return {
            "version": "0.0.0-default",
            "settings": {
                "max_gate_attempts": 3,
                "confidence_threshold": 0.5,
                "strict_mode": True,
            },
            "gates": [],
        }


def get_gate_engine():
    """
    하위 호환 함수 — s07_gate.py, T1-3 코드 의존성 유지.
    환경변수 GATE_ENV에 따라 실/Mock 게이트 엔진 반환.
    """
    # 순환 import 방지를 위해 지연 import
    gate_env = os.getenv("GATE_ENV", "mock").lower()
    if gate_env == "mock":
        from src.gate.mock.simulator import GateMockSimulator
        return GateMockSimulator()._engine
    from src.gate.engine import GateEngine
    return GateEngine()


def invalidate_cache() -> None:
    """GateRulesLoader 싱글톤 캐시 무효화 (테스트·핫리로드용)"""
    GateRulesLoader.reset()
