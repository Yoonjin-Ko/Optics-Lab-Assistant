"""광학 질문→실제 MCP 문서→그래프 응답 연결 검증. 외부 LLM 호출 없음."""
import unittest

from agent.deps import SupervisorDeps
from agent.fake_llm import FastLLM, QualityLLM
from agent.graph import build_graph
from agent.mcp_client import MCPClient
from agent.optics import optical_targets, answer_mode, THEORY_WRITER


class OpticsIntegration(unittest.IsolatedAsyncioTestCase):
    async def test_documents_followup_and_legacy(self):
        """외부 LLM 호출 없이 해당 경로의 연결·경계 조건을 검증한다.
        """
        mcp = MCPClient(flaky_first_tool_call=False)
        await mcp.start()
        try:
            graph = build_graph(SupervisorDeps(FastLLM('fake', 0), QualityLLM('fake', 0),
                                              mcp, None, 'v2'))
            cases = [
                ('분광기에서 스펙트럼 선이 겹쳐요', 'grating-prism-spectrometer'),
                ('그림자와 회절 실험에서 무늬가 안 보여요', 'shadow-and-diffraction'),
                ('Michelson 간섭계가 흔들려요', 'michelson-interferometer'),
                ('렌즈 상이 흐릿해요', 'lenses-and-optical-instruments'),
                ('편광판을 돌려도 밝기가 같아요', 'polarization-and-reflection'),
                ('빛의 속도 측정값이 달라요', 'speed-of-light'),
                ('광학 실험이 이상해요', 'experiment-intake'),
            ]
            for query, target in cases:
                with self.subTest(query=query):
                    result = await graph.ainvoke(dict(query=query, history=[], events=[], cost_usd=0))
                    self.assertIn(target, result['optics_targets'])
                    self.assertTrue(all(c['source'] == 'runbook' for c in result['collected']))
                    self.assertTrue(result['final'].strip())
                    self.assertTrue(any('광학 실험' in c['data'] for c in result['collected']))
                    self.assertNotIn('CPU', result['final'])
            # 실제 문제가 된 짧은 정의 질문은 문서 전체 요약으로 번지지 않아야 한다.
            self.assertEqual(optical_targets('산란이 뭐야?'), ['scattering-and-sky'])
            class VerboseQuality:
                async def write(self, query, collected, attempt, feedback, on_token=None):
                    self_inputs = [c['data'] for c in collected if c['source']=='runbook']
                    assert len(''.join(self_inputs)) < 500
                    assert on_token is None  # 긴 초안을 사용자에게 먼저 노출하지 않는다.
                    return '파장과 에너지와 모든 광학 개념 설명입니다.' * 100, {'usd':0}
            verbose_graph = build_graph(SupervisorDeps(FastLLM('fake',0), VerboseQuality(),mcp,None,'v2'))
            short = await verbose_graph.ainvoke(dict(query='산란이 뭐야?',history=[],events=[],cost_usd=0))
            self.assertLessEqual(len(short['final']),500)
            self.assertIn('진행 방향',short['final'])
            self.assertNotIn('파장과 에너지와 모든',short['final'])
            self.assertEqual(short['validation_attempts'],3)
            history = [{'role': 'user', 'content': 'Michelson 간섭계 무늬가 안 보여요'}]
            result = await graph.ainvoke(dict(query='빛은 보이는데 무늬만 없어요',
                                              history=history, events=[], cost_usd=0))
            self.assertEqual(result['optics_targets'], ['michelson-interferometer'])
            self.assertEqual(optical_targets('안녕하세요', history), [])
            self.assertEqual(optical_targets('UIR 업무를 설명해줘'), [])
            self.assertEqual(optical_targets('ASML 핵심 가치는?'), [])
            self.assertEqual(optical_targets('면접에서 경험 설명하는 방법'), [])
            sky_history = [{'role':'user','content':'하늘은 왜 파랄까?'}]
            euv_query = 'EUV로 회로를 그렸는데 좀 두껍게 그려졌어요 이거 왜이런가요'
            self.assertEqual(optical_targets(euv_query, sky_history), ['lithography-cd'])
            self.assertEqual(answer_mode(euv_query), 'troubleshooting')
            self.assertEqual(optical_targets('양자 터널링은 왜 생겨?', sky_history), [])
            euv = await graph.ainvoke(dict(query=euv_query, history=sky_history, events=[], cost_usd=0))
            self.assertEqual(euv['optics_targets'], ['lithography-cd'])
            self.assertTrue(all('하늘의 색' not in c['data'] for c in euv['collected']))

            for query, prior in [
                ('Michelson 간섭계 이론 알려줘', []),
                ('실험 이론 알려줘', []),
                ('빛의 종류는?', []),
                ('532 nm 광자 에너지는?', []),
                ('빛의 특성 알려줘', []),
                ('파장이 짧으면 에너지가 커?', history),
                ('그럼 원리도 설명해줘', history),
            ]:
                theory = await graph.ainvoke(dict(query=query, history=prior, events=[], cost_usd=0))
                self.assertEqual(theory['optics_mode'], 'theory')
                if query=='532 nm 광자 에너지는?':
                    self.assertIn('2.33053 eV', theory['final'])
                    self.assertTrue(theory['calculation_result']['ok'])
                else:
                    self.assertIn('실험 원리', theory['final'])
                self.assertNotIn('먼저 문서의 확인 질문에 답해', theory['final'])
                self.assertNotIn('CPU', theory['final'])
            for query in ['빛의 속도는?', '렌즈란?', '편광이 뭐야?', '회절격자란?']:
                self.assertEqual(answer_mode(query), 'theory')
            self.assertEqual(answer_mode('빛의 속도 측정값이 이상해요'), 'troubleshooting')
            attached = '[사용자 질문]\n무늬가 안 보여요\n\n[현재 가상 실험]\nMichelson 간섭계: 원리를 설명해줘.'
            self.assertEqual(answer_mode(attached), 'troubleshooting')
            self.assertIn('michelson-interferometer', optical_targets(attached))
            speed = await graph.ainvoke(dict(query='빛의 속도는?', history=[], events=[], cost_usd=0))
            self.assertEqual(speed['optics_mode'], 'theory')
            self.assertIn('299792458', speed['final'])
            self.assertNotIn('먼저 물어볼 질문', speed['final'])
            self.assertEqual(speed['validation_attempts'], 1)
            self.assertIn('1~3문장', THEORY_WRITER)
            self.assertEqual(result['optics_mode'], 'troubleshooting')
            self.assertEqual(optical_targets('빛의 종류는?', history), ['light-fundamentals'])

            legacy = await graph.ainvoke(dict(query='auth-service 지연 진단',
                                             history=[], events=[], cost_usd=0))
            self.assertTrue(any(c['source'] == 'monitoring' for c in legacy['collected']))
            self.assertIn('CPU', legacy['final'])
            self.assertNotIn('Runbook Not Found', str(legacy['collected']))
        finally:
            await mcp.stop()


if __name__ == '__main__':
    unittest.main()
