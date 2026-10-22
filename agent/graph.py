"""광학 질문 처리 그래프: 분류 → 계획 → 문서 조회 → 외부 검색 → 계산 → 작성 → 검수."""
import asyncio
import time
from functools import partial
from typing import TypedDict

from langgraph.config import get_stream_writer
from langgraph.graph import END, StateGraph
from langsmith import traceable

from .optics_calculations import plan_calculation, format_calculation
from .deps import SupervisorDeps
from .retry import with_retry
from .optics import optical_targets, answer_mode, answer_policy, answer_violations, user_question
from .web_search import needs_web_search
from .answer_context import compact_sources, normalize_answer, completed_answer_excerpt


class AgentState(TypedDict, total=False):
    query: str
    optics_targets: list[str]
    optics_mode: str
    calculation_request: dict | None
    calculation_result: dict | None
    thread_id: str
    history: list[dict]
    route: str
    tasks: list[dict]
    collected: list[dict]
    retry_count: int
    parallel_elapsed: float
    draft: str
    validation_attempts: int
    validation_feedback: str
    final: str
    last_prompt: str
    cost_usd: float
    events: list[dict]
    timings: dict
    generation_incomplete: bool


def _cost(state: AgentState, usage: dict) -> float:
    """이번 호출의 추정 비용을 그래프의 누적 비용에 더한다.

    Args:
        state: 현재 질문, 작업 목록, 수집 결과와 이벤트를 담은 그래프 상태.
        usage: 이번 모델 호출의 토큰 수와 추정 비용 정보.

    Returns:
        추정 누적 비용(USD).
    """
    return round(state.get("cost_usd", 0.0) + usage["usd"], 6)


@traceable(name="route_node")
async def route_node(state: AgentState, deps: SupervisorDeps) -> dict:
    """현재 질문을 기준으로 문서·계산·검색 경로를 선택한다."""
    calculation = plan_calculation(state["query"])
    targets = [calculation["document"]] if calculation else optical_targets(state["query"], state.get("history", []))
    if not targets and needs_web_search(state["query"]):
        targets = ["experiment-intake"]
    route = "optics" if targets else "chat"
    return {"route":route, "optics_targets":targets, "optics_mode":answer_mode(state["query"]),
            "calculation_request":calculation,
            "events":state.get("events",[])+[{"type":"RouteDecided","route":route}]}


@traceable(name="chat_answer_node")
async def chat_answer_node(state: AgentState, deps: SupervisorDeps) -> dict:
    """광학 문서가 필요 없는 일반 대화 경로."""
    writer = get_stream_writer()
    reply, usage = await deps.fast_llm.chat(
        state["query"], state.get("history", []),
        on_token=lambda piece: writer({"type": "AnswerToken", "delta": piece}))
    return {"final": reply, "last_prompt": usage.get("prompt"),
            "cost_usd": _cost(state, usage),
            "events": state["events"] + [{"type": "Finalize", "pipeline": "chat-direct"}]}


@traceable(name="plan_node")
async def plan_node(state: AgentState, deps: SupervisorDeps) -> dict:
    """질문에 선택된 광학 문서와 계산 작업만 계획한다."""
    targets=[] if state.get("calculation_request") else state.get("optics_targets",[])
    tasks=[{"id":f"optics-{i}","agent":"research","kind":"runbook","target":target,"status":"pending"}
           for i,target in enumerate(targets)]
    if state.get("calculation_request"):
        tasks.append({"id":"optics-calculation","agent":"calculation","kind":"calculation",
                      "target":state["calculation_request"]["operation"],"status":"pending"})
    return {"tasks":tasks,"events":state["events"]+[{"type":"PlanCreated","task_count":len(tasks),"targets":state.get("optics_targets",[])}]}


@traceable(name="research_node")
async def research_node(state: AgentState, deps: SupervisorDeps) -> dict:
    """선택한 문서를 MCP로 조회한다. 독립 문서는 함께 요청한다."""
    tasks=state["tasks"]
    pending=[(i,t) for i,t in enumerate(tasks) if t["agent"]=="research" and t["status"]=="pending"]
    if not pending:
        return {}
    server,template=await deps.mcp.find_resource_template("get_optics_document")
    started=time.perf_counter()
    data=await asyncio.gather(*(deps.mcp.read_resource(template.format(topic=t["target"]),server=server) for _,t in pending))
    updated=[dict(t) for t in tasks]
    collected=list(state.get("collected",[]));events=list(state["events"])
    for (i,t),body in zip(pending,data):
        updated[i]["status"]="done"
        collected.append({"source":"runbook","data":body})
        events.append({"type":"TaskCompleted","id":t["id"],"source":"runbook","target":t["target"],"retries":0})
    return {"tasks":updated,"collected":collected,"events":events,"parallel_elapsed":round(time.perf_counter()-started,3)}


