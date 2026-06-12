# SageMaker로 LLM 띄우기 — 초보자용 단계별 가이드

이 문서는 **SageMaker를 처음 쓰는 사람**이, 우리 규정 챗봇의 LLM(언어모델)을
AWS SageMaker에 올려 운영하기까지의 절차를 쉽게 설명한다.

---

## 0. 먼저 — SageMaker가 뭔가? (1분 개념)

- **SageMaker** = AWS가 제공하는 "머신러닝 종합 작업실".
- 우리가 쓸 기능은 딱 하나: **엔드포인트(Endpoint)**.
  - 엔드포인트 = LLM을 **24시간 켜놓고, 호출하면 답을 주는 API 서버**.
  - 비유: 식당 주방에 요리사(LLM)를 한 명 상주시켜 두고, 주문(질문)이 오면 요리(답변)를 내주는 것.
- **JumpStart** = 오픈소스 LLM(Llama, Qwen 등)을 **클릭 몇 번으로** 엔드포인트로 배포해주는 기능.
  모델을 직접 내려받아 설정할 필요가 없어 초보자에게 가장 쉽다.

## 우리 챗봇에서 SageMaker의 위치

```
직원 브라우저 → [웹 앱 서버(우리 코드)] → 검색(벡터DB)
                         │
                         └→ [SageMaker 엔드포인트 = LLM]  ← 이 문서가 만드는 부분
```

웹 앱은 우리가 만든 코드(`src/`)가 돌고, **LLM 추론만 SageMaker가 담당**한다.
우리 코드의 `src/rag/llm.py`의 `SageMakerLLM`이 이 엔드포인트를 호출한다.

---

## 1. 사전 준비 (보안팀과 함께)

- [ ] **AWS 계정 + SageMaker 사용 권한** (회사 클라우드 담당자에게 요청)
- [ ] **리전(Region)** 결정 — 보통 서울 `ap-northeast-2`
- [ ] **보안 승인** — "민감 규정을 AWS에서 다뤄도 되는가" 확인 (가장 중요, 앞 단계에서 합의됐다고 가정)
- [ ] **GPU 인스턴스 한도(Quota)** — LLM은 GPU가 필요. 신규 계정은 GPU 한도가 0일 수 있어
      미리 한도 증설 요청이 필요할 수 있다 (담당자/AWS Support에 요청).

---

## 2. 절차 — 콘솔(클릭) 방식 (초보자 추천)

### Step 1. SageMaker Studio 열기
1. AWS 콘솔 로그인 → 우측 상단에서 **리전을 서울로** 변경.
2. 검색창에 `SageMaker` 입력 → **Amazon SageMaker** 진입.
3. 좌측 메뉴 **Studio** → 도메인이 없으면 "Set up for single user"로 생성(몇 분 소요) → **Open Studio**.

### Step 2. JumpStart에서 모델 고르기
1. Studio 안에서 **JumpStart**(또는 좌측의 모델 허브) 클릭.
2. 검색창에 모델 이름 입력. 한국어 규정 챗봇이면 한국어가 강한 모델 추천:
   - 예: `Llama 3.1 8B Instruct`, `Qwen2.5 7B Instruct` 등 (Instruct/Chat 버전)
3. 모델 카드 클릭 → 라이선스/설명 확인.

### Step 3. 배포(Deploy)
1. 모델 카드에서 **Deploy** 버튼 클릭.
2. **Instance type(인스턴스 종류)** 선택 = LLM이 돌아갈 GPU 서버.
   - 7~8B 모델 시작용: `ml.g5.2xlarge` 정도 (GPU 1장).
   - 더 큰 모델/빠른 속도가 필요하면 상위 인스턴스.
3. **Endpoint name(엔드포인트 이름)** 을 적어둔다. 예: `regulation-llm-endpoint`
4. **Deploy** → 상태가 `Creating` → `InService`가 될 때까지 대기(보통 5~15분).

> ⚠️ `InService`가 되는 순간부터 **시간당 과금**이 시작된다(아래 6번 비용 관리 참고).

