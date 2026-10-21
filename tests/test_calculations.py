"""수치·단위·거부 조건과 실제 MCP/그래프 연결. 외부 LLM 비용은 발생하지 않는다."""
import math
import json
import unittest
from agent.optics_calculations import calculate_optics, plan_calculation, format_calculation
from agent.deps import SupervisorDeps
from agent.fake_llm import FastLLM, QualityLLM
from agent.graph import build_graph
from agent.mcp_client import MCPClient


def run(query):
    plan=plan_calculation(query)
    return calculate_optics(plan['operation'],plan['parameters'])


class CalculationTests(unittest.TestCase):
    def test_units_and_formulae(self):
        for text in ['532 nm','0.532 µm','5320 Å','5.32e-7 m']:
            self.assertAlmostEqual(run(text+' 광자 에너지 계산')['results'][0]['value'],2.3305300457,places=8)
        self.assertAlmostEqual(run('XRD 파장 1.5406 Å 면간격 0.3 nm 1차 각도 계산')['results'][1]['value'],29.7565874068,places=8)
        self.assertAlmostEqual(run('마이켈슨 거울을 0.1582 mm 이동 무늬 500개 파장 계산')['results'][0]['value'],632.8)
        self.assertEqual(run('편광판 90도 투과율 계산')['results'][0]['value'],0)
        self.assertAlmostEqual(run('볼록렌즈 초점거리 10 cm 물체거리 30 cm 상 거리 계산')['results'][0]['value'],15)
        self.assertLess(run('오목렌즈 초점거리 10 cm 물체거리 30 cm 상 거리 계산')['results'][0]['value'],0)
        self.assertEqual(run('마이켈슨 변위 0 µm 파장 532 nm 무늬 계산')['results'][0]['value'],0)

    def test_refuses_missing_invalid_and_impossible(self):
        self.assertEqual(run('광자 에너지 계산해줘')['status'],'missing_input')
        self.assertEqual(run('XRD 파장 2 nm 면간격 0.3 nm 각도 계산')['status'],'impossible')
        self.assertEqual(run('렌즈 초점거리 10 cm 물체거리 10 cm 상 거리 계산')['status'],'singular')
        self.assertEqual(run('파장 -532 nm 광자 에너지 계산')['status'],'invalid_input')
        for value in [math.nan,math.inf,True,'532']:
            result=calculate_optics('photon_energy',{'wavelength':{'value':value,'unit':'nm'}})
            self.assertFalse(result['ok'])
            json.dumps(result,allow_nan=False)
        self.assertFalse(calculate_optics('photon_energy',{'wavelength':{'value':532,'unit':'kg'}})['ok'])
        self.assertIn('필요',format_calculation(run('광자 에너지 계산해줘')))
        self.assertEqual(run('파장 532 nm 650 nm 광자 에너지 계산')['status'],'missing_input')
        self.assertIsNone(plan_calculation('산란이 뭐야?'))
        self.assertIsNone(plan_calculation('망원경 목표 각배율 40배 접안렌즈 초점거리는?'))

    def test_snapshot_and_question_priority(self):
        query='[사용자 질문]\n편광판 현재 조건으로 계산해줘\n\n[현재 가상 실험]\n[광학 계산 입력]\n{"default_operation":"malus","parameters":{"angle":{"value":45,"unit":"deg"}}}'
        plan=plan_calculation(query);self.assertEqual(plan['parameters']['angle']['value'],45)
        self.assertEqual(plan['origins']['angle'],'experiment_snapshot')
        plan=plan_calculation(query.replace('편광판 현재 조건으로 계산해줘','편광판 90도 투과율 계산'))
        self.assertEqual(plan['parameters']['angle']['value'],90)
        self.assertEqual(plan['origins']['angle'],'question')


class MCPGraphCalculationTests(unittest.IsolatedAsyncioTestCase):
    async def test_actual_mcp_tool_and_graph(self):
        mcp=MCPClient(flaky_first_tool_call=False)
        await mcp.start()
        try:
            graph=build_graph(SupervisorDeps(FastLLM('fake',0),QualityLLM('fake',0),mcp,None,'v2'))
            for query in ['532 nm 광자 에너지 계산','XRD 파장 0.15406 nm 면간격 0.3 nm 각도 계산',
                          '마이켈슨 거울을 0.1582 mm 이동 무늬 500개 파장 계산','편광판 45도 투과율 계산',
                          '렌즈 초점거리 10 cm 물체거리 30 cm 상 거리 계산','광자 에너지 계산해줘',
                          'XRD 파장 2 nm 면간격 0.3 nm 각도 계산']:
                state=await graph.ainvoke({'query':query,'history':[],'events':[],'cost_usd':0})
                self.assertTrue(any(c['source']=='calculation' for c in state['collected']))
                self.assertTrue(any(e['type']=='CalculationCompleted' for e in state['events']))
                self.assertTrue(any(e['type']=='CalculationValidated' for e in state['events']))
                self.assertEqual(state['final'],format_calculation(state['calculation_result']))
                self.assertNotIn('CPU',state['final'])
                self.assertEqual(state['validation_attempts'],1)
            plain=await graph.ainvoke({'query':'산란이 뭐야?','history':[],'events':[],'cost_usd':0})
            self.assertFalse(any(c['source']=='calculation' for c in plain['collected']))
        finally:
            await mcp.stop()
