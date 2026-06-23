# T1-1. 개발·운영 환경 셋업 — 수행 가이드

> **과제**: 프로그램 개발 전주기 지원 AI Agent  
> **Task**: T1-1. LLM API, LangGraph, 벡터DB, 임베딩 모델 설치  
> **환경**: 삼성SDS 사내망 (SCP/VDI) · AI Pro (내부 LLM) · Febrix API (벡터DB)  
> **선행 조건**: SCP 프로젝트 생성 완료, AI Pro API 키 발급, Febrix API 접근 권한 확보

---

## 1. 개요

### 1.1 목적

본 가이드는 프로그램 개발 전주기 지원 AI Agent 구축을 위한 **기반 실행 환경**을 사내망 제약 내에서 완성하는 절차를 정의한다.  
외부 인터넷이 차단된 SCP/VDI 환경에서 AI Pro LLM, Febrix 벡터DB, LangGraph 오케스트레이션 프레임워크, 임베딩 파이프라인이 **정상 연동되는 상태**를 목표로 한다.

### 1.2 구성 요소 및 기술 선택 근거

| 구성 요소 | 선택 기술 | 선택 근거 |
|-----------|-----------|-----------|
| LLM | 삼성 AI Pro API | 사내망 환경 유일 승인 LLM, 외부 API 반출 불가 정책 준수 |
| 벡터DB | Febrix API | SDS 사내 승인 벡터 검색 서비스, 별도 인프라 구축 불필요 |
| 임베딩 모델 | AI Pro 임베딩 엔드포인트 또는 사내 승인 모델 | 사내망 외부 모델 호출 불가, 동일 API 엔드포인트 활용 |
| Agent 오케스트레이션 | LangGraph | DAG 기반 상태 머신, Conditional Routing, State 관리 필수 (단순 Chain 불가) |
| 런타임 | Python 3.11+ | LangGraph 공식 지원 버전 |
| 패키지 관리 | pip + 사내 PyPI 미러 | SCP 환경 외부 PyPI 차단, 사내 미러 경유 필수 |

### 1.3 완료 기준 (Definition of Done)

- [ ] AI Pro LLM API 호출 성공 (테스트 프롬프트 응답 확인)
- [ ] Febrix API 컬렉션 생성·벡터 적재·검색 성공
- [ ] 임베딩 모델 호출 → 벡터 반환 확인
- [ ] LangGraph 설치 및 기본 DAG 실행 성공
- [ ] 전체 컴포넌트 연동 스모크 테스트 통과
- [ ] `.env` 환경변수 파일 및 `config.yaml` 기본 설정 완성

---

## 2. 사전 준비

### 2.1 필요 권한 및 계정

```
체크리스트
□ SCP 프로젝트 접근 권한 (담당 인프라팀 요청)
□ AI Pro API 키 발급 (AI Pro 포털 → API 키 관리)
□ Febrix API 접근 토큰 발급 (Febrix 관리 포털 또는 담당팀 요청)
□ 사내 PyPI 미러 주소 확인 (예: http://pypi.sds.samsung.net/simple)
□ GitHub Enterprise 접근 계정 (코드 형상관리용)
□ SCP 내 Python 3.11+ 런타임 또는 VM 할당 확인
```

### 2.2 네트워크 환경 확인

사내망에서는 외부 PyPI, Hugging Face, GitHub.com 등이 **차단**된다.  
아래 사항을 사전에 확인한다.

```bash
# 사내 PyPI 미러 응답 확인
curl -I http://<사내-pypi-미러-주소>/simple/langchain/

# AI Pro API 엔드포인트 응답 확인
curl -I https://<aiPro-endpoint>/v1/health

# Febrix API 엔드포인트 응답 확인
curl -I https://<febrix-endpoint>/api/v1/health
```

> **⚠️ 주의**: 엔드포인트 주소는 AI Pro 포털 및 Febrix 포털에서 확인.  
> 응답 없을 경우 사내 네트워크팀에 화이트리스트 등록 요청 필요.

---

## 3. Python 환경 구성

