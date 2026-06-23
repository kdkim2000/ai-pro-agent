"""
Mock 기반 통합 테스트 — 사내 시스템 연결 없이 실행 가능.
T3 Skill 개발 전 커넥터 인터페이스 검증용.
"""
import os
import pytest

os.environ["USE_MOCK_CONNECTORS"] = "true"

from src.connectors.factory import ConnectorFactory
from src.connectors.base import CRRecord


def test_all_health_checks():
    """전체 커넥터 health check (Mock)"""
    results = ConnectorFactory.all_health_check()
    assert len(results) == 7
    for name, result in results.items():
        assert result["status"] == "ok", f"{name} health check 실패: {result.get('error')}"
        assert result["is_mock"] is True


def test_github_search_code():
    github = ConnectorFactory.github()
    result = github.search_code("프로그램마스터 등록", top_k=2)
    assert result.success
    assert len(result.data) > 0
    assert result.data[0].path.endswith(".java") or result.data[0].path.endswith(".xml")


def test_github_get_file():
    github = ConnectorFactory.github()
    result = github.get_file("org/shic-app", "src/program/ProgramMasterService.java")
    assert result.success
    assert result.data.repo == "org/shic-app"


def test_github_list_repos():
    github = ConnectorFactory.github()
    result = github.list_repos("org")
    assert result.success
    assert len(result.data) >= 1


def test_github_create_pr_draft():
    github = ConnectorFactory.github()
    result = github.create_pr_draft("org/shic-app", "Test PR", "body", "feature/test")
    assert result.success
    assert "pr_url" in result.data


def test_confluence_search_pages():
    confluence = ConnectorFactory.confluence()
    result = confluence.search_pages("Requirements")
    assert result.success
    assert len(result.data) > 0


def test_confluence_get_page():
    confluence = ConnectorFactory.confluence()
    result = confluence.get_page("10001")
    assert result.success
    assert result.data.page_id == "10001"


def test_confluence_get_template():
    confluence = ConnectorFactory.confluence()
    result = confluence.get_template("Requirements")
    assert result.success
    assert isinstance(result.data, str)


def test_confluence_create_page():
    confluence = ConnectorFactory.confluence()
    result = confluence.create_page("DEV", "Test Page", "<p>content</p>")
    assert result.success
    assert "page_id" in result.data


def test_doodream_search_history():
    doodream = ConnectorFactory.doodream()
    result = doodream.search_cr_history("신규 화면 개발", cr_type="new_dev", top_k=5)
    assert result.success
    assert len(result.data) > 0
    assert result.data[0].cr_type == "new_dev"
    assert result.data[0].actual_hours is not None


def test_doodream_get_cr():
    doodream = ConnectorFactory.doodream()
    result = doodream.get_cr("CR-2026-0312")
    assert result.success
    assert result.data.cr_id == "CR-2026-0312"


def test_doodream_get_recent_crs():
    doodream = ConnectorFactory.doodream()
    result = doodream.get_recent_crs(days=90, status="closed")
    assert result.success
    assert isinstance(result.data, list)


def test_oracle_table_info():
    oracle = ConnectorFactory.oracle()
    result = oracle.get_table_info("SHIP_ORDER")
    assert result.success
    tbl = result.data
    assert tbl.table_name == "SHIP_ORDER"
    assert len(tbl.columns) > 0


def test_oracle_affected_programs():
    oracle = ConnectorFactory.oracle()
    result = oracle.get_affected_programs("SHIP_ORDER")
    assert result.success
    assert isinstance(result.data["programs"], list)
    assert len(result.data["programs"]) > 0


def test_oracle_get_dependencies():
    oracle = ConnectorFactory.oracle()
    result = oracle.get_dependencies("SHIP_ORDER", "TABLE")
    assert result.success
    assert isinstance(result.data, list)


def test_oracle_check_consistency():
    oracle = ConnectorFactory.oracle()
    result = oracle.check_consistency(["SHIP_ORDER", "UNKNOWN_TABLE"])
    assert result.success
    found = {r["table_name"]: r["exists_in_oracle"] for r in result.data}
    assert found["SHIP_ORDER"] is True
    assert found["UNKNOWN_TABLE"] is False


def test_master_check_program_registered():
    master = ConnectorFactory.master()
    result = master.check_program_registered("SHI_SHIP_ORDER_01")
    assert result.success
    assert result.data["registered"] is True


def test_master_check_program_not_registered():
    master = ConnectorFactory.master()
    result = master.check_program_registered("NOT_EXIST_PROGRAM")
    assert result.success
    assert result.data["registered"] is False


def test_master_build_program_draft():
    master = ConnectorFactory.master()
    result = master.build_program_master_draft({
        "program_id": "SHI_SHIP_ORDER_01",
        "program_name": "선박 수주 현황 조회",
        "system_code": "SHIP",
        "menu_path": "영업관리 > 수주관리",
        "cr_id": "CR-2026-0001",
        "affected_tables": ["SHIP_ORDER"],
    })
    assert result.success
    assert result.data["program_id"] == "SHI_SHIP_ORDER_01"
    assert "_meta" in result.data


def test_master_build_table_draft():
    from src.connectors.base import OracleTableInfo
    master = ConnectorFactory.master()
    tbl = OracleTableInfo(
        table_name="SHIP_ORDER", owner="SHIC", row_count=100,
        comments="선박 수주 테이블", columns=[{"column_name": "ORDER_NO", "data_type": "VARCHAR2"}],
        dependencies=[],
    )
    result = master.build_table_master_draft(tbl)
    assert result.success
    assert result.data["table_name"] == "SHIP_ORDER"


def test_dictionary_detect_unregistered():
    dictionary = ConnectorFactory.dictionary()
    result = dictionary.detect_unregistered_terms(
        "선박 수주 현황 조회 화면에서 납기일과 발주처명을 표시합니다."
    )
    assert result.success
    assert "unregistered_terms" in result.data
    assert "total_checked" in result.data


def test_dictionary_check_term_registered():
    dictionary = ConnectorFactory.dictionary()
    result = dictionary.check_term_registered("납기일")
    assert result.success
    assert result.data["registered"] is True
    assert result.data["record"].term_en == "Delivery Date"


def test_dictionary_build_term_draft():
    dictionary = ConnectorFactory.dictionary()
    result = dictionary.build_term_draft("수주번호", "선박 수주번호를 입력하세요.")
    assert result.success
    assert result.data["term_ko"] == "수주번호"
    assert "_meta" in result.data


def test_jsm_build_issue_draft():
    jsm = ConnectorFactory.jsm()
    cr = CRRecord(
        cr_id="CR-2026-0001", title="선박 수주 현황 조회 화면 신규 개발",
        description="영업팀 요청 화면", cr_type="new_dev",
        status="open", requester="홍길동", assignee="김담당",
        created_at="2026-06-01", closed_at=None,
        actual_hours=None, estimated_hours=20.0,
        affected_systems=["SHIP_ORDER"], tags=["신규화면"],
    )
    result = jsm.build_issue_draft(cr)
    assert result.success
    assert "summary" in result.data
    assert "_meta" in result.data


def test_jsm_search_issues():
    jsm = ConnectorFactory.jsm()
    result = jsm.search_issues("project = SHIC", top_k=5)
    assert result.success
    assert isinstance(result.data, list)