### Step 4. (보안) VPC 격리 — 운영 시
초기 테스트는 기본 설정으로도 되지만, **민감 데이터 운영**에서는 배포 시
**VPC / 서브넷 / 보안그룹**을 지정해 인터넷과 분리한다. (클라우드 담당자와 함께 설정)

---

## 3. 우리 코드와 연결하기

엔드포인트가 `InService`가 되면, `config.py`만 수정하면 끝이다.

```python
# config.py
LLM_BACKEND = "sagemaker"                       # stub → sagemaker
SAGEMAKER_ENDPOINT = "regulation-llm-endpoint"  # Step 3에서 정한 이름
AWS_REGION = "ap-northeast-2"
```

그리고 서버 환경에 AWS 자격증명(권한)과 boto3가 있어야 한다:

```bash
pip install boto3
aws configure        # 또는 IAM 역할(EC2/ECS에 부여)로 권한 제공
```

테스트:
```bash
python -c "from src.rag.llm import get_llm; print(get_llm().generate('연차휴가는 며칠인가요?'))"
python -m scripts.serve   # 웹 서버 실행 → 실제 LLM 답변 확인
```

> 모델 컨테이너마다 입출력 형식이 조금씩 다르다. 우리 `SageMakerLLM`은
> `{"inputs": ..., "parameters": {...}}` 형식으로 보내고 응답을 방어적으로 파싱한다.
> 만약 형식 오류가 나면, 해당 모델 카드의 "예시 payload"에 맞춰
> `src/rag/llm.py`의 `SageMakerLLM.generate()` 부분만 조정하면 된다.

---

## 4. (선택) 코드로 배포하는 방식 — SDK

콘솔 대신 파이썬으로 배포할 수도 있다(자동화에 유리). 개념만:

```python
from sagemaker.jumpstart.model import JumpStartModel

model = JumpStartModel(model_id="meta-textgeneration-llama-3-1-8b-instruct")
predictor = model.deploy(
    instance_type="ml.g5.2xlarge",
    endpoint_name="regulation-llm-endpoint",
)
print(predictor.endpoint_name)
```

처음에는 **콘솔(클릭) 방식**으로 익숙해진 뒤 SDK로 넘어가길 권한다.

---

## 5. 임베딩 모델은?

- LLM은 위처럼 SageMaker 엔드포인트로 띄운다.
- **임베딩 모델**은 보통 웹 앱 서버에서 직접 돌린다(`EMBEDDING_BACKEND="sentence-transformers"`,
  모델 가중치를 서버에 반입). 트래픽이 크면 임베딩도 별도 SageMaker 엔드포인트로 분리할 수 있다.

---

## 6. 💸 비용 관리 — 초보자가 가장 많이 당하는 함정

- **엔드포인트는 켜져 있는 내내(시간당) 과금된다.** 질문을 안 해도 GPU 서버가 떠 있으면 비용 발생.
- **테스트가 끝나면 반드시 엔드포인트를 삭제(Delete)** 하라.
  - 콘솔: SageMaker → Endpoints → 해당 항목 선택 → **Delete**.
  - 다시 필요하면 재배포하면 된다.
- 운영 단계에서 트래픽이 들쭉날쭉하면 **Serverless Inference**나 **자동 스케일링**을 검토.
- 항상 **비용 알림(AWS Budgets)** 을 설정해 두면 예상 밖 청구를 막을 수 있다.

---

## 7. 체크리스트 (한 장 요약)

1. [ ] 보안 승인 + GPU 한도 확보
2. [ ] SageMaker Studio 진입 (리전: 서울)
3. [ ] JumpStart에서 한국어 LLM 선택
4. [ ] Deploy → 인스턴스(GPU) 선택 → 엔드포인트 이름 지정 → `InService` 대기
5. [ ] `config.py`에 엔드포인트 이름/리전 입력, `LLM_BACKEND="sagemaker"`
6. [ ] 서버에 boto3 + AWS 권한 설정 → 테스트
7. [ ] **안 쓸 때 엔드포인트 삭제 (비용!)** + 비용 알림 설정
