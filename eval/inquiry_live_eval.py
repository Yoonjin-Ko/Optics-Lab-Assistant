"""UI에서 내보낸 실제 탐구 질문을 실모델+MCP로 순차 실행하고 원답·시간을 기록한다.
사용: LANGSMITH_TRACING=false LANGCHAIN_TRACING_V2=false .venv/bin/python eval/inquiry_live_eval.py --cases /tmp/optics-inquiry-cases.json --output /tmp/inquiry-results.json
외부 유료 API 대신 로컬 Ollama를 사용한다. 합격 여부는 내용 검토 후 별도 기록한다.
"""
import argparse,asyncio,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from agent.graph import build_graph
from agent.deps import SupervisorDeps
from agent.ollama_llm import OllamaFastLLM,OllamaQualityLLM
from agent.mcp_client import MCPClient

async def main(args):
    cases=json.loads(Path(args.cases).read_text())
    if args.ids:cases=[c for c in cases if c['id'] in args.ids.split(',')]
    output=Path(args.output);records=[]
    mcp=MCPClient();await mcp.start()
    try:
        graph=build_graph(SupervisorDeps(OllamaFastLLM('qwen3:0.6b',0),OllamaQualityLLM(args.quality_model,0),mcp,None,'v2'))
        for case in cases:
            record={**case,'configured_quality_model':args.quality_model,'first_token_seconds':None,'events':[],'drafts':[],'input_chars':len(case['message'])}
            started=time.perf_counter()
            try:
                async with asyncio.timeout(180):
                    async for mode,payload in graph.astream({'query':case['message'],'history':[],'events':[],'cost_usd':0},stream_mode=['custom','updates']):
                        if mode=='custom':
                            if payload.get('type')=='AnswerToken' and record['first_token_seconds'] is None:record['first_token_seconds']=round(time.perf_counter()-started,3)
                        else:
                            for node,delta in payload.items():
                                if not delta:continue
                                if 'draft' in delta and node=='write':record['drafts'].append(delta['draft'])
                                if 'final' in delta:record['answer']=delta['final']
                                if 'events' in delta:record['events']=delta['events']
                                if 'timings' in delta:record['timings']=delta['timings']
            except Exception as exc:record['error']=type(exc).__name__
            record['total_seconds']=round(time.perf_counter()-started,3)
            records.append(record);output.write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
            print(case['id'],record['total_seconds'],record.get('answer',record.get('error','NO_ANSWER')).replace('\n',' ')[:110],flush=True)
    finally:await mcp.stop()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cases',default=str(Path(__file__).parent/'fixtures/inquiry_cases.json'));p.add_argument('--output',required=True);p.add_argument('--ids');p.add_argument('--quality-model',default='qwen3:8b');asyncio.run(main(p.parse_args()))