### 3.1 가상환경 생성

```bash
# Python 버전 확인 (3.11 이상 필요)
python --version

# 프로젝트 디렉토리 생성
mkdir -p ~/projects/dev-lifecycle-agent
cd ~/projects/dev-lifecycle-agent

# 가상환경 생성 및 활성화
python -m venv .venv
source .venv/bin/activate          # Linux/Mac
# .venv\Scripts\activate           # Windows
```

### 3.2 사내 PyPI 미러 설정

외부 PyPI 차단 환경에서는 pip 설정을 사내 미러로 변경해야 한다.

```bash
# pip 전역 설정 변경
pip config set global.index-url http://<사내-pypi-미러>/simple/
pip config set global.trusted-host <사내-pypi-미러-호스트>

# 설정 확인
pip config list
```

또는 프로젝트 루트에 `pip.conf` (Linux) / `pip.ini` (Windows) 파일 생성:

```ini
# pip.conf
[global]
index-url = http://<사내-pypi-미러>/simple/
trusted-host = <사내-pypi-미러-호스트>
timeout = 60
```

### 3.3 필수 패키지 설치

```bash
# requirements.txt 생성
cat > requirements.txt << 'EOF'
# Agent 오케스트레이션
langgraph>=0.2.0
langchain>=0.3.0
langchain-core>=0.3.0

# API 통신
httpx>=0.27.0
requests>=2.32.0

# 환경변수 관리
python-dotenv>=1.0.0

# 설정 관리
pyyaml>=6.0.0

# 데이터 처리
pydantic>=2.0.0

# 로깅
structlog>=24.0.0

# 개발·테스트 도구
pytest>=8.0.0
pytest-asyncio>=0.23.0
EOF

# 설치
pip install -r requirements.txt
```

> **⚠️ 사내 미러에 없는 패키지 발생 시**  
> 인프라팀에 미러 등록 요청하거나, 허용된 경우 wheel 파일을 별도 반입.

---

## 4. AI Pro LLM 연동

### 4.1 API 클라이언트 구현

AI Pro는 사내 LLM으로 표준 REST API 형태로 제공된다.  
LangGraph와 연동하기 위해 LangChain의 `BaseChatModel`을 상속하여 **커스텀 LLM 클라이언트**를 구현한다.

```
📁 프로젝트 구조
dev-lifecycle-agent/
├── src/
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── aiPro_client.py      ← AI Pro 커스텀 클라이언트
│   │   └── config.py
│   ├── vectordb/
│   ├── agent/
│   └── skills/
├── tests/
├── config/
│   └── config.yaml
├── .env
└── requirements.txt
```

```python
# src/llm/aiPro_client.py
from __future__ import annotations
from typing import Any, Iterator, List, Optional
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
import httpx
import os


class AiProChatModel(BaseChatModel):
    """삼성 AI Pro LLM — LangChain BaseChatModel 래퍼"""

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
```

### 4.2 연동 테스트

```python
# tests/test_llm.py
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
```

```bash
# 테스트 실행
pytest tests/test_llm.py -v
```

---

## 5. 임베딩 모델 연동

### 5.1 임베딩 클라이언트 구현

사내망에서는 Hugging Face 등 외부 모델 로드가 불가하므로,  
AI Pro의 **임베딩 전용 엔드포인트**를 활용하거나 Febrix 내장 임베딩을 사용한다.

```python
# src/llm/embedding_client.py
from __future__ import annotations
from typing import List
from langchain_core.embeddings import Embeddings
import httpx
import os


class AiProEmbeddings(Embeddings):
    """AI Pro 임베딩 엔드포인트 클라이언트"""

    endpoint: str = ""
    api_key: str = ""
    model_name: str = "aiPro-embedding"
    batch_size: int = 32     # 사내 API 배치 제한에 맞게 조정
    timeout: int = 30

    def __init__(self, **kwargs):
        # pydantic v2 호환
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.endpoint = os.getenv("AIPRO_ENDPOINT", self.endpoint)
        self.api_key = os.getenv("AIPRO_API_KEY", self.api_key)

    def _call_api(self, texts: List[str]) -> List[List[float]]:
        payload = {"model": self.model_name, "input": texts}
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=self.timeout, verify=False) as client:
            response = client.post(
                f"{self.endpoint}/v1/embeddings",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()
        # OpenAI 호환 포맷 가정: data["data"][i]["embedding"]
        return [item["embedding"] for item in data["data"]]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """문서 임베딩 (배치 처리)"""
        results = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i: i + self.batch_size]
            results.extend(self._call_api(batch))
        return results

    def embed_query(self, text: str) -> List[float]:
        """쿼리 임베딩 (단건)"""
        return self._call_api([text])[0]
```

