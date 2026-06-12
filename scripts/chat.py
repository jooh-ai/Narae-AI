"""대화형 챗 CLI (8단계).

저장된 인덱스를 불러와, 터미널에서 사내 규정에 대해 질문하고 답변+출처를 받는다.

사용:
    python -m scripts.build_index     # (최초 1회) 인덱스 빌드
    python -m scripts.chat            # 대화 시작

종료: 'exit', 'quit', '종료' 입력 또는 Ctrl+C / Ctrl+D
"""
from __future__ import annotations

import sys

import config
from src.rag.chain import RagChain

_EXIT_WORDS = {"exit", "quit", "종료", "나가기"}


def main() -> None:
    print("=" * 60)
    print(" 사내 규정 챗봇  (개발 모드)")
    print(f"   LLM 백엔드     : {config.LLM_BACKEND}")
    print(f"   임베딩 백엔드  : {config.EMBEDDING_BACKEND}")
    print("   종료하려면 'exit' 또는 '종료' 입력")
    print("=" * 60)

    try:
        chain = RagChain()
    except FileNotFoundError as e:
        print(f"\n⚠️  {e}")
        sys.exit(1)

    while True:
        try:
            question = input("\n❓ 질문> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n안녕히 가세요.")
            break

        if not question:
            continue
        if question.lower() in _EXIT_WORDS:
            print("안녕히 가세요.")
            break

        answer = chain.ask(question)
        print("\n" + answer.format())


if __name__ == "__main__":
    main()
