"""web_demo_server.py — all_total_vue 에이전트와 브라우저 채팅창으로 대화해보는 데모.

web_chat.html이 바닐라 JS 대신 Vue 3(CDN 글로벌 빌드, 별도 빌드 단계 없음)로 되어
있다는 점만 all_total과 다르다. server.py(8100)의 채팅 API를 같은 출처로 중계한다. 이 스크립트는
- web_chat.html 한 장을 같은 출처(origin)로 띄우고
- optics_lab.js와 허용된 학습 문서를 제공하고
- /chat/stream 요청을 그대로 8100으로 중계(프록시)해서

브라우저의 CORS 제약 없이 실제 에이전트와 대화할 수 있게 해주는 아주 얇은 레이어다.
server.py는 평소처럼(fake/ollama/openai 아무 백엔드로나) 8100에 미리 띄워 놓아야 한다.

실행:
    python3 web_demo_server.py        # http://localhost:8600 에서 채팅 화면 오픈
"""
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

BACKEND = "http://127.0.0.1:8100"
HERE = Path(__file__).parent

app = FastAPI()


@app.get("/")
async def index():
    """브라우저용 단일 Vue HTML 파일을 제공한다.

    Returns:
        채팅 HTML 파일 응답.
    """
    return FileResponse(HERE / "web_chat.html")


@app.get("/optics_lab.js")
async def simulation_script():
    """공식 계산과 장치 개념도를 담은 JavaScript 파일을 제공한다.

    Returns:
        JavaScript 파일 응답.
    """
    return FileResponse(HERE / "optics_lab.js", media_type="text/javascript")


@app.get("/assets/atomic-light-scale.svg")
async def atomic_light_scale():
    """원자 척도와 광학 파장을 비교하는 자체 제작 그림."""
    return FileResponse(HERE / "assets" / "atomic-light-scale.svg", media_type="image/svg+xml")


@app.get("/assets/light-spectrum.svg")
async def light_spectrum():
    """학습 문서에서 사용하는 파장·에너지 스펙트럼 SVG를 제공한다."""
    return FileResponse(HERE / "assets" / "light-spectrum.svg", media_type="image/svg+xml")


@app.get("/documents/{slug}")
async def document(slug: str):
    """허용 목록에 있는 학습 문서만 읽어 JSON으로 반환한다.

    Args:
        slug: 허용된 학습 문서의 파일명(확장자 제외).

    Returns:
        문서 본문을 담은 사전. 허용되지 않은 ID는 HTTP 404.
    """
    allowed = {"optical-equipment", "measurement-and-uncertainty", "ising-and-monte-carlo", "data-and-model-validation", "electron-energy-levels", "absorption-photoelectric", "lithography-process", "resolution-and-focus", "pattern-quality", "alignment-and-verification", "lithography-cd", "scattering-and-sky", "xrd-bragg", "experiment-intake", "light-fundamentals", "grating-prism-spectrometer",
               "shadow-and-diffraction", "michelson-interferometer",
               "lenses-and-optical-instruments", "polarization-and-reflection", "speed-of-light"}
    if slug not in allowed:
        raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")
    return {"content": (HERE / "data" / "runbooks" / f"{slug}.md").read_text()}


@app.get("/health")
async def proxy_health():
    """백엔드 상태 조회를 같은 출처의 프론트엔드 요청으로 중계한다.

    Returns:
        백엔드 상태와 HTTP 코드를 반영한 JSON 응답.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(f"{BACKEND}/health")
    return JSONResponse(r.json(), status_code=r.status_code)


@app.post("/chat")
async def proxy_chat(req: Request):
    """JSON 채팅 요청을 백엔드로 전달하고 응답 상태·본문을 반환한다.

    Args:
        req: JSON 요청 본문을 읽을 HTTP 요청.

    Returns:
        백엔드 응답을 반영한 JSON 응답.
    """
    body = await req.body()
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(f"{BACKEND}/chat", content=body,
                              headers={"content-type": "application/json"})
    return JSONResponse(r.json(), status_code=r.status_code)


@app.get("/chat/stream")
async def proxy_stream(message: str, thread_id: str = "web-demo"):
    """백엔드 SSE 스트림을 브라우저에 중계한다.

    Args:
        message: 사용자가 보낸 채팅 메시지.
        thread_id: 대화를 구분하는 식별자.

    Returns:
        SSE 형식의 StreamingResponse.
    """
    async def relay():
        """상위 서버의 스트림 연결 수명 안에서 받은 바이트를 순서대로 전달한다.

        Yields:
            순서대로 전달할 SSE 텍스트 또는 원본 바이트 조각.
        """
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "GET", f"{BACKEND}/chat/stream",
                params={"message": message, "thread_id": thread_id},
            ) as upstream:
                async for chunk in upstream.aiter_bytes():
                    yield chunk

    return StreamingResponse(relay(), media_type="text/event-stream")


if __name__ == "__main__":
    print("브라우저에서 http://localhost:8600 을 열어보세요 (server.py가 8100에 떠 있어야 합니다)")
    uvicorn.run(app, host="0.0.0.0", port=8600)
