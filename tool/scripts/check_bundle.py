"""빌드 결과 검증 — exe 폴더의 번들 데이터가 온전한지 확인.

    python scripts/check_bundle.py [dist/WiryeBidTool]

번들 xlsx 템플릿이 손상되면 실행 시점에야 오류가 나므로, 빌드 직후 여기서 잡는다.
"""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

TARGETS = [
    ("wirye_capacity/templates/excel3_profile_template.xlsx", "xlsx"),
    ("wirye_capacity/data/measurements_seed.json", "json"),
    ("wirye_capacity/data/base_table.json", "json"),
]


def check(root: Path) -> int:
    bases = [root / "_internal", root]          # PyInstaller 6.x / 5.x 구조 모두 지원
    bad = 0
    print(f"검증 대상 폴더: {root}")
    for rel, kind in TARGETS:
        found = next((b / rel for b in bases if (b / rel).exists()), None)
        if found is None:
            print(f"  ❌ 없음      {rel}")
            bad += 1
            continue
        size = found.stat().st_size
        ok = True
        note = ""
        if size == 0:
            ok, note = False, "0바이트"
        elif kind == "xlsx":
            if not zipfile.is_zipfile(found):
                ok, note = False, "zip(xlsx) 구조가 아님 — 손상"
            else:
                with zipfile.ZipFile(found) as z:
                    if "xl/workbook.xml" not in z.namelist():
                        ok, note = False, "workbook.xml 없음 — 손상"
        elif kind == "json":
            try:
                json.loads(found.read_text(encoding="utf-8"))
            except Exception as e:              # noqa: BLE001
                ok, note = False, f"JSON 파싱 실패: {e}"
        mark = "✅" if ok else "❌"
        print(f"  {mark} {size:>9,}바이트  {rel}" + (f"   ← {note}" if note else ""))
        if not ok:
            bad += 1
    print()
    if bad:
        print(f"손상/누락 {bad}건 — 재빌드가 필요합니다:")
        print("  pyinstaller --noconfirm wirye_tool.spec")
        return 1
    print("번들 데이터 정상 — 실행 가능합니다.")
    return 0


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("dist/WiryeBidTool")
    if not target.exists():
        print(f"폴더가 없습니다: {target}\n먼저 빌드하세요: pyinstaller --noconfirm wirye_tool.spec")
        raise SystemExit(2)
    raise SystemExit(check(target))
