"""선택적 Tavily 검색. 질문만 전송하고 키·API 오류 본문은 반환하지 않는다."""
import os
import re
import json
from pathlib import Path
from urllib.parse import urlsplit
import httpx
from .optics import user_question


TRUSTED_DOMAINS=tuple(json.loads((Path(__file__).resolve().parent.parent/"data"/"search_domains.json").read_text())["domains"])


def trusted_domain(url):
    """정확한 호스트·하위 도메인만 허용한다. 문자열 포함 검사로 판정하지 않는다."""
    try:
        parsed=urlsplit(url)
        if parsed.scheme not in ("https","http") or parsed.username is not None or parsed.password is not None:
            return None
        host=(parsed.hostname or "").lower().rstrip(".").encode("idna").decode("ascii")
        if parsed.port not in (None,80,443):return None
    except (ValueError,UnicodeError):
        return None
    return host if any(host==d or host.endswith("."+d) for d in TRUSTED_DOMAINS) else None


def needs_web_search(query):
    q = user_question(query)
    return bool(re.search(r'검색|찾아|최신|출처|논문|우라늄|uranium|물질별|실제\s*값|문헌', q, re.I))


async def search_optics_web(query):
    key = os.getenv('TAVILY_API_KEY', '').strip()
    if not key:
        return {'status': 'not_configured', 'results': []}
    q = user_question(query).strip()[:500]
    if not q:
        return {'status': 'empty_query', 'results': []}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post('https://api.tavily.com/search',
                headers={'Authorization': 'Bearer '+key}, json={
                    'query': q, 'search_depth': 'basic', 'max_results': 6,
                    'include_domains': list(TRUSTED_DOMAINS), 'include_domains_mode': 'restrict',
                    'include_answer': False, 'include_raw_content': False})
            if response.status_code != 200:
                return {'status': 'http_error', 'http_status': response.status_code, 'results': []}
            data = response.json()
        results = []
        filtered=0
        seen=set()
        for item in data.get('results', []):
            url = str(item.get('url', ''))
            domain=trusted_domain(url)
            if not domain:
                filtered+=1
                continue
            if url in seen:continue
            seen.add(url)
            results.append({'title': str(item.get('title', ''))[:200],
                            'url': url, 'domain': domain, 'content': str(item.get('content', ''))[:2500]})
            if len(results)>=3:break
        return {'status': 'ok' if results else ('no_trusted_results' if filtered else 'no_results'),
                'results': results, 'source_policy': 'allowlist', 'filtered_count': filtered}
    except (httpx.HTTPError, ValueError, TypeError):
        return {'status': 'unavailable', 'results': []}
