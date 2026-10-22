"""그래프 노드에 모델·MCP·대화 저장소를 주입하는 구성 객체."""
from dataclasses import dataclass
from typing import Any


@dataclass
class SupervisorDeps:
    fast_llm: Any
    quality_llm: Any
    mcp: Any
    session_store: Any
    version: str
