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
2. ⬜ 문서 로딩 & 파싱
3. ⬜ 청킹
4. ⬜ 임베딩 + 벡터DB 인덱싱
5. ⬜ 검색 동작 확인
6. ⬜ LLM 연결 (stub → Ollama → SageMaker)
7. ⬜ RAG 결합 (출처 표시 포함)
8. ⬜ 챗 인터페이스 (CLI)

## 설치
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
