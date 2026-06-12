"""청킹 (3단계).

긴 세그먼트를 검색 단위(청크)로 자른다.
- 규정 문서는 "## 제N조" 같은 조항 경계가 의미 단위이므로, 그 경계를 우선 존중한다.
- 조항이 여전히 길면 글자 수(CHUNK_SIZE) 기준으로 다시 자르되, 일부를 겹쳐(CHUNK_OVERLAP)
  문맥이 끊기지 않게 한다.
- 잘라도 출처(source/locator)는 그대로 물려준다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .loaders import Segment


@dataclass
class Chunk:
    """검색/임베딩의 최소 단위."""

    text: str
    source: str
    locator: str = ""
    metadata: dict = field(default_factory=dict)

    @property
    def citation(self) -> str:
        return f"{self.source} ({self.locator})" if self.locator else self.source


# "## 제3조", "제 3 조", "1." 등 조항/항목 시작을 경계로 인식
_SECTION_RE = re.compile(r"(?m)^(?=\s*(?:#{1,6}\s*)?제\s*\d+\s*조)")


def _split_by_section(text: str) -> list[str]:
    """조항(제N조) 경계로 1차 분할. 경계가 없으면 통째로 반환."""
    parts = [p.strip() for p in _SECTION_RE.split(text) if p.strip()]
    return parts or ([text.strip()] if text.strip() else [])


def _split_by_size(text: str, size: int, overlap: int) -> list[str]:
    """글자 수 기준 분할(겹침 포함). 문단/문장 경계를 가급적 보존."""
    if len(text) <= size:
        return [text]

    chunks: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + size, n)
        # 단어 중간 절단 완화: 마지막 줄바꿈/마침표에서 끊기 시도
        if end < n:
            window = text[start:end]
            cut = max(window.rfind("\n"), window.rfind(". "), window.rfind("다. "))
            if cut > size * 0.5:  # 너무 앞이면 무시
                end = start + cut + 1
        chunks.append(text[start:end].strip())
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return [c for c in chunks if c]


def chunk_segment(seg: Segment, size: int, overlap: int) -> list[Chunk]:
    """세그먼트 하나를 청크 리스트로."""
    chunks: list[Chunk] = []
    for section in _split_by_section(seg.text):
        for piece in _split_by_size(section, size, overlap):
            chunks.append(
                Chunk(text=piece, source=seg.source, locator=seg.locator, metadata=dict(seg.metadata))
            )
    return chunks


def chunk_segments(segments: list[Segment], size: int, overlap: int) -> list[Chunk]:
    """여러 세그먼트를 한꺼번에 청킹."""
    chunks: list[Chunk] = []
    for seg in segments:
        chunks.extend(chunk_segment(seg, size, overlap))
    return chunks


if __name__ == "__main__":
    # 빠른 점검: 더미 문서를 로드 → 청킹 결과 출력
    import config
    from .loaders import load_dir

    segs = load_dir(config.SAMPLE_DOCS_DIR)
    chunks = chunk_segments(segs, config.CHUNK_SIZE, config.CHUNK_OVERLAP)
    print(f"세그먼트 {len(segs)}개 → 청크 {len(chunks)}개")
    for c in chunks:
        preview = c.text.replace("\n", " ")[:45]
        print(f"  - [{c.citation}] ({len(c.text)}자) {preview}...")
