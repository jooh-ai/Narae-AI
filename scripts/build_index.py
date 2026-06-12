"""인덱스 빌드 스크립트 (5단계).

문서 폴더 → 로드 → 청킹 → 임베딩 → FAISS 색인 → 디스크 저장.
한 번 실행해 두면 챗봇은 저장된 인덱스를 불러 쓰므로 매번 재색인할 필요가 없다.

사용:
    python -m scripts.build_index                 # config.SAMPLE_DOCS_DIR 사용
    python -m scripts.build_index --docs <경로>    # 다른 문서 폴더 지정
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import config
from src.index.vectorstore import VectorStore
from src.ingest.chunker import chunk_segments
from src.ingest.loaders import SUPPORTED_EXTENSIONS, load_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="규정 문서 인덱스 빌드")
    parser.add_argument("--docs", type=Path, default=config.SAMPLE_DOCS_DIR, help="문서 폴더 경로")
    parser.add_argument("--out", type=Path, default=config.STORAGE_DIR, help="인덱스 저장 경로")
    args = parser.parse_args()

    print(f"문서 폴더 : {args.docs}")
    print(f"지원 형식 : {', '.join(sorted(SUPPORTED_EXTENSIONS))}")

    t0 = time.time()
    segments = load_dir(args.docs)
    print(f"  → 세그먼트 {len(segments)}개 로드")

    chunks = chunk_segments(segments, config.CHUNK_SIZE, config.CHUNK_OVERLAP)
    print(f"  → 청크 {len(chunks)}개 생성")

    if not chunks:
        print("⚠️  색인할 청크가 없습니다. 문서 폴더를 확인하세요.")
        return

    store = VectorStore()
    store.build(chunks)
    store.save(args.out)
    print(
        f"  → 색인 완료 (백엔드: {store.embedder.name}, 차원: {store.embedder.dim})"
    )
    print(f"저장 위치 : {args.out}  ({time.time() - t0:.1f}s)")


if __name__ == "__main__":
    main()
