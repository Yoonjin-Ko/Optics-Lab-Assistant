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

    def test_latest_snapshot_overrides_descriptive_numbers(self):
        query='[사용자 질문]\n렌즈 상 거리 계산해줘\n\n[현재 가상 실험]\n초점거리 10 cm, 물체 거리 30 cm\n[광학 계산 입력]\n{"default_operation":"thin_lens","parameters":{"focal":{"value":20,"unit":"cm"},"object_distance":{"value":30,"unit":"cm"}}}'
        plan=plan_calculation(query)
        self.assertEqual(plan['parameters']['focal']['value'],20)
        result=calculate_optics(plan['operation'],plan['parameters'])
        old_plan=plan_calculation(query.replace('"value":20','"value":10'))
        old_result=calculate_optics(old_plan['operation'],old_plan['parameters'])
        self.assertNotEqual(result['results'],old_result['results'])

    def test_inquiry_targets_are_not_replaced_by_current_forward_result(self):
        context='\n\n[현재 가상 실험]\n[광학 계산 입력]\n{"default_operation":"michelson_fringes","parameters":{"displacement":{"value":1,"unit":"µm"},"wavelength":{"value":532,"unit":"nm"},"fringes":{"value":3.759,"unit":"count"}}}'
        for question in ['현재 최대 투과 세기의 절반을 얻으려면 편광판을 몇 도로 맞출까?', '같은 크기의 실상을 만들려면 초점거리를 어떻게 정할까?']:
            self.assertIsNone(plan_calculation('[사용자 질문]\n'+question+context))

    def test_diffraction_fringe_is_not_michelson(self):
        query='[사용자 질문]\n현재 중앙 밝은 무늬의 폭을 계산하려면 어떤 값이 필요할까?\n\n[현재 가상 실험]\n[현재 실험 문서] shadow-and-diffraction\n파장 532 nm, 슬릿 폭 0.1 mm, 거리 1 m'
        self.assertIsNone(plan_calculation(query))

    def test_mirror_goal_uses_requested_count_and_current_wavelength(self):
        query='[사용자 질문]\n지금 파장에서 무늬 10개가 지나가려면 거울을 얼마나 옮겨야 할까?\n\n[현재 가상 실험]\n[현재 실험 문서] michelson-interferometer\n[광학 계산 입력]\n{"parameters":{"wavelength":{"value":532,"unit":"nm"},"fringes":{"value":0,"unit":"count"}}}'
        plan=plan_calculation(query)
        self.assertEqual(plan['operation'],'michelson_displacement')
        self.assertEqual(plan['parameters']['fringes']['value'],10)
        result=calculate_optics(plan['operation'],plan['parameters'])
        self.assertAlmostEqual(result['results'][0]['value'],2.66)


class MCPGraphCalculationTests(unittest.IsolatedAsyncioTestCase):
    async def test_actual_mcp_tool_and_graph(self):
        mcp=MCPClient()
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
