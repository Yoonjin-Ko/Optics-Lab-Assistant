import json
import unittest
from agent.optics_calculations import plan_calculation,calculate_optics,format_calculation

def query(a=20,dx=0,question='기존 유효 팔 길이 차이가 뭐냐',missing=False):
    practical={} if missing else {'armDifference':a}
    snapshot={'version':1,'kind':'michelson','values':{'displacement':dx},'practical':practical}
    return '[사용자 질문]\n'+question+'\n\n[현재 가상 실험]\n[실험 설정 스냅샷]\n'+json.dumps(snapshot,ensure_ascii=False)

def response(q):
    plan=plan_calculation(q)
    assert plan is not None
    return format_calculation(calculate_optics(plan['operation'],plan['parameters']))

class ParameterTests(unittest.TestCase):
    def test_definition_uses_own_current_value(self):
        text=response(query())
        self.assertIn('**20 µm**',text)
        self.assertIn('두 거울까지의 거리 차이 · 기준',response(query(question='초기 팔 길이 차이가 뭐야')))
        self.assertIn('왕복 광로차',text)
        self.assertIn('추가 거울 이동량 Δx와 다른 값',text)
        self.assertIn('**0 µm**',text)
        changed=response(query(37,1.5))
        self.assertIn('**37 µm**',changed)
        self.assertIn('**38.5 µm**',changed)
        self.assertIn('**3 µm**',changed)
    def test_missing_value_not_replaced_by_displacement(self):
        text=response(query(dx=2,missing=True))
        self.assertIn('숫자는 확인할 수 없습니다',text)
        self.assertNotIn('현재 전송된 설정은 **2',text)
    def test_motion_field_and_comparison(self):
        text=response(query(30,2,'거울 이동 Δx가 뭐야'))
        self.assertIn('**2 µm**',text);self.assertNotIn('현재 전송된 설정은 **30',text)
        text=response(query(30,2,'기준 유효 팔 길이 차이와 거울 이동 Δx의 의미를 설명해줘'))
        self.assertIn('**30 µm**',text);self.assertIn('**2 µm**',text)
    def test_two_arm_distances_and_round_trip_path(self):
        snapshot={'version':1,'kind':'michelson','values':{'displacement':1},'practical':{'arm1Distance':100,'arm2Distance':100.02}}
        q='[사용자 질문]\n두 거리 차이와 왕복 광로차가 얼마야?\n\n[현재 가상 실험]\n[실험 설정 스냅샷]\n'+json.dumps(snapshot,ensure_ascii=False)
        text=response(q)
        self.assertIn('**42 µm**',text)
        self.assertIn('**21 µm**',text)
        self.assertIn('**20 µm**',text)

    def test_adjustment_not_definition(self):
        plan=plan_calculation(query(question='기준 유효 팔 길이 차이를 어떻게 바꾸면 돼?'))
        self.assertTrue(plan is None or plan['operation']!='parameter_definition')
