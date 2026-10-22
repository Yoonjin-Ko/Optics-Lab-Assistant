"""외부 LLM 없이 문서 연결·계산 흐름을 검증하는 결정적 응답 모델."""
import re

from langsmith import traceable


class FakeLLM:
    def __init__(self, name: str, usd_per_1k_tokens: float):
        """모델 식별자와 비용 추정용 단가를 보관한다.

        Args:
            name: 모델 표시 이름 또는 호출할 MCP capability 이름.
            usd_per_1k_tokens: 토큰 1,000개당 비용 추정용 단가. 실제 청구와 다를 수 있다.
        """
        self.name = name
        self.usd_per_1k = usd_per_1k_tokens

    def _usage(self, prompt: str, completion: str) -> dict:
        """문자열 길이로 fake 모드의 가상 토큰 사용량과 비용을 추정한다.

        Args:
            prompt: 토큰 추정에 사용할 입력 문자열.
            completion: 토큰 추정에 사용할 출력 문자열.

        Returns:
            모델 이름·추정 토큰·가상 비용 사전.
        """
        tokens = (len(prompt) + len(completion)) // 4 + 1
        return {"model": self.name, "tokens": tokens,
                "usd": round(tokens / 1000 * self.usd_per_1k, 6)}


class FastLLM(FakeLLM):
    """분류·계획 등 짧고 정형적인 단계 전담 (저비용)."""


    @traceable(run_type="llm", name="fast_llm.chat")
    async def chat(self, query: str, history: list[dict], on_token=None) -> tuple[str, dict]:
        """일반 대화에 응답하고 대화 이력을 참고한다."""
        for msg in reversed(history):
            m = re.search(r"제 이름은 (\S+?)입니다", msg.get("content", ""))
            if m and re.search(r"이름이 뭐", query):
                reply = f"{m.group(1)}님이라고 말씀하셨어요. 무엇을 도와드릴까요?"
                if on_token is not None:
                    on_token(reply)
                return reply, self._usage(query, reply)
        m = re.search(r"제 이름은 (\S+?)입니다", query)
        if m:
            reply = f"안녕하세요, {m.group(1)}님! 무엇을 도와드릴까요?"
        else:
            reply = "안녕하세요! 무엇을 도와드릴까요?"
        if on_token is not None:
            on_token(reply)
        return reply, self._usage(query, reply)


class QualityLLM(FakeLLM):
    """최종 답변 작성 전담 (고품질·고비용)."""

    @traceable(run_type="llm", name="quality_llm.write")
    async def write(self, query: str, collected: list[dict], attempt: int,
              feedback: str | None, on_token=None) -> tuple[str, dict]:
        """수집 자료와 질문 모드에 맞춰 답변을 작성한다."""
        docs=[c["data"] for c in collected if c["source"]=="runbook"]
        lines=[]
        for doc in docs:
            for line in doc.splitlines():
                line=line.strip()
                if not line or line.startswith(('#','<','>','\\')):continue
                if len("\n".join(lines+[line]))>650:break
                lines.append(line)
            if lines:break
        draft="[fake 모드: 문서 연결 확인용] 실험 원리·참고 내용\n"+"\n".join(lines)
        if not lines:draft="[fake 모드] 관련 문서가 없습니다. 실험 종류를 알려주세요."
        if on_token is not None:on_token(draft)
        return draft,self._usage(query,draft)