> **⚠️ Febrix 내장 임베딩 사용 시**  
> Febrix API가 텍스트 입력 → 임베딩 자동 처리를 지원하는 경우,  
> 별도 임베딩 클라이언트 없이 Febrix에 텍스트 직접 적재 가능.  
> Febrix API 문서 확인 후 방식 결정.

### 5.2 임베딩 테스트

```python
# tests/test_embedding.py
from src.llm.embedding_client import AiProEmbeddings


def test_embed_single():
    emb = AiProEmbeddings()
    vector = emb.embed_query("CR 요구사항 분석")
    assert isinstance(vector, list)
    assert len(vector) > 0
    assert all(isinstance(v, float) for v in vector)
    print(f"✅ 임베딩 차원: {len(vector)}")


def test_embed_batch():
    emb = AiProEmbeddings()
    texts = ["프로그램 마스터 등록", "테이블 스키마 변경", "Oracle 딕셔너리 조회"]
    vectors = emb.embed_documents(texts)
    assert len(vectors) == 3
    assert len(vectors[0]) == len(vectors[1])   # 차원 동일
    print(f"✅ 배치 임베딩 성공: {len(vectors)}건, 차원 {len(vectors[0])}")
```

---

## 6. Febrix 벡터DB 연동

### 6.1 Febrix API 클라이언트 구현

Febrix는 SDS 사내 벡터 검색 서비스다.  
LangChain의 `VectorStore`를 상속하여 **LangGraph Skill에서 표준 인터페이스**로 사용 가능하게 구현한다.

