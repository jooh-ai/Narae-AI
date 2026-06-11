"""벡터 저장소 (4단계).

청크들을 임베딩해 FAISS 인덱스로 색인하고, 질문과 가장 유사한 청크를 찾아준다.
벡터가 L2 정규화돼 있으므로 내적(IndexFlatIP) = 코사인 유사도.

디스크에 저장/로드할 수 있어, 한 번 색인하면 매번 다시 임베딩하지 않아도 된다.
"""
from __future__ import annotations

import pickle
from pathlib import Path

import faiss
import numpy as np

from src.ingest.chunker import Chunk
from src.index.embedder import get_embedder


class VectorStore:
    def __init__(self, embedder=None) -> None:
        self.embedder = embedder or get_embedder()
        self._index = None
        self._chunks: list[Chunk] = []

    def build(self, chunks: list[Chunk]) -> None:
        """청크 리스트로 인덱스를 구축한다."""
        if not chunks:
            raise ValueError("청크가 비어 있습니다.")
        self._chunks = chunks
        texts = [c.text for c in chunks]
        self.embedder.fit(texts)          # tfidf는 코퍼스 학습, ST는 no-op
        vectors = self.embedder.embed(texts)
        self._index = faiss.IndexFlatIP(vectors.shape[1])
        self._index.add(vectors)

    def search(self, query: str, k: int) -> list[tuple[Chunk, float]]:
        """질문과 가장 유사한 청크 k개를 (청크, 점수)로 반환."""
        if self._index is None:
            raise RuntimeError("build() 또는 load()를 먼저 호출하세요.")
        qvec = self.embedder.embed([query])
        scores, idxs = self._index.search(qvec, min(k, len(self._chunks)))
        results: list[tuple[Chunk, float]] = []
        for idx, score in zip(idxs[0], scores[0]):
            if idx != -1:
                results.append((self._chunks[idx], float(score)))
        return results

    def save(self, directory: str | Path) -> None:
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(directory / "index.faiss"))
        with open(directory / "chunks.pkl", "wb") as f:
            pickle.dump(self._chunks, f)
        self.embedder.save(directory)

    def load(self, directory: str | Path) -> None:
        directory = Path(directory)
        self._index = faiss.read_index(str(directory / "index.faiss"))
        with open(directory / "chunks.pkl", "rb") as f:
            self._chunks = pickle.load(f)
        self.embedder.load(directory)


if __name__ == "__main__":
    # 빠른 점검: 더미 문서 색인 후 검색 테스트
    import config
    from src.ingest.chunker import chunk_segments
    from src.ingest.loaders import load_dir

    segs = load_dir(config.SAMPLE_DOCS_DIR)
    chunks = chunk_segments(segs, config.CHUNK_SIZE, config.CHUNK_OVERLAP)
    store = VectorStore()
    store.build(chunks)
    print(f"청크 {len(chunks)}개 색인 완료 (백엔드: {store.embedder.name}, 차원: {store.embedder.dim})\n")

    for q in ["연차휴가는 며칠인가요?", "비밀번호 규칙 알려줘", "출장 숙박비 상한은?"]:
        print(f"Q: {q}")
        for chunk, score in store.search(q, config.TOP_K):
            preview = chunk.text.replace("\n", " ")[:40]
            print(f"   [{score:.3f}] {chunk.citation}: {preview}")
        print()
