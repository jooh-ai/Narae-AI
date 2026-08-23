"""번들 씨앗(measurements_seed.json) 정정 — 새로 설치하는 PC 가 올바른 32건으로 시작하도록.

왜 필요한가
  씨앗은 DB 가 비었을 때 자동 적재된다. 그런데 지금 씨앗에는 2026-08 대조에서
  찾아낸 오류가 그대로 남아 있어, 새 PC 에서 exe 를 처음 띄우면 오류가 부활한다:
    · 잘못된 기록 2건 (CIT 25.70/CC 411.51, CIT 6.90/CC 460.70)
    · MBL 습도계 드리프트값 5건 (0.1 · 9.7 · 36.8 · 9.1 · 0.0 %)
    · 날짜 없음 → 시계열 검증·재취득 대조 불가

무엇을 고치는가 (근거가 확정된 것만)
  1) 날짜 부여 — 담당자 실적표(2026-07-29 수령) 기준
  2) 잘못된 기록 1건 교체 — 실적표와 히스토리안이 일치하는 값으로
        2026-01-08  CIT -1.45 / 대기압 1017.0 / RH  5.8 / CC 472.49
  3) 습도 5건 — MBL → CXM(10CXM00CM001). 실적표와 소수 둘째자리까지 일치 확인분
  4) 2025-04-15 제외 — 2025 상반기는 설비 수준이 다른 시기다 (EXCLUDE 주석 참조).
     결과 31건이 된다. 실적표 32행과 1건 차이나는 이유가 이것이다.

무엇을 고치지 않는가 (일부러)
  · 나머지 25건의 theory 는 그대로 둔다. 엔진 재계산값과 최대 0.19MW 다르지만
    (엑셀4 I열 값 유래) 이건 이번 조사와 무관한 기존 차이고, 여기서 손대면
    담당자 실적표·사용자 DB 와 씨앗이 어긋난다.
  · 진공(cp_meas/cp_design)·계절·W 는 유지. 교체 2건만 새로 산정한다.
    cp_design 은 어떤 계산에도 쓰이지 않는(시뮬레이션 참고 표시용) 값이라
    인접 기록에서 선형보간한다.

실행:
    python scripts/rebuild_seed.py            # 미리보기(파일 변경 없음)
    python scripts/rebuild_seed.py --write    # 실제로 씨앗 파일 갱신
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wirye_capacity import constants as C  # noqa: E402
from wirye_capacity.correction import correction_value  # noqa: E402
from wirye_capacity.store import _SEED  # noqa: E402
from wirye_capacity.theory import TheoryEngine, igv_turnup  # noqa: E402

# 담당자 실적표 — (일자, CIT, 대기압, RH, 진공도, CC Gross). CC 로 씨앗과 매칭한다.
E4 = [
    ("2025-04-15", 13.7,  995.8, 35.4, 48.0, 438.1),
    ("2025-07-09", 36.1,  998.5, 39.7, 78.1, 376.6),
    ("2025-07-22", 32.8, 1003.7, 49.6, 75.7, 390.8),
    ("2025-07-29", 34.6,  989.4, 52.8, 82.1, 376.4),
    ("2025-08-05", 32.8,  994.0, 47.0, 74.1, 386.4),
    ("2025-08-12", 33.6, 1000.2, 36.0, 70.9, 386.2),
    ("2025-08-19", 32.7, 1000.4, 49.3, 76.2, 385.2),
    ("2025-08-21", 33.8,  999.8, 38.0, 74.9, 381.7),
    ("2025-08-27", 30.2, 1000.9, 49.1, 69.7, 395.5),
    ("2025-09-02", 30.7, 1000.0, 50.0, 71.2, 391.6),
    ("2025-09-09", 27.4, 1003.4, 51.8, 66.1, 404.4),
    ("2025-09-18", 25.3, 1006.3, 49.9, 62.2, 411.6),
    ("2025-09-23", 25.1, 1007.7, 44.0, 59.4, 414.5),
    ("2025-10-14", 21.3, 1009.1, 62.8, 59.8, 427.7),
    ("2025-10-21", 14.5, 1018.4, 49.1, 49.9, 450.5),
    ("2025-10-28", 12.7, 1018.3, 24.0, 43.1, 452.4),
    ("2025-11-04", 14.4, 1015.4, 33.2, 46.2, 450.8),
    ("2025-11-11", 13.3, 1013.4, 33.4, 46.3, 451.1),
    ("2025-11-20", 13.0, 1011.8, 29.9, 46.6, 451.4),
    ("2025-11-26",  8.9, 1014.6, 32.5, 42.5, 457.7),
    ("2025-12-02",  1.9, 1015.1,  8.2, 35.0, 466.9),
    ("2026-01-06",  3.9, 1011.2, 23.0, 47.9, 460.9),
    ("2026-01-08", -1.5, 1017.0,  5.8, 32.6, 472.5),
    ("2026-01-13", -1.9, 1010.7, 13.9, 42.4, 468.8),
    ("2026-02-04",  7.0, 1010.8, 38.5, 41.1, 457.3),
    ("2026-02-12",  8.0, 1011.3, 33.6, 46.6, 455.7),
    ("2026-02-24",  6.0, 1014.6, 17.2, 46.0, 459.7),
    ("2026-02-25", 15.1, 1011.6, 18.2, 48.9, 445.6),
    ("2026-03-04", 11.2, 1013.0, 35.4, 45.1, 453.1),
    ("2026-03-18",  9.5, 1003.6, 67.6, 44.1, 450.2),
    ("2026-03-24", 16.6, 1006.5, 41.2, 47.6, 440.6),
    ("2026-04-02", 16.7, 1004.4, 27.6, 47.7, 439.7),
]

# 학습에서 제외하는 날짜 — 씨앗에 넣지 않는다.
#
# 2025-04-15 는 "2025 상반기"라는 다른 성능 수준의 시기에 속한 시험이다.
# 근거는 담당자 Base Load 실적표(2025-03-12~2025-07-09, 16건)와의 대조다.
# 재현: python scripts/period_check.py   (원자료·계산 모두 그 스크립트에 있다)
#
#   · W(IGV)=+4 가 양쪽 전부 동일한 CIT 7~19°C 에서 두 시기가 완전히 분리된다
#         하반기 이후 13건  평균 +5.602  (범위 +3.657 ~ +7.442)
#         2025 상반기 5건  평균 +1.515  (범위 +0.545 ~ +2.893)
#         차이 -4.09 MW, Welch t = -8.03, 겹치는 값 0건
#   · 상반기 16건 전체의 GP 곡선 대비 잔차 -2.356 MW (t = -4.59)
#         3~4월(5월 CI 前) -3.165 / 5~7월초(CI 後) -1.546 → 회복 흔적은 있으나 미완
#   · 04-15 는 자기 시기 5건 중 위에서 두 번째다. 이상치가 아니라 그 시기의 전형이다
#   · 대기압 995.8 이 원인이 아니다 — 같은 시기 정상 대기압(1003~1013) 4건이 더 낮다
#   · 넣으면 10~15°C 구간평균이 -0.62 MW 내려가고 GP LOOCV MAE 가 1.3287 → 1.4696
#
# 즉 시기가 다른 수준을 곡선에 섞는 문제다. 상반기 16건을 다 넣으면 입찰 실무
# 온도대(10~25°C)가 1.2~2.4 MW 깎이는데, 현재 설비 상태를 대표하지 않는 값이므로
# 순수 기회손실이다. 저온대 -4 MW 계단이 어디서 생겼는지(2025년 5월 CI 일자,
# 7~9월 추가 정비 여부) 확정되면 "그 시점 이후만 사용"을 명시적 규칙으로 둔다.
EXCLUDE = {
    "2025-04-15": "2025 상반기(설비 수준이 다른 시기) 시험 — period_check.py 참조",
}

# 교체 1건 — 히스토리안 값(실적표와 일치 확인분). 씨앗의 어느 기록을 밀어내는지도 적는다.
REPLACE = {
    "2026-01-08": {"cit": -1.45, "press": 1017.03, "rh": 5.79, "cc_meas": 472.49,
                   "cp_meas": 32.6, "season": "극저온△", "drops_cc": 460.70,
                   "why": "씨앗 기록(CIT 6.90/CC 460.70)이 실적표·히스토리안과 불일치"},
}
# 습도 정정 5건 — MBL → CXM
RH_FIX = {"2026-02-25": 18.2, "2026-03-04": 35.4, "2026-03-18": 67.6,
          "2026-03-24": 41.2, "2026-04-02": 27.6}


def interp_cp_design(seed, cit):
    """인접 기록에서 설계 진공도를 선형보간. 어떤 계산에도 쓰이지 않는 표시용 값이다."""
    pts = sorted((r["cit"], r["cp_design"]) for r in seed if r.get("cp_design") is not None)
    if not pts:
        return None
    if cit <= pts[0][0]:
        return pts[0][1]
    if cit >= pts[-1][0]:
        return pts[-1][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= cit <= x1:
            t = 0.0 if x1 == x0 else (cit - x0) / (x1 - x0)
            return round(y0 + (y1 - y0) * t, 1)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="씨앗 파일을 실제로 갱신")
    ap.add_argument("--deg", type=float, default=C.DEFAULT_DEG)
    a = ap.parse_args()

    seed = json.loads(Path(_SEED).read_text(encoding="utf-8"))
    eng = TheoryEngine()
    print(f"씨앗 {_SEED}\n현재 {len(seed)}건 / 실적표 {len(E4)}행\n")

    # CC Gross 로 매칭 (가장 변별력 높은 열)
    used, out, log = set(), [], []
    for date, cit, press, rh, vac, ccg in E4:
        if date in REPLACE:
            continue                                   # 교체 건은 아래에서 새로 만든다
        if date in EXCLUDE:
            log.append(f"  [제외] {date}  {EXCLUDE[date]}")
            continue
        best, bd = None, 9e9
        for i, s in enumerate(seed):
            if i in used:
                continue
            d = abs(s["cc_meas"] - ccg)
            if d < bd:
                best, bd = i, d
        if bd > 0.15:
            print(f"  ! {date} CC {ccg} 에 대응하는 씨앗 기록을 못 찾음 (최소차 {bd:.2f})")
            continue
        used.add(best)
        r = dict(seed[best])
        r["date"] = date
        if date in RH_FIX:                             # 습도 정정 → 이론·보정 재계산
            old_rh, old_th, old_cr = r["rh"], r["theory"], r["corr"]
            r["rh"] = RH_FIX[date]
            r["theory"] = round(eng.theory_cc(r["cit"], r["press"], a.deg, rh=r["rh"]), 3)
            r["corr"] = round(correction_value(r["cc_meas"], r["theory"], r["w"]), 3)
            log.append(f"  [습도] {date}  RH {old_rh} → {r['rh']} (CXM)   "
                       f"이론 {old_th} → {r['theory']}   보정 {old_cr:+.3f} → {r['corr']:+.3f}")
        out.append(r)

    dropped = [seed[i] for i in range(len(seed)) if i not in used]
    for date, spec in REPLACE.items():
        w = igv_turnup(spec["cit"])
        th = round(eng.theory_cc(spec["cit"], spec["press"], a.deg, rh=spec["rh"]), 3)
        r = {"cit": spec["cit"], "press": spec["press"], "rh": spec["rh"],
             "cp_meas": spec["cp_meas"], "cp_design": interp_cp_design(seed, spec["cit"]),
             "cc_meas": spec["cc_meas"], "w": float(w), "theory": th,
             "corr": round(correction_value(spec["cc_meas"], th, w), 3),
             "season": spec["season"], "date": date}
        old = next((x for x in dropped if abs(x["cc_meas"] - spec["drops_cc"]) < 0.01), None)
        log.append(f"  [교체] {date}  {spec['why']}")
        if old:
            log.append(f"         버림  CIT {old['cit']:>6.2f} / CC {old['cc_meas']:>7.2f} / "
                       f"RH {old['rh']} / 보정 {old['corr']:+.3f}")
        log.append(f"         신규  CIT {r['cit']:>6.2f} / CC {r['cc_meas']:>7.2f} / "
                   f"RH {r['rh']} / W {r['w']:+.0f} / 이론 {r['theory']} / 보정 {r['corr']:+.3f}")
        out.append(r)

    # 정렬은 기존 파일과 같이 CIT 오름차순으로 둔다. mock 커넥터가 JSON 순서를
    # 합성 날짜(2025-T01…)에 매핑하므로 순서를 바꾸면 테스트·재현성이 흔들린다.
    out.sort(key=lambda x: x["cit"])
    print("변경 내역")
    print("\n".join(log))
    kept_out = {s["drops_cc"] for s in REPLACE.values()}
    left = [x for x in dropped if not any(abs(x["cc_meas"] - c) < 0.01 for c in kept_out)]
    if left:
        print(f"\n  ! 실적표에 대응이 없어 빠진 기록 {len(left)}건 — 확인 필요:")
        for x in left:
            print(f"      CIT {x['cit']} / CC {x['cc_meas']} / 보정 {x['corr']:+.3f}")

    print(f"\n결과 {len(out)}건 (날짜 있는 기록 {sum(1 for r in out if r.get('date'))}건)")
    if len(out) != len(seed):
        print(f"  ! 건수가 {len(seed)} → {len(out)} 로 바뀝니다. 의도한 것인지 확인하세요.")
    if not a.write:
        print("\n미리보기입니다. 실제로 갱신하려면 --write 를 붙이세요.")
        return 0

    bak = Path(str(_SEED) + ".bak")
    bak.write_text(Path(_SEED).read_text(encoding="utf-8"), encoding="utf-8")
    Path(_SEED).write_text(
        json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"\n갱신 완료. 이전 파일은 {bak.name} 로 백업했습니다.")
    print("  ※ 이미 DB 가 있는 PC 는 영향 없습니다(씨앗은 DB 가 비었을 때만 적재).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
