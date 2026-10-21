"""v2 Supervisor — 실제 langgraph.StateGraph (Wave 4·5·6·7·8·10b·15 통합).

route → (chat 직행 | incident 파이프라인)
incident: plan(MCP Prompt 절차 반영) → gate(권위 게이트) → research(가드+병렬+재시도)
          → replan_check(부족 시 gap task 후 재조사) → analysis(needs_analysis=True일 때만
          실제 실행) → write → validate(반려 시 재작성) → finalize

모든 노드는 SupervisorDeps를 functools.partial로 주입받는 순수 함수다(Wave 13).
각 노드는 @traceable로 LangSmith에 계층 트리로 기록된다.
"""
import asyncio
import json
import time
from functools import partial
from pathlib import Path
from typing import Any, TypedDict

from langgraph.config import get_stream_writer
from langgraph.graph import END, StateGraph
from langsmith import traceable

from .optics_calculations import plan_calculation, format_calculation
from .deps import SupervisorDeps
from .retry import with_retry
from .optics import optical_targets, answer_mode, short_concept_card


def _load_known_systems() -> set[str]:
    """ollama_llm.py/openai_llm.py와 동일한 소스(data/monitoring.json)에서
    시스템 목록을 읽는다 — plan_node가 MCP Prompt에 넘길 system_name을
    쿼리에서 멤버십 매칭으로 뽑아낼 때 쓴다."""
    path = Path(__file__).resolve().parent.parent / "data" / "monitoring.json"
    try:
        return set(json.loads(path.read_text()).keys())
    except (OSError, json.JSONDecodeError):
        return {"auth-service", "web-01"}


KNOWN_SYSTEMS = _load_known_systems()


def _extract_system_name(query: str) -> str:
    """정규식 대신 실제 KNOWN_SYSTEMS 멤버십 매칭 — MCP Prompt(incident_analysis_
    prompt)의 system_name은 "시스템: X" 한 줄짜리 컨텍스트라 항상 정해진 이름
    중 하나로만 고정한다(여러 개 언급돼도 join하지 않음 — 실제 조사 대상 목록은
    이후 plan()의 tasks가 별도로 결정). 쿼리에서 가장 먼저 등장하는 시스템을
    고르고, 하나도 안 걸리면 가장 흔한 사례인 auth-service로 폴백."""
    matches = [(query.index(s), s) for s in KNOWN_SYSTEMS if s in query]
    return min(matches)[1] if matches else "auth-service"


class AgentState(TypedDict, total=False):
    query: str
    optics_targets: list[str]
    optics_mode: str
    calculation_request: dict | None
    calculation_result: dict | None
    thread_id: str
    history: list[dict]
    route: str
    needs_analysis: bool
    tasks: list[dict]
    gate_removed: int
    collected: list[dict]
    replan_rounds: int
    retry_count: int
    parallel_elapsed: float
    draft: str
    validation_attempts: int
    validation_feedback: str
    final: str
    last_prompt: str
    cost_usd: float
    events: list[dict]


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
    """Wave 5 — 모든 쿼리가 무거운 파이프라인을 탈 필요는 없다."""
    calculation = plan_calculation(state["query"])
    targets = [calculation["document"]] if calculation else optical_targets(state["query"], state.get("history", []))
    if targets:
        return {"route": "incident", "calculation_request": calculation, "optics_targets": targets, "optics_mode": answer_mode(state["query"]),
                "needs_analysis": False,
                "events": state.get("events", []) +
                    [{"type": "RouteDecided", "route": "incident"}]}
    result, usage = deps.fast_llm.route(state["query"])
    event = {"type": "RouteDecided", "route": result["route"]}
    return {"route": result["route"], "calculation_request": None, "needs_analysis": result["needs_analysis"],
            "cost_usd": _cost(state, usage),
            "events": state.get("events", []) + [event]}


@traceable(name="chat_answer_node")
async def chat_answer_node(state: AgentState, deps: SupervisorDeps) -> dict:
    """Wave 5 direct 경로 — 히스토리 기반 응답 (Wave 12 세션 증명 지점).

    토큰 단위 스트리밍 — get_stream_writer()는 /chat/stream처럼 custom 모드로 소비될
    때만 실제로 전송되고, /chat(ainvoke)처럼 스트리밍하지 않는 호출에서는 자동으로
    no-op이 된다."""
    writer = get_stream_writer()
    reply, usage = await deps.fast_llm.chat(
        state["query"], state.get("history", []),
        on_token=lambda piece: writer({"type": "AnswerToken", "delta": piece}))
    return {"final": reply, "last_prompt": usage.get("prompt"),
            "cost_usd": _cost(state, usage),
            "events": state["events"] + [{"type": "Finalize", "pipeline": "chat-direct"}]}