@traceable(name="web_search_node")
async def web_search_node(state: AgentState, deps: SupervisorDeps) -> dict:
    if not state.get("optics_targets") or state.get("calculation_request") or not needs_web_search(state["query"]):
        return {}
    try:
        data = await deps.mcp.call_tool("search_optics_web", {"query": user_question(state["query"])})
    except Exception:
        data = {"status": "unavailable", "results": []}
    return {"collected":state.get("collected", [])+[{"source":"web_search", "data":data}],
            "events":state["events"]+[{"type":"WebSearchCompleted", "status":data["status"],
                "count":len(data.get("results", []))}]}


@traceable(name="calculation_node")
async def calculation_node(state: AgentState, deps: SupervisorDeps) -> dict:
    """계산 담당: 필요한 질문에서만 실제 MCP 수치 도구를 호출한다."""
    request = state.get("calculation_request")
    if not request:
        return {"calculation_result": None}
    data, retries = await with_retry(deps.mcp.call_tool, "calculate_optics",
                                    {"operation":request["operation"], "parameters":request["parameters"]})
    data["input_origins"] = request["origins"]
    tasks = [dict(t, status="done") if t.get("agent")=="calculation" else dict(t) for t in state["tasks"]]
    return {"tasks":tasks, "calculation_result":data,
            "retry_count":state.get("retry_count",0)+retries,
            "collected":state.get("collected",[])+[{"source":"calculation", "data":data}],
            "events":state["events"]+[{"type":"CalculationCompleted", "tool":"calculate_optics",
                "operation":request["operation"], "status":data["status"], "ok":data["ok"]}]}


@traceable(name="collect_node")
async def collect_node(state: AgentState, deps: SupervisorDeps) -> dict:
    """문서·검색·계산 담당을 필요한 경우에만 실행하고 독립 결과를 병합한다."""
    workers=[]
    if any(t["agent"]=="research" for t in state["tasks"]):workers.append(("documents",research_node))
    if not state.get("calculation_request") and needs_web_search(state["query"]):workers.append(("search",web_search_node))
    if state.get("calculation_request"):workers.append(("calculation",calculation_node))
    async def run(name,fn):
        start=time.perf_counter()
        result=await fn(state,deps)
        return name,result,round(time.perf_counter()-start,4)
    start=time.perf_counter()
    results=await asyncio.gather(*(run(name,fn) for name,fn in workers))
    collected=list(state.get("collected",[]));events=list(state["events"])
    tasks=[dict(t) for t in state["tasks"]];timings={};extra={}
    for name,result,elapsed in results:
        timings[name]=elapsed
        collected.extend(result.get("collected",[])[len(state.get("collected",[])):])
        events.extend(result.get("events",[])[len(state["events"]):])
        for task in result.get("tasks",[]):
            if task["status"]=="done":
                for t in tasks:
                    if t["id"]==task["id"]:t["status"]="done"
        for key in ["calculation_result","retry_count"]:
            if key in result:extra[key]=result[key]
    elapsed=round(time.perf_counter()-start,4)
    events.append({"type":"SourcesPrepared","seconds":elapsed,"workers":list(timings)})
    return {**extra,"collected":collected,"events":events,"tasks":tasks,"parallel_elapsed":elapsed,
            "timings":{**state.get("timings",{}),**timings}}


@traceable(name="write_node")
async def write_node(state: AgentState, deps: SupervisorDeps) -> dict:
    """수집 자료를 바탕으로 짧은 답변을 작성한다. 재작성 시도는 별도로 표시한다."""
    if state.get("calculation_result") is not None:
        draft = format_calculation(state["calculation_result"])
        return {"draft":draft, "last_prompt":None, "events":state["events"]+[
            {"type":"DraftWritten", "attempt":1, "length":len(draft), "mode":"verified_calculation"}]}
    attempt = state.get("validation_attempts", 0) + 1
    writer = get_stream_writer()
    collected = compact_sources(state["query"],list(state.get("collected", [])))
    if state.get("optics_targets"):
        collected.append({"source":"optics_mode","data":state["optics_mode"]})
    policy=answer_policy(state["query"])
    started=time.perf_counter();first_token=None;visible_chars=0
    def emit(piece):
        nonlocal first_token,visible_chars
        if first_token is None:first_token=time.perf_counter()-started
        # 상한을 넘는 장문은 표시하지 않고, 필요할 때 한 번만 재작성한다.
        remaining=policy["max_chars"]-visible_chars
        if remaining>0:
            visible=piece[:remaining];visible_chars+=len(visible)
            writer({"type":"AnswerToken","attempt":attempt,"delta":visible})
    draft, usage = await deps.quality_llm.write(
        (("## 이전 대화 (사용자 관찰)\n" + "\n".join(
            f"{m['role']}: {m['content']}" for m in state.get("history", [])[-6:] if m["role"] == "user")
            + "\n## 현재 질문\n" + state["query"])
         if state.get("optics_targets") and state.get("optics_mode")=="troubleshooting" else state["query"]),
        collected,
        attempt, state.get("validation_feedback"),
        on_token=emit)
    elapsed=round(time.perf_counter()-started,4)
    draft=normalize_answer(state["query"],draft)
    return {"draft": draft, "last_prompt": usage.get("prompt"),
            "generation_incomplete":usage.get("finish_reason")=="length",
            "timings":{**state.get("timings",{}),f"write_{attempt}":elapsed,"first_token":round(first_token,4) if first_token is not None else None},
            "cost_usd": _cost(state, usage),
            "events": state["events"] + [{"type": "DraftWritten", "attempt": attempt,
                                          "length": len(draft),"seconds":elapsed,"first_token_seconds":first_token}]}


