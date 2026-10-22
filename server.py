"""광학 도우미 FastAPI 서버. 모델·MCP·세션을 초기화하고 REST/SSE로 답변한다."""
import json
import os
import httpx
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()   # LANGCHAIN_TRACING_V2 / API_KEY / PROJECT — import보다 먼저

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from langsmith import traceable
from langsmith.run_helpers import get_current_run_tree
from pydantic import BaseModel

from agent.deps import SupervisorDeps
from agent.fake_llm import FastLLM, QualityLLM
from agent.graph import build_graph
from agent.mcp_client import MCPClient
from agent.session_store import SqliteSessionStore

CREATION_COUNT = 0


class ChatRequest(BaseModel):
    message: str
    thread_id: str = "default"


def _build_llms():
    """LLM_BACKEND=fake(기본, 결정론) | ollama(로컬 실모델) | openai(실제 OpenAI API)."""
    backend = os.environ.get("LLM_BACKEND", "fake")
    if backend == "ollama":
        from agent.ollama_llm import OllamaFastLLM, OllamaQualityLLM
        fast = OllamaFastLLM(os.environ.get("OLLAMA_FAST_MODEL", "qwen3:0.6b"),
                             usd_per_1k_tokens=0.00015)
        quality = OllamaQualityLLM(os.environ.get("OLLAMA_QUALITY_MODEL", "qwen3:8b"),
                                   usd_per_1k_tokens=0.005)
        return backend, fast, quality
    if backend == "openai":
        from agent.openai_llm import OpenAIFastLLM, OpenAIQualityLLM
        fast = OpenAIFastLLM(os.environ.get("OPENAI_FAST_MODEL", "gpt-4o-mini"),
                             usd_per_1k_tokens=0.00015)
        quality = OpenAIQualityLLM(os.environ.get("OPENAI_QUALITY_MODEL", "gpt-4o"),
                                   usd_per_1k_tokens=0.005)
        return backend, fast, quality
    fast = FastLLM("fast-model-stub", usd_per_1k_tokens=0.00015)
    quality = QualityLLM("quality-model-stub", usd_per_1k_tokens=0.005)
    return backend, fast, quality


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작 시 MCP·모델·그래프·저장소를 생성하고 종료 시 자원을 정리한다.

    Args:
        app: 자원을 연결하고 보관할 FastAPI 앱.
    """
    global CREATION_COUNT
    CREATION_COUNT += 1
    mcp = MCPClient()
    await mcp.start()
    backend, fast_llm, quality_llm = _build_llms()
    app.state.llm_backend = backend
    deps = SupervisorDeps(
        fast_llm=fast_llm,
        quality_llm=quality_llm,
        mcp=mcp,
        session_store=SqliteSessionStore(),
        version="v2",
    )
    app.state.deps = deps
    app.state.graph = build_graph(deps)
    app.state.instance_id = id(deps)
    yield
    await mcp.stop()
    deps.session_store.close()
    try:   # 종료 전 LangSmith 배치 전송 플러시 — kill 시 run이 pending으로 남는 것 방지
        from langchain_core.tracers.langchain import wait_for_all_tracers
        wait_for_all_tracers()
    except Exception:
        pass


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health():
    """현재 서버 인스턴스·모델·Supervisor 구성 정보를 반환한다.

    Returns:
        실행 구성과 서버 상태 사전.
    """
    return {"status": "ok", "instance_id": app.state.instance_id,
            "creation_count": CREATION_COUNT,
            "supervisor_version": app.state.deps.version,
            "llm_backend": app.state.llm_backend,
            "fast_llm": app.state.deps.fast_llm.name,
            "quality_llm": app.state.deps.quality_llm.name}


@app.get("/version")
async def version():
    """실행 중인 Supervisor 버전을 반환한다.

    Returns:
        Supervisor 버전 사전.
    """
    return {"supervisor_version": app.state.deps.version}


def _metadata(result: dict, run_id: str | None) -> dict:
    """그래프 결과에서 화면·관측용 실행 메타데이터를 추출한다.

    Args:
        result: Supervisor 실행 결과 사전.
        run_id: 요청에 연결된 추적 ID. 추적하지 않으면 None.

    Returns:
        클라이언트에 제공할 실행 요약 사전.
    """
    return {
        "route": result.get("route"),
        "task_count": len(result.get("tasks", [])),
        "retry_count": result.get("retry_count", 0),
        "parallel_elapsed": result.get("parallel_elapsed"),
        "timings":result.get("timings",{}),
        "validation_attempts": result.get("validation_attempts", 0),
        "cost_usd": result.get("cost_usd", 0.0),
        "llm_backend": app.state.llm_backend,
        "supervisor_version": app.state.deps.version,
        "instance_id": app.state.instance_id,
        "langsmith_run_id": run_id,
    }


@traceable(name="chat_request")
async def _handle_chat(message: str, thread_id: str) -> tuple[dict, str | None]:
    """이력을 불러와 선택한 Supervisor를 실행하고 완료된 대화를 저장한다.

    Args:
        message: 사용자가 보낸 채팅 메시지.
        thread_id: 대화를 구분하는 식별자.

    Returns:
        Supervisor 결과와 추적 ID의 튜플.
    """
    deps = app.state.deps
    history = deps.session_store.load(thread_id)
    result = await app.state.graph.ainvoke(
        {"query": message, "thread_id": thread_id, "history": history,
         "events": [], "cost_usd": 0.0})
    deps.session_store.append(thread_id, "user", message)
    deps.session_store.append(thread_id, "assistant", result["final"])
    rt = get_current_run_tree()
    return result, (str(rt.id) if rt else None)


@app.post("/chat")
async def chat(req: ChatRequest):
    """일반 HTTP 채팅을 실행하고 답변·이벤트·메타데이터를 반환한다.

    Args:
        req: JSON 요청 본문을 읽을 HTTP 요청.

    Returns:
        답변·실행 이벤트·모델 정보 사전.
    """
    result, run_id = await _handle_chat(req.message, req.thread_id)
    return {"reply": result["final"], "events": result.get("events", []),
            "metadata": _metadata(result, run_id)}


@app.get("/chat/stream")
async def chat_stream(request: Request, message: str, thread_id: str = "default"):
    """처리 이벤트·답변을 SSE로 전달한다."""
    deps = app.state.deps

    async def gen():
        """그래프 이벤트·토큰·최종 답변을 SSE로 변환하고 완료된 대화만 저장한다.

        Yields:
            순서대로 전달할 SSE 텍스트 또는 원본 바이트 조각.
        """
        history = deps.session_store.load(thread_id)
        seen = 0
        final = ""
        last_prompt = None   # finalize까지 살아남은 최종 write/chat 호출의 실제 프롬프트
        # stream_mode를 리스트로 주면 (mode, payload) 튜플이 나온다 — "updates"는
        # 노드가 끝날 때마다의 상태 델타, "custom"은 write_node/chat_answer_node가
        # get_stream_writer()로 실행 중에 즉시 흘려보내는 토큰(AnswerToken) 이벤트다.
        async for mode, payload in app.state.graph.astream(
                {"query": message, "thread_id": thread_id, "history": history,
                 "events": [], "cost_usd": 0.0}, stream_mode=["updates", "custom"]):
            if mode == "custom":
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                continue
            for node_name, delta in payload.items():
                if not delta:
                    continue
                for ev in (delta.get("events") or [])[seen:]:
                    ev = {**ev, "node": node_name}
                    yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
                if delta.get("events"):
                    seen = len(delta["events"])
                if delta.get("final"):
                    final = delta["final"]
                if delta.get("last_prompt"):
                    last_prompt = delta["last_prompt"]
        yield f"data: {json.dumps({'type': 'FinalAnswer', 'reply': final, 'prompt': last_prompt}, ensure_ascii=False)}\n\n"
        # 중지/연결 종료된 응답은 다음 질문의 대화 이력에 포함하지 않는다.
        if await request.is_disconnected():
            return
        deps.session_store.append(thread_id, "user", message)
        deps.session_store.append(thread_id, "assistant", final)
        yield "data: [DONE]\n\n"

    async def guarded():
        try:
            async for chunk in gen():
                yield chunk
        except Exception as exc:
            status=getattr(getattr(exc,"response",None),"status_code",None)
            if status in (401,403):
                message="모델 API 인증 또는 접근 권한 오류입니다. 서버의 API 키·모델 권한을 확인하세요."
            elif status==429:
                message="모델 API의 사용량 또는 요청 한도에 도달했습니다. 계정 사용량을 확인하세요."
            elif isinstance(exc,httpx.TimeoutException):
                message="모델 응답 시간이 초과되었습니다. 모델 실행 상태를 확인한 뒤 다시 시도하세요."
            else:
                message="답변 처리 중 서버 오류가 발생했습니다. 백엔드를 재시작하고 다시 시도하세요."
            # 예외 본문은 키·요청 내용을 포함할 수 있으므로 전송하지 않는다.
            print(f"chat_stream failed: {type(exc).__name__}, status={status}",flush=True)
            yield "data: "+json.dumps({"type":"Error","message":message,"code":type(exc).__name__},ensure_ascii=False)+"\n\n"
            yield "data: [DONE]\n\n"
    return StreamingResponse(guarded(), media_type="text/event-stream",headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8100, log_level="warning")
