/* v2-01 · 표지 — 요소 2개: 제목 블록 / 히어로 차트. 하단에 핵심 3수치.
   18장판보다 설명을 걷어내고 숫자를 키웠다.                              */
'use strict';
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  const { d } = T.shell(pptx, {});
  d.text(meta.org, { x: G.L, y: G.SEC_Y, w: 600, px: 12, lh: 1.25, mono: true, color: C.dim2, cs: 1.8 });
  d.text(meta.when, { x: 1008, y: G.SEC_Y, w: 200, px: 12, lh: 1.25, mono: true,
                      color: C.dim2, cs: 1.8, align: 'right' });

  T.title(d, '공급가능용량 산정,', '사람의 판단에서 *데이터로*', { y: 112, w: 590, px: 44 });
  d.sub('보정값 ~하나~ 로 맞춰 온 신고를 *온도별 학습*으로', G.L, 268, 590, 1);
  d.sub('바꿨습니다.', G.L, 302, 590, 1);

  /* 히어로 — 종전 수평선 vs 개선 곡선 */
  const ZX = 668, OX = ZX + 16, OY = 148;
  d.zone(ZX, 112, 540, 318);
  d.plab('보정값 · MW · 외기온도 0 ~ 30℃', OX, 126, 480);
  const T4 = D.curve_t, RBF = D.curves.rbf, FLAT = D.blanket.flat;
  const CX = t => 48 + t * 14.2, CY = v => 128 - v * 13;
  const X = v => OX + v, Y = v => OY + v;
  const sign = v => (v >= 0 ? '+' : '−') + Math.abs(v).toFixed(1);
  const lab = (s, x, w, base, px, col, al) => d.text(s, { x, y: Y(base) - px * 0.8, w, px,
    lh: 1.3, mono: true, color: col, align: al || 'left' });
  [24, 128, 180].forEach((y, i) => d.hline(X(40), Y(y), 450, i === 1 ? C.rule : C.rule2, 1));
  d.vline(X(40), Y(24), 156, C.rule, 1);
  [[8, '+8'], [0, '0'], [-4, '−4']].forEach(([v, s]) => lab(s, X(0), 34, CY(v) + 4, 10, C.dim2));
  T4.forEach(t => { d.vline(X(CX(t)), Y(180), 5, C.dim2, 1);
    lab(t === 0 ? '0℃' : String(t), X(CX(t)) - 24, 48, 200, 10, C.dim2, 'center'); });
  d.hline(X(40), Y(CY(FLAT)), 450, C.slateL, 2.6, 'dash');
  lab('종전 · 하나의 값 ' + sign(FLAT), X(48), 220, CY(FLAT) - 10, 12, C.slateL);
  const P = T4.map((t, i) => [CX(t), CY(RBF[i])]);
  for (let i = 0; i < P.length - 1; i++)
    d.seg(X(P[i][0]), Y(P[i][1]), X(P[i + 1][0]), Y(P[i + 1][1]), C.brass, 2.8);
  P.forEach(([a, b]) => d.rect(X(a) - 4, Y(b) - 4, 8, 8, C.brass));
  lab(sign(RBF[0]), X(58), 60, CY(RBF[0]) + 21, 12.5, C.brass);
  lab(sign(RBF[3]), X(398), 66, CY(RBF[3]) + 15, 12.5, C.brass, 'right');
  d.text('겨울엔 ' + (RBF[0] - FLAT).toFixed(1) + ' MW 모자라고, 여름엔 ' +
         (FLAT - RBF[3]).toFixed(1) + ' MW 넘칩니다',
         { x: OX, y: 392, w: 500, px: 13.5, lh: 1.4, color: C.red });

  /* 핵심 3수치 — 크게 */
  d.hline(G.L, 480, G.W, C.rule, 1);
  const I = D.impact, K = I.cut;
  [[72, '예측 오차', K.mae, I.blanket.mae.toFixed(2) + ' → ' + I.gp.mae.toFixed(2) + ' MW'],
   [420, '기준 미달 회차', K.short, I.blanket.short + ' → ' + I.gp.short + ' 건'],
   [768, '과대 신고 누계', K.over, I.blanket.over.toFixed(1) + ' → ' + I.gp.over.toFixed(1) + ' MW']]
    .forEach(([x, l, pct, sub]) => {
      d.plab(l, x, 502, 300);
      d.big(pct + '%↓', x, 526, 220, 54);
      d.text(sub, { x, y: 596, w: 300, px: 16, lh: 1.4, mono: true, color: C.ink });
    });
  [396, 744].forEach(x => d.vline(x, 502, 116, C.rule, 1));

  d.hline(G.L, 634, G.W, C.rule, 1);
  d.text(meta.dept + '  ·  ' + meta.authors.join(' · '),
         { x: G.L, y: G.FOOT_Y, w: 600, px: 12, lh: 1.4, mono: true, color: C.dim, cs: 1.6 });
  d.text('발표 10분  ·  Tool 시연 4분', { x: 808, y: G.FOOT_Y, w: 400, px: 12, lh: 1.4,
                                          mono: true, color: C.dim2, cs: 1.6, align: 'right' });
};
