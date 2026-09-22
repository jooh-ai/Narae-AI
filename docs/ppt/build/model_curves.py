#!/usr/bin/env python3
"""회귀 모델 설명 장(부록)이 쓸 곡선 — 실제 실적으로 뽑는다.

    python3 docs/ppt/build/model_curves.py --tool-root <체크아웃>/tool

손으로 그린 예시 곡선을 쓰지 않는다. 같은 시험 실적 40회에 방법만 바꿔
그리면, 장표의 그림이 곧 우리 데이터의 사실이 된다. 값은 전부 도구 코드
(`select.predict` · `gp.GPCorrectionCurve`)를 그대로 불러 얻는다.

내보내는 것 (docs/ppt/build/model_curves.json)
    t         −4 ~ 40℃, 1℃ 간격
    scatter   시험 40회의 (외기온도, 실제−계산)
    rbf       GP · RBF (제곱지수)        — 우리가 쓰는 곡선
    exp       GP · 지수 (Matérn 1/2)     — 각지는 곡선
    curve     커널회귀                   — GP 가 아닌 다른 방법
    band      GP · RBF 의 90% 예측구간 (lo/hi)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "model_curves.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tool-root", default="", help="도구 체크아웃의 tool 폴더")
    a = ap.parse_args()
    tool = Path(a.tool_root).resolve() if a.tool_root else (ROOT / "tool")
    sys.path.insert(0, str(tool))
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from wirye_capacity import constants as C, gp as G, select as S

    recs = json.loads(Path(C.resource("data", "measurements_seed.json"))
                      .read_text(encoding="utf-8"))
    recs = [r for r in recs if r.get("cit") is not None and r.get("corr") is not None]

    ts = list(range(-4, 41))
    out = {
        "_출처": "tool/wirye_capacity/data/measurements_seed.json · 도구 코드로 계산",
        "_방법": "select.predict(method, 전체 실적, t) 를 1℃ 간격으로 부른다. "
                 "band 는 gp.GPCorrectionCurve.interval(t) (90%, z=1.645).",
        "n": len(recs),
        "t": ts,
        "scatter": [[r["cit"], round(r["corr"], 3)] for r in recs],
    }
    for key, method in (("rbf", "gp:rbf"), ("exp", "gp:exp"), ("curve", "curve")):
        out[key] = [(None if (v := S.predict(method, recs, t)) is None else round(v, 3))
                    for t in ts]

    g = G.GPCorrectionCurve(recs)
    lo, hi = [], []
    for t in ts:
        a_, b_ = g.interval(t)
        same = abs(b_ - a_) < 1e-9          # 특수구간 — 구간이 없다
        lo.append(None if same else round(a_, 3))
        hi.append(None if same else round(b_, 3))
    out["band"] = {"lo": lo, "hi": hi}

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    ok = sum(1 for v in out["rbf"] if v is not None)
    print(f"완료  {OUT.name}  실적 {out['n']}회 · 격자 {len(ts)}점 · 예측 {ok}점")
    for k in ("rbf", "exp", "curve"):
        vs = [v for v in out[k] if v is not None]
        print(f"  {k:6s} {min(vs):+.2f} ~ {max(vs):+.2f}")
    bw = [h - l for l, h in zip(out["band"]["lo"], out["band"]["hi"])
          if l is not None]
    print(f"  band   폭 {min(bw):.2f} ~ {max(bw):.2f} MW")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
