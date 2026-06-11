"""LLM 클라이언트 (6단계) — 교체 가능 구조.

모든 백엔드는 generate(prompt, system) -> str 인터페이스를 따른다.
config.LLM_BACKEND 한 줄로 전환:

- "stub"      : 모델 없이 파이프라인을 검증하기 위한 더미. (외부망 개발 기본값)
                실제 추론은 하지 않고, 검색된 근거를 그대로 보여주도록 자리표시 답변을 낸다.
- "ollama"    : 로컬에 띄운 Ollama 서버 호출. (개발 PC에서 실모델 테스트)
- "sagemaker" : 내부망 SageMaker 엔드포인트 호출. (운영)

stub으로 전체 흐름(검색→프롬프트→답변→출처)을 완성해 두고,
내부망에서는 백엔드만 sagemaker로 바꾸면 동일 코드가 동작한다.
"""
from __future__ import annotations


class StubLLM:
    """실제 모델 없이 동작하는 자리표시 LLM (외부망 개발용).

    추론을 못 하므로, 답변 자리에 '실모델 미연결' 안내를 낸다.
    핵심 가치인 '검색된 근거(출처)'는 RAG 체인이 별도로 항상 보여주므로,
    이 상태로도 검색 품질과 전체 흐름을 검증할 수 있다.
    """

    name = "stub"

    def generate(self, prompt: str, system: str | None = None) -> str:
        return (
            "[STUB LLM] 실제 언어모델이 연결되지 않은 개발 모드입니다.\n"
            "검색은 정상 동작하므로 아래 '참고 조항'에서 답을 확인하세요.\n"
            "내부망에서 config.LLM_BACKEND를 'sagemaker'로 바꾸면 실제 답변이 생성됩니다."
        )


class OllamaLLM:
    """로컬 Ollama 서버 호출 (개발 PC용). 'ollama serve'가 떠 있어야 한다."""

    name = "ollama"

    def __init__(self, host: str, model: str) -> None:
        self.host = host.rstrip("/")
        self.model = model

    def generate(self, prompt: str, system: str | None = None) -> str:
        import requests

        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system or "",
            "stream": False,
        }
        resp = requests.post(f"{self.host}/api/generate", json=payload, timeout=120)
        resp.raise_for_status()
        return resp.json().get("response", "").strip()


class SageMakerLLM:
    """내부망 SageMaker 엔드포인트 호출 (운영용).

    외부망에서는 boto3/엔드포인트가 없어 동작하지 않는다(의도된 것).
    내부망 반입 후 boto3 설치 + 엔드포인트명 지정 시 동작한다.
    """

    name = "sagemaker"

    def __init__(self, endpoint_name: str, region: str | None = None) -> None:
        self.endpoint_name = endpoint_name
        self.region = region

    def generate(self, prompt: str, system: str | None = None) -> str:
        import json

        import boto3  # 내부망에서 설치 필요

        client = boto3.client("sagemaker-runtime", region_name=self.region)
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        body = {"inputs": full_prompt, "parameters": {"max_new_tokens": 512, "temperature": 0.2}}
        resp = client.invoke_endpoint(
            EndpointName=self.endpoint_name,
            ContentType="application/json",
            Body=json.dumps(body),
        )
        result = json.loads(resp["Body"].read())
        # 모델 컨테이너에 따라 응답 형식이 다를 수 있어 방어적으로 파싱
        if isinstance(result, list) and result:
            return str(result[0].get("generated_text", result[0])).strip()
        if isinstance(result, dict):
            return str(result.get("generated_text") or result.get("outputs") or result).strip()
        return str(result).strip()


def get_llm():
    """config.LLM_BACKEND에 맞는 LLM 클라이언트를 생성한다."""
    import config

    backend = config.LLM_BACKEND
    if backend == "stub":
        return StubLLM()
    if backend == "ollama":
        return OllamaLLM(config.OLLAMA_HOST, config.OLLAMA_MODEL)
    if backend == "sagemaker":
        endpoint = getattr(config, "SAGEMAKER_ENDPOINT", "")
        region = getattr(config, "AWS_REGION", None)
        if not endpoint:
            raise ValueError("config.SAGEMAKER_ENDPOINT를 설정하세요.")
        return SageMakerLLM(endpoint, region)
    raise ValueError(f"알 수 없는 LLM_BACKEND: {backend}")


if __name__ == "__main__":
    llm = get_llm()
    print(f"백엔드: {llm.name}")
    print(llm.generate("연차휴가는 며칠인가요?"))
