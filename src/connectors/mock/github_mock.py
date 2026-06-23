# src/connectors/mock/github_mock.py
"""GitHub Enterprise Mock (T1-2_GUIDE.md Section 5)"""
from __future__ import annotations
from typing import Optional
from ..base import BaseGitHubConnector, ConnectorResult, CodeFile


class GitHubMockConnector(BaseGitHubConnector):
    """GitHub Enterprise Mock -- realistic sample data for T3 Skill development"""
    is_mock = True

    _CODE_SAMPLES = [
        CodeFile(
            path="src/program/ProgramMasterService.java",
            content="""
public class ProgramMasterService {
    public ProgramMaster findByProgramId(String programId) {
        return programMasterRepository.findById(programId)
            .orElseThrow(() -> new ProgramNotFoundException(programId));
    }
    public void registerProgram(ProgramMasterDto dto) {
        programMasterRepository.save(dto.toEntity());
    }
}""",
            repo="org/shic-app", branch="main", sha="abc123def",
            url="https://github.internal/org/shic-app/blob/main/src/program/ProgramMasterService.java",
            language="Java",
        ),
        CodeFile(
            path="src/table/TableMasterMapper.xml",
            content="""
<select id="selectTableList" parameterType="String">
    SELECT TABLE_ID, TABLE_NAME, TABLE_DESC
    FROM TBL_TABLE_MASTER
    WHERE SYSTEM_CODE = #{systemCode}
    AND USE_YN = 'Y'
</select>""",
            repo="org/shic-app", branch="main", sha="def456ghi",
            url="https://github.internal/org/shic-app/blob/main/src/table/TableMasterMapper.xml",
            language="XML",
        ),
    ]

    def health_check(self) -> ConnectorResult:
        return ConnectorResult(success=True, data="mock-connected")

    def search_code(self, query: str, repo: Optional[str] = None, top_k: int = 5) -> ConnectorResult:
        return ConnectorResult(success=True, data=self._CODE_SAMPLES[:top_k], source="mock")

    def get_file(self, repo: str, path: str, ref: str = "main") -> ConnectorResult:
        for f in self._CODE_SAMPLES:
            if f.path == path:
                return ConnectorResult(success=True, data=f)
        return ConnectorResult(success=False, error=f"Mock: file '{path}' not found")

    def list_repos(self, org: str) -> ConnectorResult:
        return ConnectorResult(success=True, data=["org/shic-app", "org/shic-batch", "org/shic-common"])

    def create_pr_draft(self, repo: str, title: str, body: str, head: str, base: str = "main") -> ConnectorResult:
        return ConnectorResult(success=True, data={"pr_number": 999, "pr_url": f"https://github.internal/{repo}/pull/999"}, source="mock")
