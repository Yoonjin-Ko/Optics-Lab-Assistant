"""앱의 실험 용어가 문서로 연결되는지 전체 색인을 검증한다."""
import unittest
from pathlib import Path
from agent.optics import TERM_INDEX,select_experiments,optical_targets


class OpticsTermTests(unittest.TestCase):
    def test_all_terms_are_documented_and_routable(self):
        root=Path(__file__).resolve().parents[1]/'data'/'runbooks'
        for item in TERM_INDEX:
            body=(root/(item['document']+'.md')).read_text()
            self.assertIn(item['definition'],body)
            for term in item['terms']:
                with self.subTest(term=term):
                    self.assertIn(item['document'],select_experiments(term+' 뜻이 뭐야?'))

    def test_definition_question_with_snapshot(self):
        query='[사용자 질문]\n결정구조가 뭐고 격자상수가 뭐야\n\n[현재 가상 실험]\nXRD 면간격 0.3 nm'
        self.assertEqual(optical_targets(query),['xrd-bragg'])
