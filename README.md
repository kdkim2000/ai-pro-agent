# 프로그램 개발 전주기 지원 AI Agent

> **과제**: AI 인증 3단계 — AI기반 개발/운영업무 생산성 향상  
> **부서**: 중공업IT파트  
> **환경**: 삼성SDS 사내망 (SCP/VDI) · AI Pro LLM · Febrix 벡터DB

---

## 개요

CR(Change Request) 접수부터 배포 준비까지 프로그램 개발 전주기를 지원하는 AI Agent.  
LangGraph 기반 DAG 워크플로우로 8단계 Skill을 오케스트레이션하며,  
RAG 기반 사내 지식 검색과 Config 기반 게이트 점검으로 관리 포인트 누락을 방지한다.

## 주요 기능

- **요구사항 구체화**: RAG 기반 유사 CR·코드·문서 검색
- **영향도 분석**: Oracle 19c 딕셔너리 + 코드 의존성 분석
- **공수 산정**: 유사 CR 이력 기반 객관적 산정
- **산출물 초안 생성**: Confluence 표준 템플릿 기반
- **관리 포인트 게이트**: Config 기반 확정적 누락 방지
- **배포 준비 지원**: PR 본문·체크리스트 자동 생성

## 기술 스택

| 구성 요소 | 기술 |
|-----------|------|
| LLM | 삼성 AI Pro API (BaseChatModel 래퍼) |
| 벡터DB | Febrix API (VectorStore 래퍼) |
| 임베딩 | AI Pro 임베딩 엔드포인트 |
| 오케스트레이션 | LangGraph 0.2+ |
| 런타임 | Python 3.11+ |

## 프로젝트 구조

```
├── config/             # 설정 파일
├── src/
│   ├── llm/            # AI Pro LLM·임베딩 클라이언트
│   ├── vectordb/       # Febrix 벡터DB 클라이언트
│   ├── connectors/     # 외부 시스템 연동 (GitHub, Confluence, JSM 등)
│   ├── agent/          # LangGraph DAG 워크플로우
│   ├── skills/         # 8개 Skill 구현
│   ├── rag/            # 청크·인덱싱·검색·Reranker
│   ├── gate/           # 게이트 Config 로더·판별 엔진
│   └── utils/          # 로깅·마스킹·지표
├── tests/              # 테스트 코드
└── docs/               # 문서
```

## 설치 및 실행

```bash
# 가상환경 생성
python -m venv .venv
.venv\Scripts\activate          # Windows

# 패키지 설치
pip install -r requirements.txt

# 환경변수 설정
# .env 파일에 AI Pro, Febrix 등 엔드포인트 및 API 키 입력

# 스모크 테스트
pytest tests/test_smoke.py -v
```

## Task 진행 현황

전체 Task 목록은 [AI-Agent_TASK.md](docs/AI-Agent_TASK.md) 참조.

---

*Samsung SDS | 중공업IT파트*