```python
# src/vectordb/febrix_client.py
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
from langchain_core.vectorstores import VectorStore
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
import httpx
import os
import uuid


class FebrixVectorStore(VectorStore):
    """Febrix 사내 벡터DB — LangChain VectorStore 래퍼"""

    def __init__(
        self,
        collection_name: str,
        embedding: Embeddings,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 30,
    ):
        self.collection_name = collection_name
        self.embedding = embedding
        self.endpoint = endpoint or os.getenv("FEBRIX_ENDPOINT", "")
        self.api_key = api_key or os.getenv("FEBRIX_API_KEY", "")
        self.timeout = timeout
        self._base_url = f"{self.endpoint}/api/v1"
        self._headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{self._base_url}{path}"
        with httpx.Client(timeout=self.timeout, verify=False) as client:
            response = getattr(client, method)(url, headers=self._headers, **kwargs)
            response.raise_for_status()
            return response.json()

    # ── 컬렉션 관리 ──────────────────────────────────────────

    def create_collection(self, dimension: int = 1536) -> dict:
        """컬렉션 생성 (없을 경우 초기 1회 실행)"""
        return self._request(
            "post",
            "/collections",
            json={
                "name": self.collection_name,
                "dimension": dimension,
                "metric": "cosine",      # 코사인 유사도
            },
        )

    def get_or_create_collection(self, dimension: int = 1536) -> dict:
        """컬렉션 존재 여부 확인 후 없으면 생성"""
        try:
            return self._request("get", f"/collections/{self.collection_name}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return self.create_collection(dimension)
            raise

    # ── 벡터 적재 ────────────────────────────────────────────

    def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[dict]] = None,
        ids: Optional[List[str]] = None,
        **kwargs,
    ) -> List[str]:
        """텍스트 → 임베딩 → Febrix 적재"""
        if not ids:
            ids = [str(uuid.uuid4()) for _ in texts]
        if not metadatas:
            metadatas = [{} for _ in texts]

        vectors = self.embedding.embed_documents(texts)

        points = [
            {
                "id": id_,
                "vector": vector,
                "payload": {**meta, "text": text},
            }
            for id_, vector, text, meta in zip(ids, vectors, texts, metadatas)
        ]

        self._request(
            "post",
            f"/collections/{self.collection_name}/points",
            json={"points": points},
        )
        return ids

    def add_documents(self, documents: List[Document], **kwargs) -> List[str]:
        """Document 객체 리스트 적재"""
        texts = [doc.page_content for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        return self.add_texts(texts, metadatas=metadatas, **kwargs)

    # ── 벡터 검색 ────────────────────────────────────────────

    def similarity_search(
        self, query: str, k: int = 5, filter: Optional[dict] = None, **kwargs
    ) -> List[Document]:
        docs_and_scores = self.similarity_search_with_score(
            query, k=k, filter=filter, **kwargs
        )
        return [doc for doc, _ in docs_and_scores]

    def similarity_search_with_score(
        self, query: str, k: int = 5, filter: Optional[dict] = None, **kwargs
    ) -> List[Tuple[Document, float]]:
        query_vector = self.embedding.embed_query(query)

        payload: Dict[str, Any] = {
            "vector": query_vector,
            "top": k,
            "with_payload": True,
        }
        if filter:
            payload["filter"] = filter

        result = self._request(
            "post",
            f"/collections/{self.collection_name}/points/search",
            json=payload,
        )

        docs_with_scores = []
        for hit in result.get("result", []):
            payload_data = hit.get("payload", {})
            text = payload_data.pop("text", "")
            doc = Document(page_content=text, metadata=payload_data)
            score = hit.get("score", 0.0)
            docs_with_scores.append((doc, score))

        return docs_with_scores

    @classmethod
    def from_texts(
        cls,
        texts: List[str],
        embedding: Embeddings,
        metadatas: Optional[List[dict]] = None,
        collection_name: str = "default",
        **kwargs,
    ) -> "FebrixVectorStore":
        store = cls(
            collection_name=collection_name,
            embedding=embedding,
            **kwargs,
        )
        store.get_or_create_collection()
        store.add_texts(texts, metadatas=metadatas)
        return store
```

### 6.2 컬렉션 설계

Agent에서 사용할 컬렉션을 용도별로 분리한다.

```python
# src/vectordb/collections.py

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
```

### 6.3 Febrix 연동 테스트

```python
# tests/test_febrix.py
import pytest
from src.vectordb.febrix_client import FebrixVectorStore
from src.llm.embedding_client import AiProEmbeddings
from langchain_core.documents import Document


@pytest.fixture
def store():
    emb = AiProEmbeddings()
    s = FebrixVectorStore(
        collection_name="dev_agent_test",
        embedding=emb,
    )
    s.get_or_create_collection()
    return s


def test_add_and_search(store):
    docs = [
        Document(
            page_content="프로그램마스터 등록 누락 시 운영 이관 오류 발생",
            metadata={"source": "cr_history", "cr_id": "CR-001", "type": "incident"},
        ),
        Document(
            page_content="테이블마스터 미등록으로 Oracle 딕셔너리 정합성 불일치",
            metadata={"source": "cr_history", "cr_id": "CR-002", "type": "incident"},
        ),
        Document(
            page_content="신규 화면 개발 시 통합용어사전 미등록 용어 사용",
            metadata={"source": "cr_history", "cr_id": "CR-003", "type": "standard"},
        ),
    ]
    ids = store.add_documents(docs)
    assert len(ids) == 3
    print(f"✅ 적재 완료: {ids}")

    # 유사 검색
    results = store.similarity_search("마스터 등록 누락 문제", k=2)
    assert len(results) > 0
    print(f"✅ 검색 결과: {results[0].page_content[:80]}")


def test_search_with_filter(store):
    results = store.similarity_search_with_score(
        "Oracle 딕셔너리",
        k=3,
        filter={"type": {"$eq": "incident"}},
    )
    assert isinstance(results, list)
    for doc, score in results:
        print(f"  score={score:.4f}: {doc.page_content[:60]}")
```

