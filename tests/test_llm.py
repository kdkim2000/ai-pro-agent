# tests/test_llm.py
"""AI Pro LLM 연동 테스트

T1-1_GUIDE.md §4.2 기반.
AI Pro API 호출 성공 및 메시지 변환 정상 동작을 확인한다.
※ 사내 API 연동 필요 — SCP/VDI 환경에서 실행.
"""
import pytest
from src.llm.aiPro_client import AiProChatModel
from langchain_core.messages import HumanMessage


def test_aiPro_basic_call():
    """AI Pro 기본 호출 테스트"""
    llm = AiProChatModel()
    messages = [HumanMessage(content="안녕하세요. 테스트 메시지입니다. 짧게 응답해주세요.")]
    result = llm._generate(messages)

    assert result is not None
    assert len(result.generations) > 0
    content = result.generations[0].message.content
    assert isinstance(content, str) and len(content) > 0
    print(f"✅ AI Pro 응답: {content[:100]}")


def test_aiPro_system_message():
    """시스템 메시지 포함 호출 테스트"""
    from langchain_core.messages import SystemMessage
    llm = AiProChatModel()
    messages = [
        SystemMessage(content="당신은 개발 업무를 지원하는 AI 어시스턴트입니다."),
        HumanMessage(content="CR이 무엇인지 한 줄로 설명하세요."),
    ]
    result = llm._generate(messages)
    assert result.generations[0].message.content
    print(f"✅ 시스템 메시지 응답: {result.generations[0].message.content[:100]}")