@traceable(name="validate_node")
async def validate_node(state: AgentState, deps: SupervisorDeps) -> dict:
    """응답 형식을 검사한다. 내용의 사실성을 검증하는 기능은 아니다.

    모든 주제에 공통 출력 정책을 적용하고 최대 2회 재작성한다.
    답변 조각은 생성 중 중계하고 단순 서식은 로컬에서 정리한다.

    Args:
        state: draft, optics_mode, validation_attempts를 포함한 그래프 상태.
        deps: 노드 인터페이스를 통일하기 위한 의존성 묶음(여기서는 사용하지 않음).

    Returns:
        시도 횟수, 보완 요청, 형식 검사 이벤트를 담은 상태 갱신 사전.
    """
    if state.get("calculation_result") is not None:
        data = state["calculation_result"]
        expected = format_calculation(data)
        return {"draft":expected, "validation_attempts":state.get("validation_attempts",0)+1,
                "validation_feedback":None, "events":state["events"]+[
                    {"type":"CalculationValidated", "status":data["status"],
                     "checks":["explicit_units", "finite_values", "domain", "result_matches_tool"],
                     "ok":data["ok"]}]}
    draft = state["draft"]
    attempts = state.get("validation_attempts", 0) + 1
    issues=answer_violations(state["query"],draft)
    if state.get("generation_incomplete"):issues.append("토큰 한도 전에 완결된 짧은 답변으로 작성하세요.")
    ok=not issues
    verdict="합격" if ok else "불합격"
    if not ok and attempts>=2:
        # 검사를 통과하지 못한 장문을 그대로 합격 처리하지 않는다.
        excerpt=completed_answer_excerpt(state["query"],draft)
        draft=excerpt or "답변 생성이 중간에 끝났습니다. 잠시 후 다시 질문해 주세요."
        verdict="완결 문단 보존" if excerpt else "출력 검사 실패"
    feedback=" ".join(issues) if issues and attempts<2 else None
    event = {"type": "Validation", "attempt": attempts, "verdict": verdict}
    return {"draft": draft, "validation_attempts": attempts, "validation_feedback": feedback,
            "events": state["events"] + [event]}


@traceable(name="finalize_node")
async def finalize_node(state: AgentState, deps: SupervisorDeps) -> dict:
    """검증 루프를 마친 답변을 최종 응답으로 옮기고 완료 이벤트를 기록한다.

    Args:
        state: 현재 질문, 작업 목록, 수집 결과와 이벤트를 담은 그래프 상태.
        deps: LLM, MCP 클라이언트, 대화 저장소 등의 의존성 묶음.
    """
    return {"final": state["draft"],
            "events": state["events"] + [{"type": "Finalize", "pipeline": "optics"}]}


def _after_route(state: AgentState) -> str:
    """질문 분류에 따라 직접 대화 또는 조사 계획 노드로 이동한다.

    Args:
        state: 현재 질문, 작업 목록, 수집 결과와 이벤트를 담은 그래프 상태.

    Returns:
        다음 노드 이름(chat_answer 또는 plan).
    """
    return "chat_answer" if state["route"] == "chat" else "plan"


def _after_validate(state: AgentState) -> str:
    """형식 보완이 필요하면 재작성하고 아니면 답변을 확정한다.

    Args:
        state: 현재 질문, 작업 목록, 수집 결과와 이벤트를 담은 그래프 상태.

    Returns:
        다음 노드 이름(finalize 또는 write).
    """
    return "finalize" if state.get("validation_feedback") is None else "write"


def build_graph(deps: SupervisorDeps):
    """의존성을 각 노드에 주입하고 조건부 분기를 연결한 그래프를 컴파일한다.

    Args:
        deps: LLM, MCP 클라이언트, 대화 저장소 등의 의존성 묶음.

    Returns:
        ainvoke/astream으로 실행할 수 있는 컴파일된 그래프.
    """
    g = StateGraph(AgentState)
    node = lambda fn: partial(fn, deps=deps)
    g.add_node("route", node(route_node))
    g.add_node("chat_answer", node(chat_answer_node))
    g.add_node("plan", node(plan_node))
    g.add_node("collect", node(collect_node))
    g.add_node("write", node(write_node))
    g.add_node("validate", node(validate_node))
    g.add_node("finalize", node(finalize_node))

    g.set_entry_point("route")
    g.add_conditional_edges("route", _after_route,
                            {"chat_answer": "chat_answer", "plan": "plan"})
    g.add_edge("chat_answer", END)
    g.add_edge("plan", "collect")
    g.add_edge("collect", "write")
    g.add_edge("write", "validate")
    g.add_conditional_edges("validate", _after_validate,
                            {"finalize": "finalize", "write": "write"})
    g.add_edge("finalize", END)
    return g.compile()
