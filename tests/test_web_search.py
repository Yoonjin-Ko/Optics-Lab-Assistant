import json
import unittest
from unittest.mock import patch
import httpx
from agent.web_search import search_optics_web, needs_web_search, trusted_domain, TRUSTED_DOMAINS


class SearchTests(unittest.IsolatedAsyncioTestCase):
    async def test_key_missing(self):
        with patch.dict('os.environ', {'TAVILY_API_KEY': ''}):
            self.assertEqual((await search_optics_web('광학 검색'))['status'], 'not_configured')

    async def test_request_and_result(self):
        async def handler(request):
            self.assertEqual(request.headers['Authorization'], 'Bearer test-only')
            body=request.content.decode()
            payload=json.loads(body)
            self.assertEqual(payload['include_domains_mode'],'restrict')
            self.assertEqual(payload['include_domains'],list(TRUSTED_DOMAINS))
            self.assertNotIn('비공개실험조건',body)
            return httpx.Response(200,json={'results':[
                {'title':'Research','url':'https://www.nist.gov/paper','content':'measured data'},
                {'title':'bad','url':'javascript:alert(1)','content':'bad'}]})
        real_client=httpx.AsyncClient
        with patch.dict('os.environ',{'TAVILY_API_KEY':'test-only'}), patch('agent.web_search.httpx.AsyncClient',side_effect=lambda **kw:real_client(transport=httpx.MockTransport(handler),**kw)):
            data=await search_optics_web('[사용자 질문]\n우라늄 페르미 준위\n\n[현재 가상 실험]\n비공개실험조건')
        self.assertEqual(data['status'],'ok')
        self.assertEqual(len(data['results']),1)

    async def test_failure_does_not_leak(self):
        real_client=httpx.AsyncClient
        with patch.dict('os.environ',{'TAVILY_API_KEY':'test-only'}), patch('agent.web_search.httpx.AsyncClient',side_effect=lambda **kw:real_client(transport=httpx.MockTransport(lambda r:httpx.Response(401,text='secret server body')),**kw)):
            data=await search_optics_web('검색')
        self.assertEqual(data['status'],'http_error')
        self.assertNotIn('secret',str(data))

    def test_routing(self):
        self.assertTrue(needs_web_search('우라늄의 페르미 준위는?'))
        self.assertTrue(needs_web_search('GaAs 물성 논문 찾아줘'))
        self.assertFalse(needs_web_search('산란이 뭐야?'))

    def test_host_boundaries(self):
        for url in ['https://nist.gov/paper','https://www.nist.gov/paper','https://opg.optica.org/paper']:
            self.assertIsNotNone(trusted_domain(url))
        for url in ['https://nist.gov.evil.example/paper','https://notnist.gov','https://nist.gov@evil.example',
                    'https://evil.example/?source=nist.gov','javascript:alert(1)','https://nist.gov:9999/path']:
            self.assertIsNone(trusted_domain(url),url)

    async def test_filtered_results_do_not_trigger_open_search(self):
        calls=[]
        def handler(request):
            calls.append(request)
            return httpx.Response(200,json={'results':[{'url':'https://unknown.example/a','title':'unknown','content':'unreviewed'}]})
        real_client=httpx.AsyncClient
        with patch.dict('os.environ',{'TAVILY_API_KEY':'test-only'}),patch('agent.web_search.httpx.AsyncClient',side_effect=lambda **kw:real_client(transport=httpx.MockTransport(handler),**kw)):
            data=await search_optics_web('광학 문헌 검색')
        self.assertEqual(data['status'],'no_trusted_results')
        self.assertEqual(data['results'],[])
        self.assertEqual(len(calls),1)
