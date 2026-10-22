"""광학 MCP 서버를 stdio로 연결하고 문서·도구 호출에 재사용한다."""
import asyncio
import json
import os
import sys
from contextlib import AsyncExitStack
from pathlib import Path

from langsmith import traceable
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_DIR = Path(__file__).parent.parent
DEFAULT_SERVER_SCRIPTS = {
    "optics": SERVER_DIR / "mcp_server.py",
}


def _attr(obj, *names):
    """mcp SDK 버전에 따라 pydantic 필드명이 camelCase(예: resourceTemplates,
    uriTemplate, 구버전 1.x)와 snake_case(예: resource_templates, uri_template,
    신버전 2.x)로 갈린다 — 이 프로젝트 안에도 시스템 python3(mcp 1.28.1, camelCase)와
    .venv(mcp 2.2.0, snake_case)가 섞여 있어 실행 환경마다 바뀐다. 둘 다 시도해서
    설치된 버전과 무관하게 동작하게 한다."""
    for name in names:
        if hasattr(obj, name):
            return getattr(obj, name)
    raise AttributeError(f"{type(obj).__name__!r} has none of {names!r}")


class MCPClient:
    def __init__(self, server_scripts: dict[str, Path] | None = None):
        """연결할 서버 목록·종료 스택·호출 잠금 상태를 준비한다.

        Args:
            server_scripts: 서버 논리 이름과 실행할 Python 스크립트 경로의 매핑.
        """
        self._server_scripts = server_scripts or DEFAULT_SERVER_SCRIPTS
        self._stack: AsyncExitStack | None = None
        self.sessions: dict[str, ClientSession] = {}
        self._lock = asyncio.Lock()
        self._templates = {}

    async def start(self) -> None:
        """MCP 서버 프로세스를 시작하고 초기화한 연결을 재사용하도록 보관한다.
        """
        self._stack = AsyncExitStack()
        for server_name, script in self._server_scripts.items():
            params = StdioServerParameters(
                command=sys.executable, args=[str(script)],
                env={**os.environ, "FASTMCP_LOG_LEVEL": "ERROR"})
            read, write = await self._stack.enter_async_context(stdio_client(params))
            session = await self._stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            self.sessions[server_name] = session

    async def stop(self) -> None:
        """종료 스택을 닫아 MCP 연결과 서버 프로세스를 정리한다.
        """
        if self._stack is not None:
            await self._stack.aclose()
            self._stack = None
            self.sessions = {}
            self._templates = {}

    @traceable(run_type="tool", name="mcp.call_tool")
    async def call_tool(self, name: str, arguments: dict, server: str = "optics") -> dict:
        """지정한 MCP 도구를 호출하고 JSON 텍스트 응답을 사전으로 변환한다.

        Args:
            name: 모델 표시 이름 또는 호출할 MCP capability 이름.
            arguments: MCP 도구·프롬프트에 전달할 인자 사전.
            server: 연결된 MCP 서버의 논리 이름.

        Returns:
            도구 JSON 응답을 파싱한 사전.
        """
        result = await self.sessions[server].call_tool(name, arguments)
        return json.loads(result.content[0].text)

    @traceable(run_type="tool", name="mcp.list_resource_templates")
    async def list_resource_templates(self, server: str) -> list:
        """한 MCP 서버가 제공하는 리소스 URI 템플릿 목록을 조회한다.

        Args:
            server: 연결된 MCP 서버의 논리 이름.

        Returns:
            리소스 템플릿 객체 목록.
        """
        async with self._lock:
            result = await self.sessions[server].list_resource_templates()
        return _attr(result, "resourceTemplates", "resource_templates")

    @traceable(run_type="tool", name="mcp.find_resource_template")
    async def find_resource_template(self, template_name: str) -> tuple[str, str]:
        """연결된 서버들을 순서대로 조회해 template_name을 제공하는 서버를 찾는다."""
        if template_name in self._templates:
            return self._templates[template_name]
        for server_name in self.sessions:
            templates = await self.list_resource_templates(server_name)
            matched = next((t for t in templates if t.name == template_name), None)
            if matched is not None:
                found=(server_name, _attr(matched, "uriTemplate", "uri_template"))
                self._templates[template_name]=found
                return found
        raise ValueError(
            f"MCP resource template not found on any connected server: {template_name}")

    @traceable(run_type="tool", name="mcp.read_resource")
    async def read_resource(self, uri: str, server: str) -> str:
        """발견한 서버의 리소스 URI에서 문서 본문을 읽는다.

        Args:
            uri: 조회할 MCP 리소스 URI.
            server: 연결된 MCP 서버의 논리 이름.

        Returns:
            리소스 문서의 텍스트.
        """
        result = await self.sessions[server].read_resource(uri)
        return result.contents[0].text
