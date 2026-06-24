# AGENTS.md — AI Pro Lifecycle Agent

## Quick start

```bash
python -m venv .venv && source .venv/Scripts/activate && pip install -r requirements.txt
cp .env.sample .env          # fill in real creds
```

Always set `USE_MOCK_CONNECTORS=true` for local/T3 dev — all 7 connectors switch to mock with realistic sample data.

## Test

```bash
pytest                              # all (verbose, short tb)
pytest tests/connectors/ -v         # mock connector tests (no network)
pytest tests/agent/test_workflow.py # full DAG test
```

Tests importing connectors or skills **must** set `os.environ["USE_MOCK_CONNECTORS"] = "true"` at module top before any `from src.*` import. Without this, skill `__init__` tries real API connections and fails.

## Architecture

- **Entrypoint**: `src/agent/workflow.py` → `build_app()` returns compiled `StateGraph` (13 nodes, 3 HITL interrupt points). The older `src/agent/scaffold.py` is a 4-node prototype — use `workflow.py` for new work.
- **State**: `src/agent/state.py` — `AgentState(TypedDict)` with `add_messages` reducer. Each skill owns one `<step>_result` field.
- **Skills**: `src/skills/s01_*.py`–`s08_*.py`, all extend `BaseSkill` (retry + low-confidence HITL escalation built in). Currently all **Stub** — real logic lands in T3.
- **Connectors**: `src/connectors/factory.py` — `ConnectorFactory.github()`, `.confluence()`, `.jsm()`, `.doodream()`, `.oracle()`, `.master()`, `.dictionary()`. All return `ConnectorResult(success, data, error)`. Write methods (`create_pr_draft`, `create_page`) are HITL-gated.
- **Gate**: `src/gate/engine.py` — deterministic rule engine (no LLM). Rules in `config/gate_rules.yaml`. `GateRulesLoader` is a singleton with auto-hot-reload.

## Key conventions

- `get_logger()` from `src/utils/logger.py` — structlog, JSON output, ISO timestamps.
- Config from `config/config.yaml` (LLM temp, RAG weights, gate path). Never hardcode.
- `AgentState` **immutable fields** (set once, never change): `cr_id`, `cr_type`, `cr_info`.
- Skill confidence `< 0.5` → auto HITL escalation (`hitl_status=waiting`).
- `gate_rules.yaml:version` must be bumped on any rule change.
- LangGraph `interrupt()` used for 3 HITL points: `hitl_artifact`, `hitl_gate`, `hitl_deploy`.
- Compile with `MemorySaver` checkpointer for HITL resume.

## Work history protocol

After any Task completion, write `docs/work-history/<TASK-ID>_<title>_작업이력.md` (see `docs/work-history/T1-1_환경셋업_작업이력.md` for template), then `git add docs/work-history/ && git commit -m "docs: <TASK-ID> 작업이력 추가"`, and update the Implementation Phases section in `CLAUDE.md`.
