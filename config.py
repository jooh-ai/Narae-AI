"""프로젝트 전역 설정.

외부망(개발) → 내부망/SageMaker(운영) 이전 시
이 파일의 값만 바꾸면 되도록 한 곳에 모아둡니다.
"""
from pathlib import Path

# --- 경로 ---
BASE_DIR = Path(__file__).resolve().parent
SAMPLE_DOCS_DIR = BASE_DIR / "data" / "sample_docs"   # 더미 규정 문서
STORAGE_DIR = BASE_DIR / "storage"                    # 인덱스 저장 위치

# --- 청킹(3단계) ---
CHUNK_SIZE = 500          # 한 청크의 대략적 글자 수
CHUNK_OVERLAP = 80        # 청크 간 겹침(문맥 보존)

# --- 임베딩(4단계) ---
# "tfidf": scikit-learn 기반, 완전 오프라인(외부망 개발용 기본값)
# "sentence-transformers": 의미 검색용 고품질 모델 (가중치가 로컬 캐시에 있어야 함 → 내부망 운영용)
EMBEDDING_BACKEND = "tfidf"
# 한국어를 잘 처리하는 다국어 임베딩 모델 (로컬 다운로드 후 오프라인 동작)
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# --- 검색(5단계) ---
TOP_K = 4                 # 질문당 가져올 관련 청크 수

# --- LLM(6단계) ---
# "stub": 모델 없이 파이프라인 검증용 / "ollama": 로컬 Ollama / "sagemaker": 내부망 운영
LLM_BACKEND = "stub"
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:7b"
