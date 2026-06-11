"""임베딩 (4단계) — 교체 가능 구조.

- "tfidf"  : scikit-learn 문자 n-gram TF-IDF. 모델 다운로드 불필요(완전 오프라인).
             한국어를 형태소 분석기 없이 처리하기 위해 char_wb n-gram을 사용한다.
             → 외부망 개발 기본값.
- "sentence-transformers": 의미 검색용 고품질 임베딩. 가중치가 로컬에 있어야 한다.
             → 내부망 운영용 (config에서 백엔드만 바꾸면 됨).

모든 임베더는 L2 정규화된 float32 벡터를 돌려준다 → 코사인 유사도 = 내적.
"""
from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np


def _l2_normalize(mat: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (mat / norms).astype("float32")


class TfidfEmbedder:
    """문자 n-gram TF-IDF 임베더 (오프라인)."""

    name = "tfidf"

    def __init__(self) -> None:
        self._vectorizer = None
        self.dim = 0

    def fit(self, texts: list[str]) -> None:
        from sklearn.feature_extraction.text import TfidfVectorizer

        self._vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), min_df=1)
        self._vectorizer.fit(texts)
        self.dim = len(self._vectorizer.vocabulary_)

    def embed(self, texts: list[str]) -> np.ndarray:
        if self._vectorizer is None:
            raise RuntimeError("fit()을 먼저 호출해야 합니다.")
        mat = self._vectorizer.transform(texts).toarray().astype("float32")
        return _l2_normalize(mat)

    def save(self, directory: Path) -> None:
        with open(directory / "embedder_tfidf.pkl", "wb") as f:
            pickle.dump(self._vectorizer, f)

    def load(self, directory: Path) -> None:
        with open(directory / "embedder_tfidf.pkl", "rb") as f:
            self._vectorizer = pickle.load(f)
        self.dim = len(self._vectorizer.vocabulary_)


class SentenceTransformerEmbedder:
    """의미 임베딩 (내부망 운영용). 가중치가 로컬 캐시에 있어야 동작."""

    name = "sentence-transformers"

    def __init__(self, model_name: str) -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)
        self.dim = self._model.get_sentence_embedding_dimension()

    def fit(self, texts: list[str]) -> None:  # 학습 불필요
        return None

    def embed(self, texts: list[str]) -> np.ndarray:
        vecs = self._model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
        return vecs.astype("float32")

    def save(self, directory: Path) -> None:  # 모델 파일은 캐시에 있으므로 저장 불필요
        return None

    def load(self, directory: Path) -> None:
        return None


def get_embedder():
    """config.EMBEDDING_BACKEND에 맞는 임베더를 생성한다."""
    import config

    backend = config.EMBEDDING_BACKEND
    if backend == "tfidf":
        return TfidfEmbedder()
    if backend == "sentence-transformers":
        return SentenceTransformerEmbedder(config.EMBEDDING_MODEL)
    raise ValueError(f"알 수 없는 EMBEDDING_BACKEND: {backend}")
