#!/usr/bin/env python3
"""종전 엑셀 화면 캡처 — 발표자료 '전(前)' 사진을 만든다.

    python3 docs/ppt/build/excel_shot.py

엑셀3 「온도 Profile」 템플릿(`tool/wirye_capacity/templates/`)을 실제 엑셀 화면처럼
그려 PNG 로 저장한다. 이 환경에는 엑셀도 LibreOffice 렌더도 없으므로,
openpyxl 로 셀을 읽어 HTML 로 그린 뒤 headless Chromium 으로 찍는다.

**만들어 내는 그림이 아니다.** 값·수식·서식·시트 이름 모두 담당자가 쓰던 원본
파일에서 그대로 읽는다. 바꾸는 것은 두 가지뿐이다.

  · 서버 경로의 IP 와 사번을 가린다 (`--mask`). 남의 바탕화면 경로가 장표에
    그대로 나가면 지적하는 자리처럼 보인다.
  · 61행을 다 실으면 글자가 뭉개져서, 위/아래를 잘라 '⋮' 로 잇는다(`--fold`).

산출물 (docs/ppt/assets/)
    xl_profile.png    값 보기 — 담당자가 실제로 보던 화면
    xl_formula.png    수식 보기 — 이 표 한 장이 다른 시트를 참조하는 모습
    xl_links.png      외부 링크 — 2019년 파일을 아직 참조하고 있다 (--links 일 때만)
"""
from __future__ import annotations

import argparse
import html
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import openpyxl
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "tool" / "wirye_capacity" / "templates" / "excel3_profile_template.xlsx"
OUT = ROOT / "docs" / "ppt" / "assets"
CHROME = Path("/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell")

# 엑셀 화면 색 — 캡처가 '진짜 엑셀' 로 읽혀야 한다
XL = dict(head="#F2F2F2", headline="#D0D7DE", grid="#D8D8D8", text="#1A1A1A",
          sel="#217346", body="#FFFFFF", tab="#F3F3F3")


def fmt(v, nf: str) -> str:
    """엑셀 표시 형식을 흉내낸다 — 화면에 보이던 대로 찍어야 '그 화면' 이 된다."""
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    if isinstance(v, (int, float)):
        if "%" in nf:
            return f"{v * 100:.0f}%"
        if "#,##0.0" in nf:
            return f"{v:,.1f}"
        if "#,##0" in nf or nf.startswith("_("):
            return f"{v:,.0f}"
        if isinstance(v, float):
            return f"{v:,.2f}".rstrip("0").rstrip(".")
        return f"{v:,}"
    return str(v)


def cell_css(c) -> str:
    s = []
    f = c.font
    if f is not None:
        if f.b:
            s.append("font-weight:700")
        if f.sz and float(f.sz) >= 13:
            s.append(f"font-size:{min(float(f.sz), 15) * 1.05:.0f}px")
        rgb = getattr(f.color, "rgb", None) if f.color else None
        if isinstance(rgb, str) and len(rgb) == 8 and rgb[2:] not in ("000000", "FFFFFF"):
            s.append(f"color:#{rgb[2:]}")
    fill = c.fill
    rgb = getattr(fill.fgColor, "rgb", None) if (fill and fill.fgColor) else None
    if isinstance(rgb, str) and len(rgb) == 8 and rgb[2:] not in ("000000", "FFFFFF"):
        s.append(f"background:#{rgb[2:]}")
    al = (c.alignment.horizontal if c.alignment else None)
    if al in ("center", "right", "left"):
        s.append(f"text-align:{al}")
    return ";".join(s)


