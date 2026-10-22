"""광학 MCP 서버: 학습 문서 Resource, 공식 계산·웹 검색 Tool."""
from pathlib import Path

from fastmcp import FastMCP

mcp = FastMCP(name="optics-lab")

DATA_DIR = Path(__file__).parent / "data"


@mcp.tool()
async def search_optics_web(query: str) -> dict:
    """광학 질문의 외부 참고 자료를 Tavily로 검색한다. 키가 없으면 검색하지 않는다."""
    from agent.web_search import search_optics_web as search
    return await search(query)


@mcp.tool()
def calculate_optics(operation: str, parameters: dict) -> dict:
    """광자 에너지·Bragg·Michelson·Malus·얇은 렌즈 및 등록된 탐구 목적을 계산한다.

    parameters의 각 항목은 {value: 유한 숫자, unit: 명시 단위} 형식이다.
    지원식·단위·물리 조건을 검증하고 입력 부족/불가능 조건에서는 결과를 만들지 않는다.
    operation='inquiry'는 별도 버전 계약 {version, kind, index, settings}를 받는다.
    settings의 단위는 UI 계약에 고정되어 있으며 서버가 다시 범위를 검사한다.
    """
    from agent.optics_calculations import calculate_optics as calculate
    return calculate(operation, parameters)


@mcp.resource("optics://documents/{topic}")
def get_optics_document(topic: str) -> str:
    """문서 ID로 광학 학습·점검 Markdown을 반환한다."""
    # 문서 ID는 단일 경로 조각으로 제한한다.
    root = DATA_DIR / "runbooks"
    # 외부 입력으로 문서 디렉터리 밖 파일을 읽지 못하도록 제한한다.
    if not topic or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789-" for ch in topic):
        return "# Runbook Not Found\n\nInvalid runbook identifier"
    # 매 호출마다 디스크를 읽으므로 같은 ID의 문서 내용 변경은 다음 조회에 반영된다.
    runbook_path = root / f"{topic}.md"
    if not runbook_path.exists():
        return f"# Runbook Not Found\n\nNo optics document for topic: {topic}"
    return runbook_path.read_text()


if __name__ == "__main__":
    try:
        mcp.run(show_banner=False)
    except TypeError:   # 구버전 fastmcp 호환
        mcp.run()
