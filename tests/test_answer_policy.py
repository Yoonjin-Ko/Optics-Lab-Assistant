"""주제별 정답이 아닌 공통 출력 계약을 검증한다."""
import unittest
from agent.optics import answer_policy, answer_violations


class AnswerPolicyTests(unittest.TestCase):
    def test_same_policy_across_topics(self):
        for topic in ['반사','간섭','결정','측정','전자 상태']:
            with self.subTest(topic=topic):
                self.assertEqual(answer_policy(topic+' 설명해줘')['max_chars'],900)
                self.assertTrue(answer_violations(topic+' 설명해줘','긴 설명.'*250))
                self.assertFalse(answer_violations(topic+' 설명해줘','질문에 대한 결론을 먼저 설명합니다. 필요한 조건과 근거를 짧게 덧붙입니다.'))

    def test_explicit_detail_and_snapshot(self):
        self.assertTrue(answer_policy('자세히 유도해줘')['detailed'])
        self.assertFalse(answer_policy('[사용자 질문]\n간단히 설명해줘\n\n[현재 가상 실험]\n상세 자료')['detailed'])
        self.assertTrue(answer_violations('설명해줘','### 전체 개론\n  - 중첩 설명을 길게 작성합니다.'))

class CompletedExcerptTests(unittest.TestCase):
    def test_preserves_complete_lead_but_not_unfinished_or_math(self):
        from agent.answer_context import completed_answer_excerpt
        lead='물체 거리가 고정되어 있으면 초점거리를 늘릴수록 상의 크기가 커집니다.'
        self.assertEqual(completed_answer_excerpt('간단히 설명',lead+'\n\n'+'긴 설명입니다.'*300),lead)
        self.assertIsNone(completed_answer_excerpt('설명','아직 끝나지 않은'))
        self.assertIsNone(completed_answer_excerpt('설명',r'\[ 미완성 수식'))


class WriterRequestTests(unittest.TestCase):
    def test_snapshot_instruction_removed_and_inputs_separated(self):
        from agent.answer_context import writer_request
        query='[사용자 질문]\n목표 배율을 얻으려면?\n\n[현재 가상 실험]\nf=10 cm. 이 결과를 설명해줘.\n[광학 계산 입력]\n{"parameters":{"focal":{"value":10,"unit":"cm"}}}\n\n가상 모델입니다.'
        prompt=writer_request(query,[])
        self.assertNotIn('이 결과를 설명해줘',prompt)
        self.assertIn('현재 상태의 계산 입력 (목표값 아님)',prompt)
        self.assertIn('"value": 10',prompt)
        self.assertIn('가상 모델입니다.',prompt)
        self.assertEqual(prompt.count('목표 배율을 얻으려면?'),1)

    def test_invalid_snapshot_json_preserved(self):
        from agent.answer_context import experiment_evidence
        self.assertIn('{broken',experiment_evidence('f=10\n[광학 계산 입력]\n{broken'))

    def test_sources_do_not_replace_last_question(self):
        from agent.answer_context import writer_request
        query='[사용자 질문]\n현재 물질은 어떤 현상을 보여?\n\n[현재 가상 실험]\n현재 모드=metal, 일함수4.7eV'
        prompt=writer_request(query,['긴 참고 문서이며 전체를 요약하라는 요청이 아님'],'짧게 작성')
        self.assertLess(prompt.index('긴 참고 문서'),prompt.index('현재 모드=metal'))
        self.assertLess(prompt.index('현재 모드=metal'),prompt.index('## 지금 답할 사용자 질문'))
        self.assertEqual(prompt.count('현재 물질은 어떤 현상을 보여?'),1)
