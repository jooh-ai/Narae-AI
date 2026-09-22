/* 슬라이드 1 · 표지
   히어로 그래프 = 이 과제의 결론. 종전은 온도와 무관한 수평 점선 하나,
   개선은 온도에 따라 내려가는 곡선. 두 선의 간격이 곧 손실이다.

   축 규격 (목업 design_v2.html 과 동일)
     x  0℃ = 48 · 30℃ = 474  (14.2 px/℃)
     y  13 px/MW · 0 MW = y128
   실측 GP·RBF 4점 (0,+7.50)(10,+5.17)(20,+3.47)(30,−2.38) → y = 31,61,83,159
   종전 일괄 baseline = 36건 평균 +2.84 → y = 128 − 2.84×13 = 91
     (계획서 §6 의 '≈+2.4' 는 실제 적용 BLT 값이고, 오차 3.833 MAE 와
      대응하는 비교 기준은 최소제곱 최적 상수 = 평균 +2.84 다.)                */
'use strict';
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  const { d } = T.shell(pptx, {});

  /* 상단 메타 */
  d.text(meta.org, { x: G.L, y: G.SEC_Y, w: 600, px: 12, lh: 1.25, mono: true, color: C.dim2, cs: 1.8 });
  d.text(meta.when, { x: 1008, y: G.SEC_Y, w: 200, px: 12, lh: 1.25, mono: true, color: C.dim2, cs: 1.8, align: 'right' });

  /* 제목 · 주장 · 본문 */
  T.title(d, '공급가능용량 산정,', '사람의 판단에서 *데이터로*', { y: 112, w: 590, px: 44 });
  d.sub('온도가 달라도 ~보정값 하나~로 맞춰 온 신고를, *온도별로 학습하는 모델*로 바꿨습니다.',
        G.L, 280, 568, 2);
  d.txt('종전 방식과 _같은 데이터 · 같은 조건_ 에서 채점한 결과입니다. 누적 ' + D.n +
        '회차, 한 건씩 가려 맞혀봤습니다.', G.L, 392, 552, 2);

  /* ── 히어로 그래프 ─────────────────────────────────────────────── */
  const ZX = 668, ZY = 112, ZW = 540, ZH = 316;
  d.zone(ZX, ZY, ZW, ZH);
  d.plab('보정값 · 단위 MW  ·  외기온도 0 ~ 30℃', ZX + 16, ZY + 14, 480);

  const OX = ZX + 16, OY = 151;                 // 차트 원점 (목업 SVG 0,0)
  const X = v => OX + v, Y = v => OY + v;
  const lab = (str, x, w, baseline, px, color, align, mono) =>
    d.text(str, { x, y: Y(baseline) - px * 0.8, w, px, lh: 1.3,
                  color, align: align || 'left', mono: mono !== false, bold: false });

  /* 격자 · 축 */
  d.hline(X(40), Y(24), 450, C.rule2, 1);
  d.hline(X(40), Y(128), 450, C.rule, 1);
  d.hline(X(40), Y(180), 450, C.rule2, 1);
  d.vline(X(40), Y(24), 156, C.rule, 1);
  lab('+8', X(0), 34, 28, 10, C.dim2);
  lab('0', X(0), 34, 132, 10, C.dim2);
  lab('−4', X(0), 34, 184, 10, C.dim2);
  [[48, '0℃'], [190, '10'], [332, '20'], [474, '30']].forEach(([lx, s]) => {
    d.vline(X(lx), Y(180), 5, C.dim2, 1);
    lab(s, X(lx) - 24, 48, 200, 10, C.dim2, 'center');
  });

  /* 차트 좌표 변환 — 데이터 값 → 차트 로컬 px */
  const T4 = D.curve_t, RBF = D.curves.rbf, FLAT = D.blanket.flat;
  const CX = t => 48 + t * 14.2, CY = v => 128 - v * 13;
  const sign = v => (v >= 0 ? '+' : '−') + Math.abs(v).toFixed(1);

  /* 종전 — 하나의 값 */
  d.hline(X(40), Y(CY(FLAT)), 450, C.slateL, 2.6, 'dash');
  lab('종전 · 하나의 값 ' + (FLAT >= 0 ? '+' : '−') + Math.abs(FLAT).toFixed(2),
      X(48), 220, CY(FLAT) - 10, 12, C.slateL, 'left', false);

  /* 개선 — GP·RBF 실측 4점 */
  const P = T4.map((t, i) => [CX(t), CY(RBF[i])]);
  for (let i = 0; i < P.length - 1; i++)
    d.seg(X(P[i][0]), Y(P[i][1]), X(P[i + 1][0]), Y(P[i + 1][1]), C.brass, 2.6);
  P.forEach(([px_, py]) => d.rect(X(px_) - 4, Y(py) - 4, 8, 8, C.brass));
  lab(sign(RBF[0]), X(58), 60, CY(RBF[0]) + 21, 12, C.brass);
  lab(sign(RBF[3]), X(400), 66, CY(RBF[3]) + 15, 12, C.brass, 'right');

  /* 두 선의 간격 = 손실. 양 끝 온도 그 자리에 정확히 */
  const wy1 = CY(RBF[0]) + 6, wy2 = CY(FLAT) - 6;
  const sy1 = CY(FLAT) + 6, sy2 = CY(RBF[3]) - 6;
  d.vline(X(CX(T4[0])), Y(wy1), wy2 - wy1, C.red, 1.6);
  d.hline(X(CX(T4[0]) - 6), Y(wy1), 12, C.red, 1.6);
  d.hline(X(CX(T4[0]) - 6), Y(wy2), 12, C.red, 1.6);
  d.vline(X(CX(T4[3])), Y(sy1), sy2 - sy1, C.red, 1.6);
  d.hline(X(CX(T4[3]) - 6), Y(sy1), 12, C.red, 1.6);
  d.hline(X(CX(T4[3]) - 6), Y(sy2), 12, C.red, 1.6);

  /* 범례 — 문자가 아니라 실제 선 스와치로 */
  d.hline(OX, 381, 26, C.slateL, 2.6, 'dash');
  d.text('종전 · 하나의 값 ' + (FLAT >= 0 ? '+' : '−') + Math.abs(FLAT).toFixed(2),
         { x: OX + 34, y: 373, w: 200, px: 12, lh: 1.4, mono: true, color: C.slateL });
  d.hline(OX + 250, 381, 26, C.brass, 2.6);
  d.text('개선 · 온도별 곡선', { x: OX + 284, y: 373, w: 200, px: 12, lh: 1.4, mono: true, color: C.brass });
  d.text('겨울 ' + T4[0] + '℃ ' + (RBF[0] - FLAT).toFixed(1) + ' MW 과소   ·   여름 ' +
         T4[3] + '℃ ' + (FLAT - RBF[3]).toFixed(1) + ' MW 과대',
         { x: OX, y: 397, w: 480, px: 12, lh: 1.4, mono: true, color: C.red });

  d.sub('점선 하나를 *곡선*으로 바꾼 것이 전부입니다.', ZX, 452, ZW, 1);

  /* ── 핵심 3수치 ────────────────────────────────────────────────── */
  d.hline(G.L, 506, G.W, C.rule, 1);
  const I = D.impact, K = I.cut;
  const KPI = [
    [72,  '예측 오차',      K.mae + '%↓',   I.blanket.mae.toFixed(2) + ' → ' + I.gp.mae.toFixed(2) + ' MW'],
    [306, '기준 미달 회차', K.short + '%↓', I.blanket.short + ' → ' + I.gp.short + ' 건'],
    [540, '과대 신고 누계', K.over + '%↓',  I.blanket.over.toFixed(1) + ' → ' + I.gp.over.toFixed(1) + ' MW'],
  ];
  KPI.forEach(([x, l, n, sub]) => {
    d.plab(l, x, 516, 208);
    d.big(n, x, 540, 208, 48);
    d.text(sub, { x, y: 601, w: 208, px: 15, lh: 1.4, mono: true, color: C.ink });
  });
  [280, 514, 748].forEach(x => d.vline(x, 516, 106, C.rule, 1));
  d.plab('무엇이 달라졌나', 774, 516, 434);
  d.txt('_사람이 정하던 보정값 1개_ 가 사라졌습니다. 이제 온도별 실적이 값을 만들고, 회차가 쌓이면 스스로 다시 고릅니다.',
        774, 540, 434, 3);

  /* ── 하단 ─────────────────────────────────────────────────────── */
  d.hline(G.L, 634, G.W, C.rule, 1);
  d.text(meta.dept + '  ·  ' + meta.authors.join(' · '),
         { x: G.L, y: G.FOOT_Y, w: 600, px: 12, lh: 1.4, mono: true, color: C.dim, cs: 1.6 });
  d.text('발표 10분  ·  Tool 시연 4분',
         { x: 808, y: G.FOOT_Y, w: 400, px: 12, lh: 1.4, mono: true, color: C.dim2, cs: 1.6, align: 'right' });
};
