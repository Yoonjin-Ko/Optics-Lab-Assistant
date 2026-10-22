"""프론트엔드 문서 조회 API는 LLM 없이 동작한다."""
import unittest
from fastapi.testclient import TestClient
from web_demo_server import app


class DocumentsTest(unittest.TestCase):
    def test_documents_and_script(self):
        """외부 LLM 호출 없이 해당 경로의 연결·경계 조건을 검증한다.
        """
        with TestClient(app) as client:
            self.assertEqual(client.get('/').headers.get('cache-control'),'no-store')
            self.assertEqual(client.get('/optics_lab.js').headers.get('cache-control'),'no-store')
            self.assertIn('/optics_lab.js?v=',client.get('/').text)
            for slug in ('electron-energy-levels', 'absorption-photoelectric', 'lithography-process', 'scattering-and-sky', 'xrd-bragg', 'experiment-intake', 'light-fundamentals',
                         'grating-prism-spectrometer', 'shadow-and-diffraction',
                         'michelson-interferometer', 'lenses-and-optical-instruments',
                         'polarization-and-reflection', 'speed-of-light'):
                response = client.get('/documents/' + slug)
                self.assertEqual(response.status_code, 200)
                self.assertIn('광학', response.json()['content'])
            for removed in ('asml-field-work', 'asml-working-method', 'asml-learning-guide'):
                self.assertEqual(client.get('/documents/' + removed).status_code, 404)
            self.assertEqual(client.get('/documents/unknown').status_code, 404)
            self.assertEqual(client.get('/optics_lab.js').status_code, 200)