@traceable(name="plan_node")
async def plan_node(state: AgentState, deps: SupervisorDeps) -> dict:
    """Wave 4 — Plan/Task 분해. Wave 2의 MCP Prompt가 표준 절차를 깔아준다.

    resource와 마찬가지로 이름을 어느 서버가 들고 있는지 미리 가정하지 않고,
    find_prompt()로 연결된 서버들을 먼저 조회해 찾은 뒤에만 get_prompt를 보낸다."""
    if state.get("optics_targets"):
        tasks = [{"id": f"optics-{i}", "agent": "research", "kind": "runbook",
                  "target": target, "status": "pending"}
                 for i, target in enumerate(state["optics_targets"])]
        if state.get("calculation_request"):
            tasks.append({"id":"optics-calculation", "agent":"calculation", "kind":"calculation",
                          "target":state["calculation_request"]["operation"], "status":"pending"})
        return {"tasks": tasks, "needs_analysis": False,
                "events": state["events"] + [{"type": "PlanCreated",
                    "task_count": len(tasks), "targets": state["optics_targets"]}]}
    prompt_server = await deps.mcp.find_prompt("incident_analysis_prompt")
    procedure = await deps.mcp.get_prompt(
        "incident_analysis_prompt",
        {"system_name": _extract_system_name(state["query"]), "symptom": state["query"]},
        server=prompt_server,
    )
    result, usage = deps.fast_llm.plan(state["query"], procedure)
    targets = [t["target"] for t in result["tasks"]
               if t["agent"] == "research" and t.get("target")]
    event = {"type": "PlanCreated", "task_count": len(result["tasks"]),
             "targets": targets}
    return {"tasks": result["tasks"], "needs_analysis": result["needs_analysis"],
            "cost_usd": _cost(state, usage), "events": state["events"] + [event]}


@traceable(name="gate_node")
async def gate_node(state: AgentState, deps: SupervisorDeps) -> dict:
    """Wave 6 — 권위 게이트. needs_analysis=False인데 섞여 들어온 analysis task를
    프롬프트가 아니라 코드로 강제 제거한다."""
    tasks = state["tasks"]
    if not state.get("needs_analysis", False):
        kept = [t for t in tasks if t["agent"] != "analysis"]
        removed = len(tasks) - len(kept)
    else:
        kept, removed = tasks, 0
    event = {"type": "GateApplied", "removed_analysis_tasks": removed}
    return {"tasks": kept, "gate_removed": removed,
            "events": state["events"] + [event]}


@traceable(name="research_node")
async def research_node(state: AgentState, deps: SupervisorDeps) -> dict:
    """Wave 15 가드 + Wave 10b 병렬 + Wave 9 재시도 + Wave 2 Tool/Resource 실호출."""
    tasks = state["tasks"]
    research_indices = [i for i, t in enumerate(tasks)
                        if t["agent"] == "research" and t["status"] == "pending"]
    # Wave 15 — 객체가 아니라 '실행할 목록'을 검사한다 (not research_agent 버그의 수정판)
    if not research_indices:
        return {"events": state["events"] +
                [{"type": "ResearchSkipped", "reason": "pending research task 0개"}]}

    retry_total = state.get("retry_count", 0)

    # URI를 코드에 하드코딩하지 않는다. 여러 MCP 서버가 연결돼 있고 그중 어느 서버가
    # "get_incident_runbook" resource를 제공하는지 모른다고 가정하고, 먼저 연결된
    # 서버들을 조회(list)해 유효한 서버를 찾은 뒤에만 그 서버로 요청한다.
    needs_runbook = any(tasks[i]["kind"] != "monitoring" for i in research_indices)
    runbook_server = runbook_uri_template = None
    if needs_runbook:
        runbook_server, runbook_uri_template = await deps.mcp.find_resource_template(
            "get_incident_runbook")

    async def run_one(idx: int) -> dict:
        """조사 작업 하나를 실행해 결과·출처·재시도 횟수를 반환한다.

        Args:
            idx: 작업 목록에서 실행할 항목의 인덱스.
        """
        task = tasks[idx]
        await asyncio.sleep(0.35)   # 태스크당 고정 지연 — 병렬 효과를 실측하기 위함
        if task["kind"] == "monitoring":
            data, retries = await with_retry(
                deps.mcp.call_tool, "get_monitoring_status",
                {"system_name": task["target"]})
            return {"idx": idx, "source": "monitoring", "data": data, "retries": retries}
        uri = runbook_uri_template.format(incident_type=task["target"])
        data = await deps.mcp.read_resource(uri, server=runbook_server)
        return {"idx": idx, "source": "runbook", "data": data, "retries": 0}

    started = time.perf_counter()
    results = await asyncio.gather(*(run_one(i) for i in research_indices))
    elapsed = round(time.perf_counter() - started, 2)

    new_tasks = [dict(t) for t in tasks]
    collected = list(state.get("collected", []))
    events = list(state["events"])
    for r in results:
        new_tasks[r["idx"]]["status"] = "done"
        collected.append({"source": r["source"], "data": r["data"]})
        retry_total += r["retries"]
        events.append({"type": "TaskCompleted", "id": new_tasks[r["idx"]]["id"],
                       "source": r["source"], "target": new_tasks[r["idx"]]["target"],
                       "retries": r["retries"]})
    return {"tasks": new_tasks, "collected": collected, "retry_count": retry_total,
            "parallel_elapsed": elapsed, "events": events}


