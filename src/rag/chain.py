"""RAG 체인 (7단계).

질문 → 검색 → 프롬프트 조립 → LLM 생성 → (답변 + 출처).

규정 챗봇의 핵심 두 가지를 여기서 구현한다.
1) 환각 방지: '주어진 근거 안에서만 답하고, 없으면 모른다고 말하라'는 지침을 명시.
2) 출처 표시: 검색된 조항의 출처(파일/위치)를 답변과 함께 항상 반환.
"""
from __future__ import annotations

from dataclasses import dataclass

import config
from src.ingest.chunker import Chunk
from src.rag.llm import get_llm
from src.rag.retriever import Retriever

SYSTEM_PROMPT = (
    "당신은 회사의 규정·절차를 안내하는 사내 어시스턴트입니다. "
    "반드시 아래에 주어진 '참고 자료'에 근거해서만 답하세요. "
    "참고 자료에 답이 없으면 추측하지 말고 '제공된 규정에서 해당 내용을 찾을 수 없습니다'라고 답하세요. "
    "답변은 한국어로 간결하게 하고, 근거가 된 조항의 출처를 함께 언급하세요."
)

PROMPT_TEMPLATE = """다음은 사내 규정에서 검색된 참고 자료입니다.

{context}

위 참고 자료에만 근거하여 질문에 답하세요.

질문: {question}
답변:"""


@dataclass
class Answer:
    """RAG 결과: 답변 텍스트 + 근거가 된 출처 목록."""

    question: str
    text: str
    sources: list[tuple[Chunk, float]]

    def format(self) -> str:
        """답변 + 출처를 사람이 보기 좋게 문자열로."""
        lines = [self.text, "", "📚 참고 조항:"]
        if self.sources:
            for chunk, score in self.sources:
                lines.append(f"  • {chunk.citation}  (관련도 {score:.2f})")
        else:
            lines.append("  (관련 조항 없음)")
        return "\n".join(lines)


def _build_context(sources: list[tuple[Chunk, float]]) -> str:
    """검색된 청크들을 프롬프트용 참고 자료 텍스트로 조립."""
    blocks = []
    for i, (chunk, _score) in enumerate(sources, start=1):
        blocks.append(f"[자료 {i}] (출처: {chunk.citation})\n{chunk.text}")
    return "\n\n".join(blocks)


class RagChain:
    def __init__(self, retriever: Retriever | None = None, llm=None, min_score: float = 0.05) -> None:
        self.retriever = retriever or Retriever()
        self.llm = llm or get_llm()
        # 관련도가 이 값보다 낮은 청크는 근거에서 제외(엉뚱한 출처 방지)
        self.min_score = min_score

    def ask(self, question: str, k: int = config.TOP_K) -> Answer:
        hits = self.retriever.retrieve(question, k)
        sources = [(c, s) for c, s in hits if s >= self.min_score]

        # 근거가 전혀 없으면 LLM 호출 없이 즉시 '모른다' 응답(비용·환각 방지)
        if not sources:
            return Answer(
                question=question,
                text="제공된 규정에서 해당 내용을 찾을 수 없습니다.",
                sources=[],
            )

        context = _build_context(sources)
        prompt = PROMPT_TEMPLATE.format(context=context, question=question)
        text = self.llm.generate(prompt, system=SYSTEM_PROMPT)
        return Answer(question=question, text=text, sources=sources)


if __name__ == "__main__":
    chain = RagChain()
    print(f"LLM 백엔드: {chain.llm.name}\n")
    for q in ["연차휴가는 며칠인가요?", "비밀번호는 몇 자 이상이어야 해?", "회사 주차장은 어디 있어?"]:
        print(f"❓ {q}")
        print(chain.ask(q).format())
        print("-" * 60)
