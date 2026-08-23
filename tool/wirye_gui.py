"""GUI 실행 진입점 (PyInstaller 패키징용).

패키지 상대 import(from .. import ...)가 있는 ui/app.py 를 직접 스크립트로 돌리면
import 가 깨지므로, 절대 import 로 감싸는 얇은 런처를 별도로 둔다.

    python wirye_gui.py            # 소스 실행
    pyinstaller wirye_tool.spec    # exe 빌드(이 파일이 진입점)
"""
from wirye_capacity.ui.app import main

if __name__ == "__main__":
    raise SystemExit(main())
