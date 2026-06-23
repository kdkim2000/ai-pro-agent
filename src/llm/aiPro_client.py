# src/llm/aiPro_client.py
"""삼성 AI Pro LLM — LangChain BaseChatModel 커스텀 래퍼

T1-1_GUIDE.md §4.1 기반 구현.
AI Pro REST API를 LangChain 표준 인터페이스로 래핑하여
LangGraph 워크플로우에서 일관된 방식으로 호출 가능하게 한다.
"""
from __future__ import annotations
from typing import Any, Iterator, List, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
import httpx
import os


class AiProChatModel(BaseChatModel):
    """삼성 AI Pro LLM — LangChain BaseChatModel 래퍼

    환경변수:
        AIPRO_ENDPOINT: AI Pro API 엔드포인트 URL
        AIPRO_API_KEY: API 인증 키
        AIPRO_MODEL: 사용할 모델명 (기본: aiPro-default)
    """

    endpoint: str = ""
    api_key: str = ""
    model_name: str = "aiPro-default"
    temperature: float = 0.0
    max_tokens: int = 4096
    timeout: int = 60

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.endpoint = os.getenv("AIPRO_ENDPOINT", self.endpoint)
        self.api_key = os.getenv("AIPRO_API_KEY", self.api_key)

    def _convert_messages(self, messages: List[BaseMessage]) -> List[dict]:
        """LangChain 메시지 → AI Pro 요청 포맷 변환"""
        converted = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                converted.append({"role": "system", "content": msg.content})
            elif isinstance(msg, HumanMessage):
                converted.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                converted.append({"role": "assistant", "content": msg.content})
        return converted

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> ChatResult:
        payload = {
            "model": self.model_name,
            "messages": self._convert_messages(messages),
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if stop:
            payload["stop"] = stop

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=self.timeout, verify=False) as client:
            # verify=False: 사내 자체 서명 인증서 환경 대응
            # 보안팀 승인 후 사내 CA 인증서 경로로 교체 권장
            response = client.post(
                f"{self.endpoint}/v1/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

        content = data["choices"][0]["message"]["content"]
        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content=content))],
            llm_output={"model": self.model_name},
        )

    @property
    def _llm_type(self) -> str:
        return "aiPro"

    @property
    def _identifying_params(self) -> dict:
        return {"model_name": self.model_name, "endpoint": self.endpoint}
