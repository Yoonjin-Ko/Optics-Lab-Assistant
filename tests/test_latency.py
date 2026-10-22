"""시간 수치보다 호출 수·동시 실행·중간 전달을 검증한다. 외부 API는 호출하지 않는다."""
import asyncio
import json
import unittest
from unittest.mock import patch
import httpx
from agent.graph import build_graph
from agent.deps import SupervisorDeps
from agent.fake_llm import FastLLM,QualityLLM
from agent.answer_context import normalize_answer,compact_sources
from agent.optics_calculations import calculate_optics


class LatencyTests(unittest.IsolatedAsyncioTestCase):
    async def test_document_search_overlap(self):
        document_started=asyncio.Event();search_started=asyncio.Event()
        class MCP:
            async def find_resource_template(self,name):return 'optics','optics://documents/{topic}'
            async def read_resource(self,uri,server):
                document_started.set()
                await asyncio.wait_for(search_started.wait(),1)
                return '# 광학 실험\n\n파장은 파동이 반복되는 공간 주기입니다.'
            async def call_tool(self,name,arguments):
                self_name=name
                assert self_name=='search_optics_web'
                search_started.set()
                await asyncio.wait_for(document_started.wait(),1)
                return {'status':'ok','results':[]}
        graph=build_graph(SupervisorDeps(FastLLM('fake',0),QualityLLM('fake',0),MCP(),None,'v2'))
        state=await graph.ainvoke({'query':'빛의 파장 문헌 찾아줘','events':[],'history':[]})
        self.assertEqual(set(state['timings']) & {'documents','search'},{'documents','search'})
        self.assertEqual(len(state['collected']),2)

    async def test_calculation_skips_document_search_and_llm(self):
        calls=[]
        class MCP:
            async def call_tool(self,name,args):
                calls.append(name)
                return calculate_optics(**args)
        class NoLLM:
            async def write(self,*args,**kwargs):raise AssertionError('unnecessary LLM')
        graph=build_graph(SupervisorDeps(None,NoLLM(),MCP(),None,'v2'))
        state=await graph.ainvoke({'query':'532 nm 광자 에너지 계산','events':[],'history':[]})
        self.assertEqual(calls,['calculate_optics'])
        self.assertIn('2.33',state['final'])

    async def test_cosmetic_formatting_does_not_regenerate(self):
        class MCP:
            async def find_resource_template(self,name):return 'optics','optics://documents/{topic}'
            async def read_resource(self,*args,**kwargs):return '# 광학 실험\n\n원리 참고 자료'
        class Writer:
            calls=0
            async def write(self,*args,**kwargs):
                self.calls+=1
                kwargs['on_token']('### 결론\n  - 필요한 설명을 먼저 짧게 제시합니다.')
                return '### 결론\n  - 필요한 설명을 먼저 짧게 제시합니다.',{'usd':0}
        writer=Writer();graph=build_graph(SupervisorDeps(None,writer,MCP(),None,'v2'))
        state=await graph.ainvoke({'query':'편광이 뭐야?','events':[],'history':[]})
        self.assertEqual(writer.calls,1)
        self.assertNotIn('###',state['final'])

    async def test_openai_stream_chunks_and_usage(self):
        from agent.openai_llm import OpenAILLM
        completed=False;pieces=[]
        class Body(httpx.AsyncByteStream):
            async def __aiter__(self):
                nonlocal completed
                yield b'data: '+json.dumps({'choices':[{'delta':{'content':'first'},'finish_reason':None}]}).encode()+b'\n\n'
                await asyncio.sleep(0)
                assert pieces==['first']
                yield b'data: '+json.dumps({'choices':[{'delta':{'content':' second'},'finish_reason':'stop'}]}).encode()+b'\n\n'
                yield b'data: {"choices":[],"usage":{"total_tokens":12}}\n\n'
                completed=True
                yield b'data: [DONE]\n\n'
        def handler(request):
            payload=json.loads(request.content)
            self.assertTrue(payload['stream'])
            self.assertTrue(payload['stream_options']['include_usage'])
            return httpx.Response(200,stream=Body())
        real_client=httpx.AsyncClient
        with patch.dict('os.environ',{'OPENAI_API_KEY':'test-only'}),patch('agent.openai_llm.httpx.AsyncClient',side_effect=lambda **kw:real_client(transport=httpx.MockTransport(handler),**kw)):
            model=OpenAILLM('gpt-4o',0)
            text,usage=await model._chat_stream('system','user',on_token=pieces.append)
        self.assertTrue(completed)
        self.assertEqual(text,'first second')
        self.assertEqual(usage['tokens'],12)
