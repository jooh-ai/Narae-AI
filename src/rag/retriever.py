"""검색기 (5단계).

디스크에 저장된 벡터 인덱스를 불러와, 질문에 대한 관련 청크를 돌려준다.
RAG의 'R(Retrieval)' 부분을 한 곳으로 캡슐화해, 7단계에서 LLM과 결합하기 쉽게 한다.
"""
from __future__ import annotations

from pathlib import Path

import config
from src.index.vectorstore import VectorStore
from src.ingest.chunker import Chunk


class Retriever:
    def __init__(self, storage_dir: str | Path = config.STORAGE_DIR) -> None:
        self.storage_dir = Path(storage_dir)
        if not (self.storage_dir / "index.faiss").exists():
            raise FileNotFoundError(
                f"인덱스가 없습니다: {self.storage_dir}\n"
                "먼저 인덱스를 빌드하세요:  python -m scripts.build_index"
            )
        self.store = VectorStore()
        self.store.load(self.storage_dir)

    def retrieve(self, query: str, k: int = config.TOP_K) -> list[tuple[Chunk, float]]:
        """질문과 유사한 청크 k개를 (청크, 점수)로 반환."""
        return self.store.search(query, k)
