"""원문 진위 대신 출처 연결과 발췌 중 근거 보존을 검증한다."""
import json
from pathlib import Path
import unittest
from agent.answer_context import compact_sources

ROOT=Path(__file__).resolve().parents[1]

class SourceTests(unittest.TestCase):
    def test_document_sources_resolve(self):
        registry=json.loads((ROOT/'data/source_registry.json').read_text())
        documents={p.stem for p in (ROOT/'data/runbooks').glob('*.md') if p.name!='README.md'}
        self.assertEqual(documents,set(registry['documents']))
        for document,refs in registry['documents'].items():
            body=(ROOT/'data/runbooks'/f'{document}.md').read_text()
            for ref in refs:
                source=registry['sources'][ref['source']]
                self.assertTrue(source['url'].startswith('https://'))
                self.assertIn(source['url'],body)
                self.assertTrue(source['location'])
                self.assertTrue(source['access'])

    def test_excerpt_preserves_evidence_without_copying_whole_document(self):
        body='# 실험\n\n파장은 공간 주기입니다.\n\n'+'다른 설명입니다.\n\n'*1000
        body+='## 출처와 확인 범위\n\n[교재 해당 절](https://example.org/chapter) — Table 1'
        excerpt=compact_sources('파장이 뭐야',[{'source':'runbook','data':body}])[0]['data']
        self.assertIn('https://example.org/chapter',excerpt)
        self.assertIn('Table 1',excerpt)
        self.assertLess(len(excerpt),len(body))