def sheet_html(ws, r0, r1, c0, c1, *, formulas=False, fold=None, title="") -> str:
    """시트 한 구획을 엑셀 화면처럼. fold=(잘라낼 시작행, 끝행) 이면 그 구간을 ⋮ 한 줄로."""
    merged = {}
    skip = set()
    for rng in ws.merged_cells.ranges:
        if rng.min_row > r1 or rng.max_row < r0 or rng.min_col > c1 or rng.max_col < c0:
            continue
        merged[(rng.min_row, rng.min_col)] = (rng.max_row - rng.min_row + 1,
                                              rng.max_col - rng.min_col + 1)
        for rr in range(rng.min_row, rng.max_row + 1):
            for cc in range(rng.min_col, rng.max_col + 1):
                if (rr, cc) != (rng.min_row, rng.min_col):
                    skip.add((rr, cc))

    rows = []
    hd = "".join(f"<th class=ch>{get_column_letter(c)}</th>" for c in range(c0, c1 + 1))
    rows.append(f"<tr><th class='ch rn'></th>{hd}</tr>")

    r = r0
    while r <= r1:
        if fold and fold[0] <= r <= fold[1]:
            if r == fold[0]:
                rows.append(f"<tr><td class=rn>⋮</td>"
                            f"<td class='fold' colspan={c1 - c0 + 1}>⋮　　"
                            f"({fold[1] - fold[0] + 1}행 생략)　　⋮</td></tr>")
            r += 1
            continue
        tds = []
        for c in range(c0, c1 + 1):
            if (r, c) in skip:
                continue
            cell = ws.cell(r, c)
            span = merged.get((r, c))
            v = cell.value
            if formulas and isinstance(v, str) and v.startswith("="):
                txt = v
                cls = " fx"
            else:
                txt = fmt(v, cell.number_format or "General")
                cls = ""
            att = ""
            if span:
                if span[0] > 1:
                    att += f" rowspan={span[0]}"
                if span[1] > 1:
                    att += f" colspan={span[1]}"
            st = cell_css(cell)
            tds.append(f"<td class='c{cls}'{att} style='{st}'>{html.escape(str(txt))}</td>")
        rows.append(f"<tr><td class=rn>{r}</td>{''.join(tds)}</tr>")
        r += 1

    tabs = "".join(
        f"<span class='tab{' on' if s.title == ws.title else ''}'>{html.escape(s.title)}</span>"
        for s in ws.parent.worksheets)
    return f"""<!doctype html><meta charset=utf-8><style>
 *{{box-sizing:border-box}}
 body{{margin:0;background:{XL['body']};font-family:'NanumGothic','Malgun Gothic',sans-serif;
      color:{XL['text']};font-size:12.5px}}
 .bar{{background:{XL['sel']};color:#fff;padding:7px 12px;font-size:13px;font-weight:700}}
 .fbar{{border-bottom:1px solid {XL['headline']};padding:5px 10px;font-size:12px;color:#444;
        background:#FAFAFA}}
 .fbar b{{display:inline-block;min-width:52px;color:#666;font-weight:400}}
 table{{border-collapse:collapse;table-layout:fixed}}
 th.ch{{background:{XL['head']};border:1px solid {XL['headline']};font-weight:400;
        font-size:11px;color:#444;height:20px;min-width:74px}}
 th.ch.rn,td.rn{{min-width:34px;width:34px;background:{XL['head']};
        border:1px solid {XL['headline']};font-size:11px;color:#444;text-align:center}}
 td.c{{border:1px solid {XL['grid']};height:20px;padding:1px 5px;white-space:nowrap;
       overflow:hidden;text-align:center}}
 td.fx{{font-family:'NanumGothicCoding',monospace;font-size:11.5px;color:#1155CC;
        text-align:left}}
 td.fold{{border:1px solid {XL['grid']};height:22px;text-align:center;color:#999;
          background:#FCFCFC;letter-spacing:2px}}
 .tabs{{padding:6px 10px;background:{XL['tab']};border-top:1px solid {XL['headline']}}}
 .tab{{display:inline-block;padding:4px 12px;margin-right:3px;font-size:11.5px;color:#555;
       border:1px solid transparent}}
 .tab.on{{background:#fff;border:1px solid {XL['headline']};border-bottom-color:#fff;
          font-weight:700;color:{XL['sel']}}}
</style>
<div class=bar>{html.escape(title or SRC.name)}</div>
<div class=fbar><b>{get_column_letter(c0)}{r0}</b> {html.escape(str(ws.cell(r0, c0).value or ''))[:90]}</div>
<table>{''.join(rows)}</table>
<div class=tabs>{tabs}</div>"""


