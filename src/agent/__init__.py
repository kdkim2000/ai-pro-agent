# agent 패키지 공개 인터페이스 (T1-3 업데이트)
# scaffold.py는 T1-1 뼈대로 하위 호환을 위해 유지
from src.agent.state import AgentState, CRType, StepName, HITLStatus, create_initial_state
from src.agent.workflow import build_workflow, build_app
from src.agent.router import route_by_cr_type, check_gate_result, check_hitl_status

__all__ = [
    # State
    "AgentState", "CRType", "StepName", "HITLStatus", "create_initial_state",
    # Workflow
    "build_workflow", "build_app",
    # Router
    "route_by_cr_type", "check_gate_result", "check_hitl_status",
]
