# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**프로그램 개발 전주기 지원 AI Agent** — LangGraph-based agent that automates CR (Change Request) handling across the full software development lifecycle. The agent orchestrates 8 skills (requirement refinement, impact analysis, effort estimation, artifact generation, gate checks, etc.) using Samsung-internal APIs: AI Pro LLM and Febrix VectorDB.

Target environment: Samsung SCP/VDI (internal network only). External API calls use `verify=False` due to internal self-signed certs — this is intentional.

## Development Commands

```bash
# Environment setup (run once)
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt

# Copy and fill in .env before running anything
cp .env .env.local              # or just edit .env directly

# Run all tests
pytest

# Run a single test file
pytest tests/test_scaffold.py

# Run a single test function
pytest tests/test_scaffold.py::test_new_dev_routing -v

# Connector Mock tests (no network required)
pytest tests/connectors/test_factory.py -v

# Smoke tests (require SCP/VDI with real API credentials)
pytest tests/test_smoke.py -v
```

## Architecture

### Core Design Pattern
All Samsung-internal APIs are wrapped in LangChain-compatible interfaces so the rest of the codebase uses standard LangChain/LangGraph primitives:

| Wrapper | Base Class | Internal API |
|---------|-----------|-------------|
| `AiProChatModel` | `BaseChatModel` | Samsung AI Pro LLM REST |
| `AiProEmbeddings` | `Embeddings` | AI Pro Embeddings REST |
| `FebrixVectorStore` | `VectorStore` | Febrix vector DB REST |

### LangGraph DAG (src/agent/scaffold.py)
`AgentState` TypedDict flows through a `StateGraph`. Entry point uses `route_by_cr_type()` for conditional dispatch:
- `new_dev` / `feature_change` → `requirement_skill`
- `db_change` → `impact_analysis_skill`

Skills in T1 are stubs; real implementations land in T3. The graph compiles to a runnable via `build_scaffold_graph()`.

### Three Vector Collections (src/vectordb/collections.py)
- `github_code` — source code indexed from GitHub Enterprise
- `confluence_docs` — Confluence wiki pages
- `cr_history` — historical CR records for few-shot retrieval

All collections use dimension 1536 (matching AI Pro embedding model).

### Gate Validation (config/gate_rules.yaml)
Five gate points: `requirement`, `impact_analysis`, `artifact`, `master_registration`, `deploy`. Each gate defines required fields, minimum lengths, and Oracle DB checks. Gate logic lives in `src/gate/` (implemented in T1-4).

## Configuration

`config/config.yaml` controls all tuneable parameters — LLM temperature, RAG hybrid weights (BM25 0.3 / dense 0.7), reranker top_k, agent max_steps. Never hardcode these values in source; always read from config.

`.env` holds all secrets (endpoints, API keys, DB credentials). Required variables: `AIPRO_ENDPOINT`, `AIPRO_API_KEY`, `FEBRIX_ENDPOINT`, `FEBRIX_API_KEY`.

## System Connectors (src/connectors/)

`ConnectorFactory` (T1-2) provides real/mock connector switching via `USE_MOCK_CONNECTORS=true` env var. All 7 connectors share `BaseConnector` ABC and return `ConnectorResult(success, data, error)`.

| Factory method | System | Key use |
|---|---|---|
| `ConnectorFactory.github()` | GitHub Enterprise | code search, file fetch, PR draft |
| `ConnectorFactory.confluence()` | Confluence | page search, template fetch, page create |
| `ConnectorFactory.jsm()` | JSM | issue search, registration draft |
| `ConnectorFactory.doodream()` | 두드림 | CR history search for few-shot |
| `ConnectorFactory.oracle()` | Oracle 19c | table metadata, dependency analysis (read-only) |
| `ConnectorFactory.master()` | 프로그램/테이블마스터 | registration check, draft generation |
| `ConnectorFactory.dictionary()` | 용어/단어사전 | term registration check, unregistered term detection |

Write methods (`create_pr_draft`, `create_page`) are HITL-gated — only call after human approval. Mock connectors in `src/connectors/mock/` contain realistic domain sample data for T3 development.

## Implementation Phases

Tasks defined in `docs/AI-Agent_TASK.md`. Current status:
- **T1-1** (env setup): complete — LLM/embedding/VectorDB wrappers, LangGraph scaffold
- **T1-2** (connectors): complete — 7 real connectors + 7 mocks + ConnectorFactory, 25 tests passing
- **T1-3** (architecture design): pending
- **T1-4** (gate config): pending
- **T2**: RAG pipeline — chunking, indexing, hybrid search (`src/rag/`)
  - **T2-1** (data collection & preprocessing): complete — collector, preprocessor, chunker, embedder, indexer, pipeline; 28 tests passing
- **T3**: 8 skill implementations (`src/skills/`)
- **T4**: Validation & optimization
- **T5**: MVP operations

When implementing new skills in `src/skills/`, register them as nodes in `src/agent/scaffold.py` and wire the conditional edges. Use `ConnectorFactory` with `USE_MOCK_CONNECTORS=true` during T3 development.

## Logging

Use `get_logger()` from `src/utils/logger.py` everywhere. Output is structured JSON (structlog). Audit-trail entries should be emitted at key decision points for compliance traceability.

## Work History Protocol

**모든 Task(T-시리즈) 또는 의미 있는 작업 완료 후 반드시 이력 파일을 작성하고 커밋한다.**

### 이력 파일 규칙

- 위치: `docs/work-history/<TASK-ID>_<제목>_작업이력.md`
  - 예: `T1-2_커넥터인터페이스_작업이력.md`, `T2-1_RAG파이프라인_작업이력.md`
- 형식: `docs/work-history/T1-1_환경셋업_작업이력.md` 참조
- 필수 섹션:
  1. 수행일 · 수행 방법 · 소요 시간 · 참조 문서 (헤더 메타)
  2. 작업 개요 (목적, 입력 문서, 완료 기준 체크리스트)
  3. VIBE 코딩 수행 과정 (단계별 상세 — 흐름도 포함)
  4. 발생 이슈 및 해결 (증상·원인·해결·교훈 표)
  5. 최종 변경 파일 목록
  6. 학습 포인트
  7. 사내망 환경 전환 시 체크리스트 (해당 시)

### 작성 후 커밋

```bash
git add docs/work-history/
git commit -m "docs: <TASK-ID> 작업이력 추가"
git push
```

### CLAUDE.md 진행 현황 업데이트

이력 파일 작성 후 위 **Implementation Phases** 섹션의 해당 Task 상태를 `complete`로 갱신한다.
