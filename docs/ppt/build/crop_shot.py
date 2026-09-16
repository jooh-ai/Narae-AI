#!/usr/bin/env python3
"""캡처에서 필요한 열만 잘라 나란히 붙인다 — 장표에서 읽히게 만드는 용도.

    python3 docs/ppt/build/crop_shot.py <원본> <출력> --rects "x,y,w,h;x,y,w,h" \
        [--labels "일자|차이|적용값"] [--scale 2] [--gap 10]

엑셀 실적 시트는 열이 20개가 넘어서 통째로 넣으면 장표에서 글자가 안 읽힌다.
그렇다고 숫자를 우리가 다시 타이핑하면 그건 실물 캡처가 아니다. 그래서
**원본에서 필요한 열만 오려 나란히 붙인다** — 픽셀은 원본 그대로이고 바뀌는 것은
열 사이의 거리뿐이다. 장표에는 "같은 시트에서 세 열만 뽑았습니다" 라고 밝힌다.

Chromium 으로 그린다(이 환경에 이미지 라이브러리가 없다). 각 조각을 배경
이미지의 음수 위치로 밀어 넣은 div 로 만들어 가로로 잇는다.
"""
from __future__ import annotations

import argparse
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CHROME = Path("/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell")


def png_size(p: Path) -> tuple[int, int]:
    d = p.open("rb").read(32)
    if d[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit(f"PNG 가 아닙니다: {p}")
    return struct.unpack(">II", d[16:24])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--rects", required=True, help='"x,y,w,h;x,y,w,h" (원본 픽셀)')
    ap.add_argument("--labels", default="", help='조각 위에 얹을 라벨, "|" 구분')
    ap.add_argument("--scale", type=float, default=2.0, help="출력 배율 (기본 2)")
    ap.add_argument("--gap", type=int, default=10, help="조각 사이 간격 px")
    a = ap.parse_args()

    src = Path(a.src).resolve()
    rects = [tuple(int(v) for v in r.split(",")) for r in a.rects.split(";") if r.strip()]
    labels = a.labels.split("|") if a.labels else []
    iw, ih = png_size(src)

    lab_h = 22 if labels else 0
    h = max(r[3] for r in rects) + lab_h
    w = sum(r[2] for r in rects) + a.gap * (len(rects) - 1)

    cells = []
    for i, (x, y, cw, ch) in enumerate(rects):
        lb = (f"<div class=lb>{labels[i]}</div>" if i < len(labels) else
              ("<div class=lb></div>" if labels else ""))
        cells.append(
            f"<div class=col style='width:{cw}px'>{lb}"
            f"<div class=clip style='width:{cw}px;height:{ch}px'>"
            f"<img src='file://{src}' style='position:absolute;left:{-x}px;top:{-y}px;"
            f"width:{iw}px;height:{ih}px;max-width:none'></div></div>")

    html = f"""<!doctype html><meta charset=utf-8><style>
 *{{box-sizing:border-box}} body{{margin:0;background:#fff;display:flex;gap:{a.gap}px}}
 .col{{display:flex;flex-direction:column}}
 .lb{{height:{lab_h}px;line-height:{lab_h}px;font-family:'NanumGothic',sans-serif;
      font-size:12px;font-weight:700;color:#217346;text-align:center;
      border-bottom:1px solid #D8D8D8}}
 .clip{{position:relative;overflow:hidden}}
</style>{''.join(cells)}"""

    out = Path(a.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".html")
    tmp.write_text(html, encoding="utf-8")
    subprocess.run([str(CHROME), "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                    f"--force-device-scale-factor={a.scale}", f"--screenshot={out}",
                    f"--window-size={w},{h}", f"file://{tmp}"],
                   check=True, capture_output=True)
    tmp.unlink()
    ow, oh = png_size(out)
    rel = out.relative_to(ROOT) if out.is_relative_to(ROOT) else out
    print(f"{rel}  {ow}x{oh}  ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
