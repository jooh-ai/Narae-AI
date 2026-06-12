"""웹 서버 실행 스크립트 (9단계).

사용:
    python -m scripts.serve              # 0.0.0.0:8000 으로 실행
    python -m scripts.serve --port 9000

서버 1대에서 실행하면, 같은 내부망의 직원들이 브라우저로 접속해 사용한다.
"""
from __future__ import annotations

import argparse

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="사내 규정 챗봇 웹 서버")
    parser.add_argument("--host", default="0.0.0.0", help="바인딩 주소(기본: 모든 인터페이스)")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    print(f"웹 서버 시작: http://{args.host}:{args.port}  (Ctrl+C로 종료)")
    uvicorn.run("src.web.app:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