---

## 7. LangGraph 기반 Agent 뼈대 구현

### 7.1 기본 DAG 구조 검증

T1-1 단계에서는 실제 Skill을 붙이기 전에 **LangGraph 정상 동작**을 확인하는 뼈대(Scaffold)를 구현한다.

```python
# src/agent/scaffold.py
from __future__ import annotations
from typing import TypedDict, Annotated, List
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from src.llm.aiPro_client import AiProChatModel


# ── State 정의 ──────────────────────────────────────────────
class AgentState(TypedDict):
    """Agent 전역 상태 — 각 Skill이 읽고 업데이트"""
    messages: Annotated[List[BaseMessage], add_messages]
    cr_id: str
    cr_type: str            # "new_dev" | "feature_change" | "db_change"
    current_step: str
    gate_results: dict      # {step_name: bool}
    artifacts: dict         # 생성된 산출물 모음


# ── 노드 함수 정의 (Scaffold — 실 Skill은 T3에서 구현) ─────
def route_by_cr_type(state: AgentState) -> str:
    """CR 유형에 따라 다음 노드 결정 (Conditional Routing)"""
    cr_type = state.get("cr_type", "new_dev")
    routing_map = {
        "new_dev": "requirement_skill",
        "feature_change": "requirement_skill",
        "db_change": "impact_analysis_skill",
    }
    return routing_map.get(cr_type, "requirement_skill")


def requirement_skill_stub(state: AgentState) -> AgentState:
    """요구사항 구체화 Skill (Stub)"""
    print(f"[T3-3 예정] 요구사항 구체화 실행: CR={state['cr_id']}")
    state["current_step"] = "requirement_done"
    state["gate_results"]["requirement"] = True
    return state


def gate_check(state: AgentState) -> AgentState:
    """관리 포인트 게이트 점검 (Stub)"""
    print(f"[T3-9 예정] 게이트 점검: {state['gate_results']}")
    all_passed = all(state["gate_results"].values())
    state["gate_results"]["gate_check"] = all_passed
    return state


def check_gate_result(state: AgentState) -> str:
    """게이트 결과에 따른 분기"""
    return "end" if state["gate_results"].get("gate_check") else "gate_failed"


# ── 그래프 조립 ─────────────────────────────────────────────
def build_scaffold_graph():
    graph = StateGraph(AgentState)

    graph.add_node("requirement_skill", requirement_skill_stub)
    graph.add_node("impact_analysis_skill", requirement_skill_stub)  # T3에서 교체
    graph.add_node("gate_check", gate_check)

    # 진입점 → CR 유형 라우팅
    graph.set_conditional_entry_point(
        route_by_cr_type,
        {
            "requirement_skill": "requirement_skill",
            "impact_analysis_skill": "impact_analysis_skill",
        },
    )

    graph.add_edge("requirement_skill", "gate_check")
    graph.add_edge("impact_analysis_skill", "gate_check")
    graph.add_conditional_edges(
        "gate_check",
        check_gate_result,
        {"end": END, "gate_failed": END},  # T3에서 실패 분기 구체화
    )

    return graph.compile()


# ── 실행 예시 ────────────────────────────────────────────────
if __name__ == "__main__":
    app = build_scaffold_graph()
    initial_state: AgentState = {
        "messages": [HumanMessage(content="신규 화면 개발 요청")],
        "cr_id": "CR-2026-001",
        "cr_type": "new_dev",
        "current_step": "start",
        "gate_results": {},
        "artifacts": {},
    }
    result = app.invoke(initial_state)
    print("최종 State:", result)
```

### 7.2 LangGraph 뼈대 테스트