@traceable(name="replan_check_node")
async def replan_check_node(state: AgentState, deps: SupervisorDeps) -> dict:
    """문서 확보 상태를 기록한다. 삭제한 서버 장애 문서로 재조회하지 않는다."""
    has_runbook = any(c["source"] == "runbook" for c in state.get("collected", []))
    verdict = {"type": "ReplanCheck", "round": state.get("replan_rounds", 0),
               "is_sufficient": has_runbook}
    if not has_runbook:
        verdict["skip_research"] = True
        verdict["reason"] = "해당 요청에 연결된 학습 문서 없음. 서버 장애 런북 자동 조회는 제거됨."
    return {"events": state["events"] + [verdict]}


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


@traceable(name="analysis_node")
async def analysis_node(state: AgentState, deps: SupervisorDeps) -> dict:
    """Wave 6 보완 — needs_analysis=True가 정당한 경우(모델의 자기모순이 아니라
    실제로 패턴 비교가 필요하다고 판단한 경우)를 위한 실행 경로. gate가 살려둔
    agent=='analysis' task가 있을 때만 수집된 monitoring 결과들을 비교 분석한다."""
    tasks = state["tasks"]
    pending = [t for t in tasks if t["agent"] == "analysis" and t["status"] == "pending"]
    if not pending:
        return {"events": state["events"] +
                [{"type": "AnalysisSkipped", "reason": "analysis task 0개"}]}
    summary, usage = deps.fast_llm.analyze(state.get("collected", []))
    new_tasks = [dict(t) for t in tasks]
    for t in new_tasks:
        if t["agent"] == "analysis" and t["status"] == "pending":
            t["status"] = "done"
    collected = state.get("collected", []) + [{"source": "analysis", "data": summary}]
    event = {"type": "AnalysisCompleted", "length": len(summary)}
    return {"tasks": new_tasks, "collected": collected,
            "cost_usd": _cost(state, usage), "events": state["events"] + [event]}


@traceable(name="write_node")
async def write_node(state: AgentState, deps: SupervisorDeps) -> dict:
    """Wave 8/10a — 고품질 모델로 초안 작성 (1차는 의도적 저품질).

    토큰마다 attempt 번호를 같이 실어 보낸다 — validate가 반려해 재작성(attempt 증가)
    될 때 프론트가 새 말풍선으로 끊어서 보여줄 수 있게 하기 위함(Wave 8 재작성 루프를
    그대로 노출)."""
    if state.get("calculation_result") is not None:
        draft = format_calculation(state["calculation_result"])
        return {"draft":draft, "last_prompt":None, "events":state["events"]+[
            {"type":"DraftWritten", "attempt":1, "length":len(draft), "mode":"verified_calculation"}]}
    attempt = state.get("validation_attempts", 0) + 1
    writer = get_stream_writer()
    collected = list(state.get("collected", []))
    card = short_concept_card(state["query"]) if state.get("optics_targets") else None
    if card:
        # 정의 질문에는 큰 문서 전체와 과거 장문 답변을 다시 공급하지 않는다.
        collected = [{"source": "runbook", "data": "# 광학 실험 개념: " + card[0] + "\n" + card[1]}]
    if state.get("optics_targets"):
        collected.append({"source": "optics_mode", "data": state["optics_mode"]})
    draft, usage = await deps.quality_llm.write(
        (("## 이전 대화 (사용자 관찰)\n" + "\n".join(
            f"{m['role']}: {m['content']}" for m in state.get("history", [])[-10:])
            + "\n## 현재 질문\n" + state["query"])
         if state.get("optics_targets") and not card else state["query"] + ("\n[출력 제한] 질문한 개념만 2~3문장, 500자 이내. 표·수식·추가 질문·다른 개념 목록 금지." if card else "")),
        collected,
        attempt, state.get("validation_feedback"),
        on_token=None if card else lambda piece: writer(
            {"type": "AnswerToken", "attempt": attempt, "delta": piece}))
    return {"draft": draft, "last_prompt": usage.get("prompt"),
            "cost_usd": _cost(state, usage),
            "events": state["events"] + [{"type": "DraftWritten", "attempt": attempt,
                                          "length": len(draft)}]}


