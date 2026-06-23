# src/vectordb/collections.py
"""Febrix 벡터DB 컬렉션 정의

T1-1_GUIDE.md §6.2 기반.
Agent에서 사용할 컬렉션을 용도별로 분리 정의한다.
차원(dimension)은 AI Pro 임베딩 실측 후 수정.
"""

COLLECTIONS = {
    "github_code": {
        "name": "dev_agent_github_code",
        "description": "GitHub Enterprise 코드베이스 (함수·클래스 단위 청크)",
        "dimension": 1536,   # AI Pro 임베딩 차원 확인 후 수정
    },
    "confluence_docs": {
        "name": "dev_agent_confluence_docs",
        "description": "Confluence 문서 (섹션 단위 청크)",
        "dimension": 1536,
    },
    "cr_history": {
        "name": "dev_agent_cr_history",
        "description": "두드림 CR 처리 이력 (건 단위)",
        "dimension": 1536,
    },
}
