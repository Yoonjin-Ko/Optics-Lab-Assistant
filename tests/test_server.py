"""실제 MCP 프로세스로 REST 계산과 SSE 응답 완료를 확인한다."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from fastapi.testclient import TestClient
import server
from agent.fake_llm import FastLLM, QualityLLM
from agent.session_store import SqliteSessionStore


class ServerTests(unittest.TestCase):
    def test_rest_and_sse_skip_nodes(self):
        with TemporaryDirectory() as tmp, patch.object(server, '_build_llms',return_value=(
                'fake',FastLLM('fake',0),QualityLLM('fake',0))), patch.object(
                server,'SqliteSessionStore',side_effect=lambda:SqliteSessionStore(Path(tmp)/'session.db')):
            with TestClient(server.app) as client:
                response=client.post('/chat',json={'message':'532 nm 광자 에너지 계산','thread_id':'test'})
                self.assertEqual(response.status_code,200)
                self.assertIn('2.33',response.json()['reply'])
                with client.stream('GET','/chat/stream',params={'message':'산란이 뭐야?','thread_id':'test'}) as stream:
                    body=''.join(stream.iter_text())
                self.assertIn('FinalAnswer',body)
                self.assertIn('[DONE]',body)
                self.assertNotIn('get_monitoring_status',body)
                import httpx
                failure=httpx.HTTPStatusError('secret body', request=httpx.Request('POST','https://example.org'),response=httpx.Response(401))
                with patch.object(server.app.state.deps.quality_llm,'write',side_effect=failure):
                    with client.stream('GET','/chat/stream',params={'message':'마이켈슨 간섭계 띠가 안 보여요','thread_id':'error'}) as stream:
                        error_body=''.join(stream.iter_text())
                self.assertIn('"type": "Error"',error_body)
                self.assertIn('인증',error_body)
                self.assertIn('[DONE]',error_body)
                self.assertNotIn('secret body',error_body)
