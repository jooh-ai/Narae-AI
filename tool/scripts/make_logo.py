"""로고 자산 생성 — 원본 PNG 의 단색 배경을 투명으로 바꿔 data/logo.png 를 만든다.

브랜드 자산이 갱신되면 새 원본으로 다시 돌리면 된다. 배경이 단색(흰/회색)인
PNG 를 전제로, 경계의 안티에일리어싱까지 알파로 되살린다.

    python scripts/make_logo.py <원본.png> [--height 120]

data/logo.png (UI 헤더용, 배경 투명) 과 data/logo.ico (exe 아이콘, 다중 해상도)
두 개를 만든다.

왜 알파를 되살리는가
  단순히 '배경색과 같은 픽셀만 투명' 처리하면 경계에 밝은 테두리가 남는다.
  관측색 = 배경×(1-a) + 원색×a 이므로, a 를 추정해 원색을 역산한다. 이 마크는
  빨강(#C8102E)·주황(#E8821E) 뿐이고 둘 다 청색 성분이 낮아(46/30) 청색 채널
  하나로 a 를 안정적으로 뽑을 수 있다.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6 import QtCore, QtGui  # noqa: E402

DST = Path(__file__).resolve().parents[1] / "wirye_capacity" / "data" / "logo.png"
ICO = Path(__file__).resolve().parents[1] / "wirye_capacity" / "data" / "logo.ico"
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)   # Windows 아이콘 표준 크기
REF_BLUE = 38.0      # 마크 두 색의 청색 성분 (46 / 30) 대표값
SOLID = 0.96         # 이 이상은 완전 불투명으로 스냅 (반올림 잡음 제거)
PAD = 2              # 잘라낸 뒤 남길 여백 px


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("src", help="원본 PNG (배경이 단색이어야 한다)")
    ap.add_argument("--height", type=int, default=120,
                    help="출력 높이 px (UI 는 30px 로 쓰므로 HiDPI 여유분 포함)")
    ap.add_argument("--out", default=str(DST))
    ap.add_argument("--ico", default=str(ICO),
                    help="exe 아이콘(.ico) 도 함께 생성 — wirye_tool.spec 의 icon=")
    a = ap.parse_args()

    img = QtGui.QImage(a.src)
    if img.isNull():
        raise SystemExit(f"이미지를 읽을 수 없습니다: {a.src}")
    img = img.convertToFormat(QtGui.QImage.Format_ARGB32)
    w, h = img.width(), img.height()

    # 배경색 = 네 꼭짓점 평균
    corners = [img.pixelColor(x, y) for x, y in
               ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1))]
    bg = [sum(c.red() for c in corners) / 4,
          sum(c.green() for c in corners) / 4,
          sum(c.blue() for c in corners) / 4]
    span = bg[2] - REF_BLUE
    print(f"원본 {w}x{h}  배경 rgb({bg[0]:.0f},{bg[1]:.0f},{bg[2]:.0f})")
    if span < 60:
        raise SystemExit("배경이 마크 색과 너무 가까워 알파를 추정할 수 없습니다")

    out = QtGui.QImage(w, h, QtGui.QImage.Format_ARGB32)
    out.fill(QtCore.Qt.transparent)
    x0, y0, x1, y1 = w, h, -1, -1
    for y in range(h):
        for x in range(w):
            c = img.pixelColor(x, y)
            alpha = (bg[2] - c.blue()) / span
            if alpha <= 0.02:
                continue
            alpha = 1.0 if alpha >= SOLID else min(alpha, 1.0)
            if alpha >= 1.0:
                r, g, b = c.red(), c.green(), c.blue()
            else:   # 관측색에서 배경 기여분을 빼 원색을 역산
                r, g, b = (min(255, max(0, round((v - bgv * (1 - alpha)) / alpha)))
                           for v, bgv in zip((c.red(), c.green(), c.blue()), bg))
            out.setPixelColor(x, y, QtGui.QColor(r, g, b, round(alpha * 255)))
            x0, y0, x1, y1 = min(x0, x), min(y0, y), max(x1, x), max(y1, y)

    if x1 < 0:
        raise SystemExit("마크를 찾지 못했습니다 (전부 배경)")
    rect = QtCore.QRect(max(0, x0 - PAD), max(0, y0 - PAD),
                        min(w, x1 + PAD + 1) - max(0, x0 - PAD),
                        min(h, y1 + PAD + 1) - max(0, y0 - PAD))
    crop = out.copy(rect)
    final = crop.scaledToHeight(a.height, QtCore.Qt.SmoothTransformation)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    if not final.save(a.out, "PNG"):
        raise SystemExit(f"저장 실패: {a.out}")
    print(f"잘라냄 {rect.width()}x{rect.height()} → 저장 {final.width()}x{final.height()}  {a.out}")

    if a.ico:
        write_ico(crop, Path(a.ico))
        print(f"exe 아이콘 저장 {ICO_SIZES} → {a.ico}")


def write_ico(src: QtGui.QImage, dst: Path) -> None:
    """다중 해상도 .ico 생성. Qt 의 ico 라이터는 한 장만 쓰므로 컨테이너를 직접 만든다.

    Vista 이후 ICO 는 항목을 PNG 로 담을 수 있어(압축·알파 그대로) 이 방식이 가장
    단순하다. 마크가 정사각형이 아니므로 정사각 캔버스에 가운데 정렬한다 —
    늘려 맞추면 찌그러진다.
    """
    blobs = []
    for n in ICO_SIZES:
        fit = src.scaled(n, n, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        sq = QtGui.QImage(n, n, QtGui.QImage.Format_ARGB32)
        sq.fill(QtCore.Qt.transparent)
        q = QtGui.QPainter(sq)
        q.drawImage((n - fit.width()) // 2, (n - fit.height()) // 2, fit)
        q.end()
        buf = QtCore.QBuffer()
        buf.open(QtCore.QIODevice.WriteOnly)
        if not sq.save(buf, "PNG"):
            raise SystemExit(f"{n}px PNG 인코딩 실패")
        blobs.append((n, bytes(buf.data())))

    head = b"\x00\x00\x01\x00" + len(blobs).to_bytes(2, "little")
    offset = len(head) + 16 * len(blobs)
    entries, body = b"", b""
    for n, blob in blobs:
        d = 0 if n >= 256 else n          # ICO 는 256 을 0 으로 적는다
        entries += (bytes([d, d, 0, 0]) + (1).to_bytes(2, "little")
                    + (32).to_bytes(2, "little") + len(blob).to_bytes(4, "little")
                    + offset.to_bytes(4, "little"))
        body += blob
        offset += len(blob)
    dst.write_bytes(head + entries + body)


if __name__ == "__main__":
    main()
