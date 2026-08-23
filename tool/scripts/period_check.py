"""시기별 성능 수준 대조 — 2025 상반기 Base Load 실적 vs 누적 DB.

왜 필요한가
  누적 DB(31건)는 전부 2025-07-22 이후다. 그래서 "2025-04-15 를 넣어야 하나"를
  DB 내부만 보고는 판단할 수 없었다. 담당자 Base Load 실적표(2025-03-12~
  2025-07-09, 16건)를 받아 같은 정의로 보정값을 산출해 두 시기를 비교한 것이
  이 스크립트다. rebuild_seed.EXCLUDE 의 근거이므로 원자료를 함께 보관한다.

결론
  2025 상반기는 하반기 이후보다 보정값이 낮은 별개 시기다. 04-15 는 그 시기의
  이상치가 아니라 전형이며(자기 시기 5건 중 위에서 두 번째), 낮은 원인은
  대기압 995.8 이 아니다(같은 시기 정상 대기압 4건이 더 낮다).

W(IGV) 규약 — 이게 성립해야 아래 계산이 유효하다
  Base Load 실적표의 CC(Gross) 는 IGV 반영값이다. 근거 둘:
    1) 담당자 공급가능용량 실적표의 04-15 행이 CC 438.10 / 이론 432.31 /
       보정 +1.788 → 438.10 - 432.31 - 4.00 = 1.79. 담당자도 W=+4 를 뺐다.
    2) 07/09 행에만 'HCO, IGV X' 주석이 있고 그 행의 369.9 는 우리 DB 의
       376.56 보다 정확히 6.66 MW 낮다(≈ IGV +6). 예외 표기가 필요했다는 것이
       나머지 행은 IGV 포함이라는 뜻이다.
  실적표의 'BLT 적용값' 열(+6~-1)은 W(IGV) 와 다른 값이다 — 04-15 는 BLT +5 인데
  담당자는 W +4 를 썼다. 입찰 적용 마진으로 보이나 확인 전이므로 쓰지 않는다.

실행:
    python scripts/period_check.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wirye_capacity import constants as C  # noqa: E402
from wirye_capacity.gp import GPCorrectionCurve  # noqa: E402
from wirye_capacity.store import _SEED  # noqa: E402
from wirye_capacity.theory import TheoryEngine, igv_turnup  # noqa: E402

# 담당자 Base Load 실적표 (2026-08 수령분) — 표에 적힌 값 그대로.
#   날짜, CIT(°C), 대기압(mbar), 상대습도(%), CC Gross(MW), 진공도(mbar), BLT 적용값
# 07-09 는 'HCO, IGV X' 행이라 CC 가 IGV 미반영값이다(위 규약 주석 참조).
H1_2025 = [
    ("2025-03-12", 12.5, 1005.6, 54.2, 443.7, 50.3, 4),
    ("2025-03-19", 7.3, 1013.4, 19.4, 455.3, 42.6, 5),
    ("2025-03-26", 25.7, 991.7, 9.2, 406.8, 50.3, 5),
    ("2025-04-03", 16.0, 1008.3, 29.8, 438.7, 49.7, 5),
    ("2025-04-08", 18.8, 1003.3, 27.3, 429.7, 50.1, 5),
    ("2025-04-15", 13.7, 995.8, 35.4, 438.1, 48.0, 5),
    ("2025-04-23", 23.5, 995.5, 36.4, 411.1, 60.5, 1),
    ("2025-04-29", 21.4, 1002.0, 11.9, 421.5, 51.6, 3),
    ("2025-05-19", 20.0, 996.8, 42.2, 426.3, 49.7, 6),   # 실적표 '25년 5월 CI' 라벨
    ("2025-05-27", 27.4, 1006.0, 30.1, 408.3, 57.9, 6),
    ("2025-06-04", 25.5, 993.5, 28.1, 408.4, 57.4, 5),
    ("2025-06-11", 28.9, 1000.9, 29.3, 400.0, 63.2, 5),
    ("2025-06-17", 29.9, 994.9, 43.6, 391.2, 67.8, 2),
    ("2025-06-24", 27.6, 997.3, 47.9, 399.2, 63.9, 2),
    ("2025-07-02", 31.9, 1001.8, 56.8, 385.3, 76.3, 1),
    ("2025-07-09", 36.6, 998.5, 35.7, 369.9, 77.0, -1),  # HCO, IGV X
]

CI_DATE = "2025-05"          # 실적표에 적힌 '25년 5월 CI' — 전/후 구분 기준
BAND = (7.0, 19.0)           # W(IGV)=+4 가 양쪽 전부 동일한 구간


def _mean_sd(xs: list[float]) -> tuple[float, float]:
    n = len(xs)
    mu = sum(xs) / n
    sd = (sum((x - mu) ** 2 for x in xs) / (n - 1)) ** 0.5 if n > 1 else float("nan")
    return mu, sd


def _report(label: str, res: list[float]) -> None:
    n = len(res)
    mu, sd = _mean_sd(res)
    se = sd / n ** 0.5 if n > 1 else float("nan")
    t = mu / se if se == se and se > 0 else float("nan")
    print(f"{label:36s} n={n:2d}  평균잔차 {mu:+7.3f}  sd {sd:5.3f}  t={t:+6.2f}")


def main() -> None:
    eng = TheoryEngine()
    seed = json.loads(_SEED.read_text(encoding="utf-8"))
    recs = seed["records"] if isinstance(seed, dict) else seed

    def row(date, cit, press, rh, cc, w):
        th = eng.theory_cc(cit, press, C.DEFAULT_DEG, rh=rh)
        return {"date": date, "cit": cit, "press": press, "rh": rh, "cc": cc,
                "w": w, "theory": th, "corr": cc - th - w}

    # 누적 DB — 저장된 theory 가 아니라 엔진으로 재계산해 상반기와 조건을 맞춘다.
    db = [row(r["date"], r["cit"], r["press"], r["rh"], r["cc_meas"], r.get("w") or 0.0)
          for r in recs]
    h1 = [row(d, cit, p, rh, cc, igv_turnup(cit)) for d, cit, p, rh, cc, _v, _b in H1_2025]

    print(f"누적 DB {len(db)}건 (전부 2025-07-22 이후) / 2025 상반기 {len(h1)}건\n")

    # ── 1) W 가 동일한 구간에서 직접 비교 ────────────────────────────────
    lo, hi = BAND
    a = sorted((r for r in db if lo <= r["cit"] <= hi), key=lambda r: r["cit"])
    b = sorted((r for r in h1 if lo <= r["cit"] <= hi), key=lambda r: r["cit"])
    assert all(r["w"] == 4.0 for r in a + b), "W(IGV) 가 +4 로 통일되지 않음 — BAND 재확인"

    print(f"── CIT {lo:.0f}~{hi:.0f}°C, W(IGV)=+4 동일 조건 직접 비교 ──")
    print(f"{'[하반기 이후 = 누적 DB]':40s} [2025 상반기]")
    for i in range(max(len(a), len(b))):
        def fmt(rows, i):
            if i >= len(rows):
                return ""
            r = rows[i]
            return f"{r['date']} CIT {r['cit']:5.2f} P{r['press']:6.1f} corr {r['corr']:+6.3f}"
        print(f"{fmt(a, i):48s} {fmt(b, i)}")

    ma, sa = _mean_sd([r["corr"] for r in a])
    mb, sb = _mean_sd([r["corr"] for r in b])
    se = (sa * sa / len(a) + sb * sb / len(b)) ** 0.5
    print(f"\n하반기 이후 n={len(a):2d}  평균 {ma:+.3f}  sd {sa:.3f}  "
          f"범위 {min(r['corr'] for r in a):+.3f} ~ {max(r['corr'] for r in a):+.3f}")
    print(f"2025 상반기 n={len(b):2d}  평균 {mb:+.3f}  sd {sb:.3f}  "
          f"범위 {min(r['corr'] for r in b):+.3f} ~ {max(r['corr'] for r in b):+.3f}")
    print(f"차이 {mb - ma:+.3f} MW   Welch t = {(mb - ma) / se:+.2f}")
    overlap = [r["date"] for r in b if r["corr"] >= min(x["corr"] for x in a)]
    print(f"겹치는 상반기 기록 : {len(overlap)}건 {overlap}")

    # ── 2) 04-15 저압 가설 ───────────────────────────────────────────────
    print("\n── 04-15 저압 가설 (같은 시기 안에서) ──")
    for r in sorted(b, key=lambda x: x["press"]):
        mark = "  ← 이 시기 유일한 저압" if r["press"] < 1000 else ""
        print(f"   {r['date']}  P {r['press']:6.1f}  corr {r['corr']:+6.3f}{mark}")

    # ── 3) GP 곡선 대비 잔차 ─────────────────────────────────────────────
    gp = GPCorrectionCurve([{"cit": r["cit"], "corr": r["corr"]} for r in db])
    print(f"\n── 누적 DB GP 곡선(ls,sf,sn={gp.hyper}, 적합 {gp.tmin:.2f}~{gp.tmax:.2f}°C) "
          f"대비 잔차 ──")
    for r in h1:
        r["res"] = r["corr"] - gp._post(r["cit"])[0]
    _report("누적 DB (기준, 자기적합)",
            [r["corr"] - gp._post(r["cit"])[0] for r in db])
    _report("2025 상반기 전체", [r["res"] for r in h1])
    _report(f"  ~{CI_DATE} 이전 (5월 CI 前)", [r["res"] for r in h1 if r["date"] < CI_DATE])
    _report(f"  {CI_DATE} 이후 (CI 後)", [r["res"] for r in h1 if r["date"] >= CI_DATE])

    # ── 4) 상반기를 넣으면 구간평균이 어떻게 되나 ────────────────────────
    print("\n── 상반기 16건을 전부 넣는다면 (구간평균 영향) ──")
    for blo, bhi in ((0, 5), (5, 10), (10, 15), (15, 20), (20, 25), (25, 30), (30, 35), (35, 41)):
        cur = [r["corr"] for r in db if blo <= r["cit"] < bhi]
        add = cur + [r["corr"] for r in h1 if blo <= r["cit"] < bhi]
        if not cur:
            continue
        mo, mn = sum(cur) / len(cur), sum(add) / len(add)
        print(f"   {blo:3d}~{bhi:3d}°C   현재 {mo:+7.3f} (n={len(cur):2d})  →  "
              f"추가 후 {mn:+7.3f} (n={len(add):2d})   {mn - mo:+.3f} MW")


if __name__ == "__main__":
    main()
