"""현재 UI에서 캡처한 탐구 계약 53건의 실제 MCP 경로·시간을 재현한다.
성공 상태는 도구 실행 성공이며 자연어 질문 전반의 정확도 점수가 아니다.
"""
import asyncio
import json
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from agent.graph import build_graph
from agent.deps import SupervisorDeps
from agent.mcp_client import MCPClient

class NoLLM:
    async def write(self,*args,**kwargs):raise AssertionError('탐구 계산 중 LLM 호출')
    async def chat(self,*args,**kwargs):raise AssertionError('탐구 계산 중 LLM 호출')

async def main():
    root=Path(__file__).parent
    cases=json.loads((root/'fixtures/inquiry_contract_cases.json').read_text())
    mcp=MCPClient();await mcp.start();records=[]
    try:
        graph=build_graph(SupervisorDeps(NoLLM(),NoLLM(),mcp,None,'v2'))
        for case in cases:
            started=time.perf_counter()
            state=await graph.ainvoke({'query':case['message'],'history':[],'events':[],'cost_usd':0})
            records.append({'id':case['id'],'question':case['question'],'seconds':round(time.perf_counter()-started,4),'ok':state.get('calculation_result',{}).get('ok'),'result':state.get('calculation_result'),'answer':state['final']})
    finally:await mcp.stop()
    (root/'inquiry_contract_results.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
    passed=sum(r['ok'] is True for r in records)
    print(f'MCP 탐구 계약 실행: {passed}/{len(records)} 성공 (LLM 호출 없음)')
    if passed!=len(records):raise SystemExit(1)

if __name__=='__main__':asyncio.run(main())