```python
# tests/test_scaffold.py
from src.agent.scaffold import build_scaffold_graph, AgentState
from langchain_core.messages import HumanMessage


def test_new_dev_routing():
    app = build_scaffold_graph()
    state = AgentState(
        messages=[HumanMessage(content="신규 화면")],
        cr_id="CR-001", cr_type="new_dev",
        current_step="start", gate_results={}, artifacts={},
    )
    result = app.invoke(state)
    assert result["gate_results"].get("requirement") is True
    print("✅ 신규개발 라우팅 정상")


def test_db_change_routing():
    app = build_scaffold_graph()
    state = AgentState(
        messages=[HumanMessage(content="DB 스키마 변경")],
        cr_id="CR-002", cr_type="db_change",
        current_step="start", gate_results={}, artifacts={},
    )
    result = app.invoke(state)
    assert result["current_step"] == "requirement_done"
    print("✅ DB 변경 라우팅 정상")
```

---

## 8. 환경변수 및 설정 파일

### 8.1 `.env` 파일

```dotenv
# .env  (형상관리 제외 — .gitignore에 추가)

# ── AI Pro LLM ─────────────────────────────
AIPRO_ENDPOINT=https://<aiPro-endpoint>
AIPRO_API_KEY=<발급받은-api-key>
AIPRO_MODEL=aiPro-default
AIPRO_EMBEDDING_MODEL=aiPro-embedding

# ── Febrix 벡터DB ───────────────────────────
FEBRIX_ENDPOINT=https://<febrix-endpoint>
FEBRIX_API_KEY=<발급받은-api-key>

# ── GitHub Enterprise ──────────────────────
GITHUB_ENTERPRISE_URL=https://<사내-github-url>
GITHUB_TOKEN=<github-pat>

# ── Confluence ─────────────────────────────
CONFLUENCE_URL=https://<confluence-url>
CONFLUENCE_TOKEN=<api-token>

# ── Oracle 19c ─────────────────────────────
ORACLE_DSN=<host>:<port>/<service_name>
ORACLE_USER=<readonly-user>
ORACLE_PASSWORD=<password>

# ── 로그 레벨 ──────────────────────────────
LOG_LEVEL=INFO
```

### 8.2 `config/config.yaml`

```yaml
# config/config.yaml

llm:
  model: ${AIPRO_MODEL}
  temperature: 0.0
  max_tokens: 4096
  timeout: 60

embedding:
  model: ${AIPRO_EMBEDDING_MODEL}
  batch_size: 32
  dimension: 1536        # AI Pro 임베딩 실측 후 수정

vectordb:
  collections:
    github_code:
      name: dev_agent_github_code
      top_k: 5
    confluence_docs:
      name: dev_agent_confluence_docs
      top_k: 5
    cr_history:
      name: dev_agent_cr_history
      top_k: 3
  cache_ttl_seconds: 3600

rag:
  bm25_weight: 0.3       # 키워드 검색 가중치
  dense_weight: 0.7      # 벡터 검색 가중치
  reranker_top_k: 10     # Reranker 입력 후보 수
  final_top_k: 5         # 최종 반환 문서 수

agent:
  max_steps: 20          # 무한 루프 방지
  timeout_seconds: 120

gate:
  config_path: config/gate_rules.yaml

logging:
  level: INFO
  format: json
```

### 8.3 `.gitignore`

```
.env
*.pyc
__pycache__/
.venv/
*.log
.pytest_cache/
```

---

## 9. 스모크 테스트 (전체 연동 확인)

모든 컴포넌트가 정상 설치·연동되었는지 한 번에 확인하는 통합 테스트다.

