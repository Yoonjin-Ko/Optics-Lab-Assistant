"""같은 질의 집합으로 실제 MCP 계산과 그래프 연결을 평가한다. LLM 성능 평가는 아니다."""
import asyncio
import json
import math
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from agent.deps import SupervisorDeps
from agent.fake_llm import FastLLM, QualityLLM
from agent.graph import build_graph
from agent.mcp_client import MCPClient

CASES=[
 ('532 nm 광자 에너지 계산','calculated','광자 에너지',2.3305300457368467),
 ('5320 Å 광자 에너지 계산','calculated','광자 에너지',2.3305300457368467),
 ('XRD 파장 0.15406 nm 면간격 0.3 nm 각도 계산','calculated','2θ',29.75658740683661),
 ('마이켈슨 거울을 0.1582 mm 이동 무늬 500개 파장 계산','calculated','파장',632.8),
 ('마이켈슨 변위 1 µm 파장 500 nm 무늬 계산','calculated','무늬 주기 수',4),
 ('편광판 45도 투과율 계산','calculated','투과율',50),
 ('렌즈 초점거리 10 cm 물체거리 30 cm 상 거리 계산','calculated','상 거리',15),
 ('광자 에너지 계산해줘','missing_input',None,None),
 ('파장 -532 nm 광자 에너지 계산','invalid_input',None,None),
 ('XRD 파장 2 nm 면간격 0.3 nm 각도 계산','impossible',None,None),
 ('렌즈 초점거리 10 cm 물체거리 10 cm 상 거리 계산','singular',None,None),
]
async def main():
    mcp=MCPClient(flaky_first_tool_call=False)
    await mcp.start()
    try:
        graph=build_graph(SupervisorDeps(FastLLM('fake',0),QualityLLM('fake',0),mcp,None,'v2'))
        rows=[]
        for query,status,name,expected in CASES:
            start=time.perf_counter()
            state=await graph.ainvoke({'query':query,'events':[],'history':[],'cost_usd':0})
            elapsed=time.perf_counter()-start
            data=state.get('calculation_result',{})
            actual=next((r['value'] for r in data.get('results',[]) if r['name']==name),None)
            called=sum(e['type']=='CalculationCompleted' for e in state['events'])
            passed=data.get('status')==status and called==1 and (name is None or actual is not None and math.isclose(actual,expected,rel_tol=1e-9,abs_tol=1e-9))
            rows.append({'query':query,'expected_status':status,'actual_status':data.get('status'),'expected_value':expected,'actual_value':actual,'mcp_calculation_calls':called,'latency_seconds':round(elapsed,4),'passed':passed})
        report={'backend':'fake (수치 도구와 MCP는 실제 실행)','case_count':len(rows),'passed':sum(r['passed'] for r in rows),'notes':['LLM 답변 품질·Ollama/OpenAI 지연의 평가가 아니다.','기존 research 노드의 작업당 인위적 0.35초 지연이 포함된다.','변경 전 실행 결과를 저장하지 않아 Before/After 성능 향상은 주장하지 않는다.'],'cases':rows}
        out=Path(__file__).with_name('optics_calculation_results.json')
        out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print(f"{report['passed']}/{len(rows)} 통과 · {out}")
        if not all(r['passed'] for r in rows):raise SystemExit(1)
    finally:
        await mcp.stop()
if __name__=='__main__':asyncio.run(main())
