# src/connectors/factory.py
from __future__ import annotations
import os
from .base import (
    BaseGitHubConnector, BaseConfluenceConnector, BaseJSMConnector,
    BaseDoodreamConnector, BaseOracleConnector, BaseMasterConnector,
    BaseDictionaryConnector,
)


def _use_mock() -> bool:
    return os.getenv("USE_MOCK_CONNECTORS", "false").lower() == "true"


class ConnectorFactory:
    """
    환경변수 USE_MOCK_CONNECTORS 기반으로 실 커넥터 또는 Mock 커넥터를 반환.

    사용 예:
        github = ConnectorFactory.github()
        result = github.search_code("프로그램마스터 등록")
    """

    @staticmethod
    def github() -> BaseGitHubConnector:
        if _use_mock():
            from .mock.github_mock import GitHubMockConnector
            return GitHubMockConnector()
        from .github_client import GitHubEnterpriseConnector
        return GitHubEnterpriseConnector()

    @staticmethod
    def confluence() -> BaseConfluenceConnector:
        if _use_mock():
            from .mock.confluence_mock import ConfluenceMockConnector
            return ConfluenceMockConnector()
        from .confluence_client import ConfluenceConnector
        return ConfluenceConnector()

    @staticmethod
    def jsm() -> BaseJSMConnector:
        if _use_mock():
            from .mock.jsm_mock import JSMMockConnector
            return JSMMockConnector()
        from .jsm_client import JSMConnector
        return JSMConnector()

    @staticmethod
    def doodream() -> BaseDoodreamConnector:
        if _use_mock():
            from .mock.doodream_mock import DoodreamMockConnector
            return DoodreamMockConnector()
        from .doodream_client import DoodreamConnector
        return DoodreamConnector()

    @staticmethod
    def oracle() -> BaseOracleConnector:
        if _use_mock():
            from .mock.oracle_mock import OracleMockConnector
            return OracleMockConnector()
        from .oracle_client import Oracle19cConnector
        return Oracle19cConnector()

    @staticmethod
    def master() -> BaseMasterConnector:
        if _use_mock():
            from .mock.master_mock import MasterMockConnector
            return MasterMockConnector()
        from .master_client import MasterSystemConnector
        return MasterSystemConnector()

    @staticmethod
    def dictionary() -> BaseDictionaryConnector:
        if _use_mock():
            from .mock.dictionary_mock import DictionaryMockConnector
            return DictionaryMockConnector()
        from .dictionary_client import DictionaryConnector
        return DictionaryConnector()

    @staticmethod
    def all_health_check() -> dict:
        """모든 커넥터 연결 상태 일괄 확인"""
        results = {}
        connectors = {
            "github": ConnectorFactory.github,
            "confluence": ConnectorFactory.confluence,
            "jsm": ConnectorFactory.jsm,
            "doodream": ConnectorFactory.doodream,
            "oracle": ConnectorFactory.oracle,
            "master": ConnectorFactory.master,
            "dictionary": ConnectorFactory.dictionary,
        }
        for name, factory_fn in connectors.items():
            try:
                connector = factory_fn()
                result = connector.health_check()
                results[name] = {
                    "status": "ok" if result.success else "error",
                    "is_mock": connector.is_mock,
                    "error": result.error,
                }
            except Exception as e:
                results[name] = {"status": "exception", "is_mock": False, "error": str(e)}
        return results