```python
# tests/test_smoke.py
"""
T1-1 완료 기준 검증 스모크 테스트
모든 테스트 통과 시 T1-2(시스템 연동 인터페이스 설계)로 진행
"""
import pytest
from langchain_core.messages import HumanMessage


def test_01_aiPro_llm():
    """AI Pro LLM 호출 성공"""
    from src.llm.aiPro_client import AiProChatModel
    llm = AiProChatModel()
    result = llm._generate([HumanMessage(content="ping")])
    assert result.generations[0].message.content
    print("✅ [1/5] AI Pro LLM 정상")


def test_02_embedding():
    """임베딩 모델 벡터 반환"""
    from src.llm.embedding_client import AiProEmbeddings
    emb = AiProEmbeddings()
    vec = emb.embed_query("테스트")
    assert len(vec) > 0
    print(f"✅ [2/5] 임베딩 정상 (dim={len(vec)})")


def test_03_febrix_collection():
    """Febrix 컬렉션 생성·확인"""
    from src.vectordb.febrix_client import FebrixVectorStore
    from src.llm.embedding_client import AiProEmbeddings
    store = FebrixVectorStore("smoke_test_collection", AiProEmbeddings())
    result = store.get_or_create_collection()
    assert result is not None
    print("✅ [3/5] Febrix 컬렉션 정상")


def test_04_febrix_search():
    """Febrix 적재·검색 왕복"""
    from src.vectordb.febrix_client import FebrixVectorStore
    from src.llm.embedding_client import AiProEmbeddings
    from langchain_core.documents import Document
    store = FebrixVectorStore("smoke_test_collection", AiProEmbeddings())
    store.add_documents([Document(page_content="스모크 테스트 문서")])
    results = store.similarity_search("스모크 테스트", k=1)
    assert len(results) > 0
    print("✅ [4/5] Febrix 검색 정상")


def test_05_langgraph_scaffold():
    """LangGraph 뼈대 DAG 실행"""
    from src.agent.scaffold import build_scaffold_graph, AgentState
    app = build_scaffold_graph()
    result = app.invoke(AgentState(
        messages=[HumanMessage(content="테스트")],
        cr_id="SMOKE-001", cr_type="new_dev",
        current_step="start", gate_results={}, artifacts={},
    ))
    assert result["gate_results"].get("gate_check") is True
    print("✅ [5/5] LangGraph DAG 정상")
```

```bash
# 전체 스모크 테스트 실행
pytest tests/test_smoke.py -v --tb=short

# 기대 출력
# ✅ [1/5] AI Pro LLM 정상
# ✅ [2/5] 임베딩 정상 (dim=1536)
# ✅ [3/5] Febrix 컬렉션 정상
# ✅ [4/5] Febrix 검색 정상
# ✅ [5/5] LangGraph DAG 정상
# 5 passed in X.XXs
```

---

## 10. 트러블슈팅

| 증상 | 원인 | 조치 |
|------|------|------|
| `pip install` 타임아웃 | 사내 PyPI 미러 미설정 | `pip config set global.index-url` 재확인 |
| AI Pro API 401 Unauthorized | API 키 만료 또는 환경변수 미로드 | `.env` 로드 확인, API 키 재발급 |
| AI Pro API SSL 오류 | 사내 자체 서명 인증서 | `verify=False` 임시 적용 후 보안팀에 CA 인증서 요청 |
| Febrix 404 Not Found | 컬렉션 미생성 | `get_or_create_collection()` 선행 호출 확인 |
| Febrix 차원 불일치 | 임베딩 모델 차원 != 컬렉션 설정 차원 | `test_02_embedding` 실측 차원으로 `config.yaml` 수정 |
| LangGraph import 오류 | `langgraph` 버전 불일치 | `pip install "langgraph>=0.2.0"` 재설치 |
| Oracle 접속 오류 | `cx_Oracle` 드라이버 또는 TNS 미설정 | Oracle Instant Client 설치, `tnsnames.ora` 확인 |

---

## 11. Task 완료 체크리스트

```
T1-1 완료 기준
□ .env 파일 작성 및 모든 환경변수 값 입력 완료
□ requirements.txt 기반 패키지 설치 완료 (사내 미러 경유)
□ test_smoke.py 5개 테스트 전원 통과 (pytest -v)
□ config/config.yaml 실측값(임베딩 차원 등) 반영 완료
□ .gitignore에 .env 추가 및 GitHub Enterprise push 완료
□ 트러블슈팅 이슈 발생 시 해결 내용 Confluence 기록

→ 전원 체크 완료 시 T1-2(시스템 연동 인터페이스 설계)로 진행
```

---

*작성일: 2026-06 | 버전: v1.0 | 담당: 중공업IT파트*