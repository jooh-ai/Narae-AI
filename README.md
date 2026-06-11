# 사내 규정 RAG 챗봇 (외부망 개발용 스캐폴딩)

회사의 규정·절차 문서를 학습시켜 질문에 답하는 RAG(검색 증강 생성) 챗봇입니다.
**보안 문서는 내부망에서만 다루므로**, 외부망에서는 형식만 흉내 낸 **더미 데이터**로
파이프라인을 개발하고, 완성된 코드를 내부망/SageMaker로 이전합니다.

## 설계 원칙
- **LLM·임베딩·OCR을 전부 로컬/교체 가능 구조로** — 외부망(더미/Ollama) ↔ 내부망(SageMaker) 이전 용이
- **모든 답변에 출처(문서·위치) 표시** — 규정 챗봇의 "그럴듯한 오답" 방지

## 폴더 구조
```
.
├── config.py              # 전역 설정 (모델, 경로, 백엔드 등)
├── requirements.txt
├── data/
│   └── sample_docs/       # 더미 규정 문서 (실제 문서 X)
└── src/                   # 단계별로 채워나갈 모듈
```

## 진행 단계
1. ✅ 프로젝트 뼈대 + 환경 + 더미 문서
2. ✅ 문서 로딩 & 파싱 (`src/ingest/loaders.py`)
3. ✅ 청킹 (`src/ingest/chunker.py`)
4. ✅ 임베딩 + 벡터DB 인덱싱 (`src/index/`)
5. ✅ 검색 API (`src/rag/retriever.py`, `scripts/build_index.py`)
6. ✅ LLM 연결 — stub/ollama/sagemaker (`src/rag/llm.py`)
7. ✅ RAG 결합 + 출처 표시 (`src/rag/chain.py`)
8. ✅ 챗 인터페이스 CLI (`scripts/chat.py`)

## 설치 & 실행
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python -m scripts.build_index    # (최초 1회) 인덱스 빌드
python -m scripts.chat           # 대화형 챗봇 실행
```

## 내부망 이전 시 바꿀 것 (config.py)
외부망 개발 → 내부망 운영 전환은 **코드 수정 없이 설정만** 바꾼다.
- `EMBEDDING_BACKEND`: `"tfidf"` → `"sentence-transformers"` (모델 가중치 반입 필요)
- `LLM_BACKEND`: `"stub"` → `"sagemaker"` + `SAGEMAKER_ENDPOINT` 지정
- 실제 규정 문서를 `data/real_docs/`(gitignore됨)에 두고 `build_index --docs`로 재색인

## 향후 확장
- 이미지/스캔 PDF용 **로컬 OCR**(Tesseract/PaddleOCR) 로더 추가
- 사용자별 **열람 권한 필터링**(검색 단계에서 접근 가능한 문서만)
- 웹 UI