def links_html(mask: bool) -> str:
    z = zipfile.ZipFile(SRC)
    out = []
    for n in ("xl/externalLinks/_rels/externalLink1.xml.rels",
              "xl/externalLinks/_rels/externalLink2.xml.rels"):
        for m in re.finditer(r'Target="([^"]+)"', z.read(n).decode("utf-8")):
            t = m.group(1).replace("file:///", "").replace("%20", " ")
            if mask:
                t = re.sub(r"\d+\.\d+\.\d+\.\d+", "***.*.**.*", t)
                t = re.sub(r"Users\\[^\\]+", r"Users\\****", t)
            out.append(t)
    items = "".join(f"<div class=row><span class=ic>🔗</span>{html.escape(t)}</div>" for t in out)
    return f"""<!doctype html><meta charset=utf-8><style>
 body{{margin:0;background:#fff;font-family:'NanumGothic',sans-serif;color:#1A1A1A;font-size:13px}}
 .bar{{background:{XL['sel']};color:#fff;padding:7px 12px;font-weight:700;font-size:13px}}
 .hd{{padding:10px 14px 6px;font-size:12.5px;color:#555;border-bottom:1px solid #E4E4E4}}
 .row{{padding:9px 14px;border-bottom:1px solid #EFEFEF;
       font-family:'NanumGothicCoding',monospace;font-size:11.5px;color:#333;word-break:break-all}}
 .ic{{margin-right:8px}}
</style>
<div class=bar>연결 편집 — 이 통합 문서가 참조하는 다른 파일</div>
<div class=hd>원본: {SRC.name}</div>{items}"""


def shot(html_text: str, png: Path, w: int, h: int) -> None:
    tmp = png.with_suffix(".html")
    tmp.write_text(html_text, encoding="utf-8")
    subprocess.run([str(CHROME), "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                    "--force-device-scale-factor=2", f"--screenshot={png}",
                    f"--window-size={w},{h}", f"file://{tmp}"],
                   check=True, capture_output=True)
    tmp.unlink()
    print(f"  {png.name:18s} {png.stat().st_size // 1024:5d} KB   {w}x{h}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-mask", action="store_true", help="서버 IP·사번을 가리지 않는다")
    ap.add_argument("--links", action="store_true",
                    help="외부 링크 캡처도 만든다 (기본은 만들지 않는다 — 위 주석 참조)")
    a = ap.parse_args()
    if not CHROME.exists():
        sys.exit(f"headless Chromium 이 없습니다: {CHROME}")
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"원본  {SRC.relative_to(ROOT)}")

    wb = openpyxl.load_workbook(SRC, data_only=True)     # 값 보기
    ws = wb["온도 Profile"]
    shot(sheet_html(ws, 2, 66, 2, 14, fold=(20, 60),
                    title="엑셀 ③ 온도 프로파일  —  [온도 Profile] 시트"),
         OUT / "xl_profile.png", 1080, 640)

    wbf = openpyxl.load_workbook(SRC, data_only=False)   # 수식 보기
    wsf = wbf["온도 Profile"]
    shot(sheet_html(wsf, 4, 24, 2, 10, formulas=True,
                    title="엑셀 ③ 수식 보기 (Ctrl + `)  —  [온도 Profile] 시트"),
         OUT / "xl_formula.png", 900, 560)

    if a.links:
        # 2019년 경로에 서버 IP 와 남의 사번이 그대로 남아 있다. 장표에 넣으면
        # 지적하는 자리처럼 보여서 쓰지 않기로 했다(2026-09-14). 필요하면 --links.
        shot(links_html(not a.no_mask), OUT / "xl_links.png", 900, 220)


if __name__ == "__main__":
    main()
