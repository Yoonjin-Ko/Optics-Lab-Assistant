"""탐구 질문 전체 연결·핵심 오답·설정 변경·정의역과 실제 MCP 경로 검증."""
import json
import re
import unittest
from pathlib import Path
from agent.inquiry_calculations import CATALOG, calculate_inquiry, plan_inquiry
from agent.optics_calculations import format_calculation
from agent.graph import build_graph
from agent.deps import SupervisorDeps
from agent.mcp_client import MCPClient

SETTINGS=dict(focal=10,object=30,angle=45,wavelength=532,slit=.1,distance=1,displacement=1,mirrorTiltX=.1,mirrorTiltY=0,n1=1,n2=1.5,incidence=45,absorptionType='semiconductor',threshold=1.12,absorptionWave=532,f=50,u=1000,fNumber=4,wave=550,objective=500,eyepiece=25,diameter=80,telescopeModel='kepler',microF=4,tube=200,microNA=.65,medium=1,microscopeModel='infinity',xray=.15406,spacing=.3,order=1,scanTwoTheta=30,material='custom',plane='111',apex=60,prismRotation=0)
def request(k,i,**changes):return dict(version=1,kind=k,index=i,settings={**SETTINGS,**changes})
def message(r):return '[사용자 질문]\n'+CATALOG[r['kind']][r['index']]+'\n\n[현재 가상 실험]\n[탐구 계산 계약]\n'+json.dumps(r,ensure_ascii=False)
def answer(k,i,**changes):
    r=calculate_inquiry(request(k,i,**changes));assert r['ok'],r
    return r['answer']

class InquiryTests(unittest.TestCase):
    def test_every_ui_question_has_contract_and_finite_result(self):
        html=(Path(__file__).resolve().parents[1]/'web_chat.html').read_text()
        chunk=html.split('const inquiryGuides={',1)[1].split('\n    };',1)[0]
        catalog={}
        for line in chunk.splitlines():
            m=re.search(r"^\s*('?[-a-z]+'?):.*questions:\[(.*?)\]",line)
            if m:catalog[m[1].strip("'")]=re.findall(r"'([^']*)'",m[2])
        self.assertEqual(catalog,CATALOG)
        for k,qs in CATALOG.items():
            for i,_ in enumerate(qs):
                with self.subTest(kind=k,index=i):
                    r=request(k,i);plan=plan_inquiry(message(r));self.assertIsNotNone(plan)
                    data=calculate_inquiry(plan['parameters']);self.assertTrue(data['ok'],data)
                    self.assertTrue(data['formula']);self.assertNotRegex(format_calculation(data),r'NaN|Infinity')
    def test_numeric_goals_change_with_settings(self):
        self.assertIn('f=15 cm',answer('lens',1))
        self.assertIn('f=20 cm',answer('lens',1,object=40))
        self.assertIn('물체 쪽 7.5 cm',answer('concave-lens',0))
        self.assertIn('회절 무늬는 커집니다',answer('camera',2))
        self.assertIn('2.66 µm',answer('michelson',0))
        self.assertIn('3.165 µm',answer('michelson',0,wavelength=633))
        self.assertIn('12.5 mm',answer('telescope',0))
        self.assertIn('2 mm',answer('microscope',1))
        self.assertIn('2.0202 mm',answer('microscope',1,microscopeModel='finite'))
        self.assertIn('튜브렌즈 뒤 초점거리 200 mm',answer('microscope',0))
        self.assertIn('전반사가 불가능',answer('fresnel',2))
        self.assertIn('41.8103',answer('fresnel',2,n1=1.5,n2=1))
        self.assertIn('1107',answer('absorption',1))
        self.assertIn('1.77333 mm',answer('diffraction',0,slitMode='double',slitSeparation=.3))
        self.assertIn('0.886667 mm',answer('diffraction',0,slitMode='double',slitSeparation=.6))
        self.assertNotEqual(answer('prism',0),answer('prism',0,prismRotation=2))
        self.assertNotEqual(answer('xrd',0),answer('xrd',0,material='Si'))
    def test_contract_cannot_replace_edited_question(self):
        q=message(request('lens',1));self.assertIsNone(plan_inquiry(q.replace(CATALOG['lens'][1],'초점거리가 뭐야?')))
        self.assertIsNone(plan_inquiry(q.replace('"version": 1','"version": 2')))
    def test_domain_boundaries(self):
        for k,i,changes in [('microscope',0,{'microNA':1.5}),('camera',0,{'u':50}),('xrd',0,{'xray':2}),('xrd',0,{'material':'Si','plane':'200'}),('diffraction',0,{'slit':0}),('absorption',0,{'threshold':float('nan')}),('lens',0,{'object':True})]:
            self.assertFalse(calculate_inquiry(request(k,i,**changes))['ok'])
        self.assertIn('유한한 상',answer('lens',0,object=10))
        self.assertIn('역산할 수 없습니다',answer('michelson',2,displacement=0))
        self.assertIn('결정할 수 없습니다',answer('xrd',2))

class InquiryMCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_all_contracts_through_real_mcp_without_llm(self):
        class NoLLM:
            async def write(self,*a,**kw):raise AssertionError('계산 경로에서 LLM 호출')
        mcp=MCPClient();await mcp.start()
        try:
            graph=build_graph(SupervisorDeps(NoLLM(),NoLLM(),mcp,None,'v2'))
            for k,qs in CATALOG.items():
                for i,_ in enumerate(qs):
                    with self.subTest(kind=k,index=i):
                        result=await graph.ainvoke({'query':message(request(k,i)),'history':[],'events':[],'cost_usd':0})
                        self.assertIn('공식:',result['final'])
                        self.assertTrue(result['calculation_result']['ok'])
        finally:await mcp.stop()