@traceable(name="validate_node")
async def validate_node(state: AgentState, deps: SupervisorDeps) -> dict:
    """응답 형식을 검사한다. 내용의 사실성을 검증하는 기능은 아니다.

    이론 모드는 15자 이상, 점검 모드는 30자 이상과 1) 표기를 확인한다.
    최대 3회 작성 후에는 루프를 종료하므로 통과가 과학적 정확성을 보증하지 않는다.

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
    theory = state.get("optics_mode") == "theory"
    ok = len(draft.strip()) >= 15 if theory else len(draft) >= 30 and "1)" in draft
    card = short_concept_card(state["query"]) if state.get("optics_targets") else None
    too_long = bool(card and (len(draft)>500 or len(draft.splitlines())>8))
    if too_long:
        ok=False
    if too_long and attempts>=3:
        # 무리한 문자열 절단 대신 검토한 짧은 정의로 대체한다.
        draft=card[1]
        ok=True
    verdict = "합격" if ok else "불합격"
    if not ok and attempts >= 3:   # 실모델 무한 재작성 방지 — 최대 3회 후 통과 처리
        ok, verdict = True, "합격(최대 시도 도달 — 통과 처리)"
    feedback = None if ok else ("질문에 대한 직접적인 답을 완전한 문장으로 설명하세요." if theory else (
        f"응답이 너무 짧습니다({len(draft)}자, 최소 30자). 절차를 1) 2) 3) 번호로 "
        f"구체적으로 설명하세요."))
    if too_long and not ok:
        feedback="답변이 질문 범위를 벗어납니다. 해당 개념 정의와 예시 하나만 2~3문장, 500자 이내로 쓰세요. 표·수식·다른 개념·추가 질문은 빼세요."
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
            "events": state["events"] + [{"type": "Finalize", "pipeline": "incident-v2"}]}


def _after_route(state: AgentState) -> str:
    """질문 분류에 따라 직접 대화 또는 조사 계획 노드로 이동한다.

    Args:
        state: 현재 질문, 작업 목록, 수집 결과와 이벤트를 담은 그래프 상태.

    Returns:
        다음 노드 이름(chat_answer 또는 plan).
    """
    return "chat_answer" if state["route"] == "chat" else "plan"


def _after_replan_check(state: AgentState) -> str:
    """추가 문서 조회 필요 여부에 따라 재조사 또는 분석 노드로 이동한다.

    Args:
        state: 현재 질문, 작업 목록, 수집 결과와 이벤트를 담은 그래프 상태.

    Returns:
        다음 노드 이름(analysis 또는 research).
    """
    last = state["events"][-1]
    return "analysis" if last.get("is_sufficient") or last.get("skip_research") else "research"


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
    node = lambda fn: partial(fn, deps=deps)   # Wave 13 — 명시적 의존성 주입
    g.add_node("route", node(route_node))
    g.add_node("chat_answer", node(chat_answer_node))
    g.add_node("plan", node(plan_node))
    g.add_node("gate", node(gate_node))
    g.add_node("research", node(research_node))
    g.add_node("replan_check", node(replan_check_node))
    g.add_node("calculation", node(calculation_node))
    g.add_node("analysis", node(analysis_node))
    g.add_node("write", node(write_node))
    g.add_node("validate", node(validate_node))
    g.add_node("finalize", node(finalize_node))

    g.set_entry_point("route")
    g.add_conditional_edges("route", _after_route,
                            {"chat_answer": "chat_answer", "plan": "plan"})
    g.add_edge("chat_answer", END)
    g.add_edge("plan", "gate")
    g.add_edge("gate", "research")
    g.add_edge("research", "replan_check")
    g.add_conditional_edges("replan_check", _after_replan_check,
                            {"analysis": "calculation", "research": "research"})
    g.add_edge("calculation", "analysis")
    g.add_edge("analysis", "write")
    g.add_edge("write", "validate")
    g.add_conditional_edges("validate", _after_validate,
                            {"finalize": "finalize", "write": "write"})
    g.add_edge("finalize", END)
    return g.compile()
