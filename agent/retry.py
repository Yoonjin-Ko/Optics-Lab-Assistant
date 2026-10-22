"""일시적 오류만 지수 백오프로 재시도한다."""
import asyncio

from langsmith import traceable


@traceable(name="with_retry")
async def with_retry(fn, *args, retries: int = 3, base_delay: float = 0.3, **kwargs):
    """비동기 호출의 시간 초과만 제한 횟수 내에서 지수 간격으로 재시도한다.

    Args:
        fn: 호출할 비동기 함수.
        retries: 첫 호출을 포함한 최대 시도 횟수.
        base_delay: 첫 재시도 전 대기 시간(초). 이후 3배씩 증가한다.
        args: 대상 함수에 전달할 위치 인자.
        kwargs: 대상 함수에 전달할 키워드 인자.

    Returns:
        성공 결과와 실제 재시도 횟수의 튜플. 한도 초과나 다른 예외는 전파한다.
    """
    attempt = 0
    while True:
        attempt += 1
        try:
            result = await fn(*args, **kwargs)
            return result, attempt - 1   # (결과, 재시도 횟수)
        except asyncio.TimeoutError:
            if attempt >= retries:
                raise
            delay = base_delay * (3 ** (attempt - 1))
            await asyncio.sleep(delay)
