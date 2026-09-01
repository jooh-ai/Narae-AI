/* v2-10 · 개선 효과 — 요소 2개: 감소율 3수치 / 시운전 회차별 막대.
   정량·정성 두 장을 한 장으로 합치고 정성 효과는 결론 한 줄로 남겼다.    */
'use strict';
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  const { d } = T.shell(pptx, { sec: '효과', idx: 6, step: 6 });
  const I = D.impact, K = I.cut, S = D.commission;
  T.title(d, '같은 방식으로 채점했더니,', '세 지표가 *동시에* 좋아졌습니다');
  T.lead(d, '종전 방식과 현재 도구를 같은 ' + D.n + '회차에 나란히 채점한 결과입니다.',
         { lines: 1 });

  /* 감소율 3수치 */
  [[72,  '예측 오차',      K.mae,   '`' + I.blanket.mae.toFixed(2) + '` → `' + I.gp.mae.toFixed(2) + '` MW'],
   [467, '기준 미달 회차', K.short, '`' + I.blanket.short + '` → `' + I.gp.short + '` 건'],
   [862, '과대 신고 누계', K.over,  '`' + I.blanket.over.toFixed(1) + '` → `' + I.gp.over.toFixed(1) + '` MW']]
    .forEach(([x, l, pct, sub]) => {
      d.panel(x, 284, 346, 'on');
      d.plab(l, x, 298, 346);
      d.bigUnit(pct + '%', '감소', x, 320, 58, C.brass, 17);
      d.txt(sub, x, 396, 346, 1);
    });

  /* 시운전 — 예측을 먼저 남기고 실측과 대조 */
  d.zone(G.L, 452, G.W, 172);
  d.plab('시운전 ' + S.n + '회차  ·  세로 = 실측 − 예측 MW  ·  아래쪽은 예측이 컸던 회차',
         96, 466, 680);
  d.text('편차 ' + (S.me >= 0 ? '+' : '−') + Math.abs(S.me).toFixed(3) +
         '  ·  오차 ' + S.mae.toFixed(3) + '  ·  개선율 +' + Math.round(S.skill * 100) + '%',
         { x: 790, y: 464, w: 394, px: 12.5, lh: 1.3, mono: true, bold: true,
           color: C.brass, align: 'right' });

  const ZERO = 536, PXMW = 20, BW = 46;
  d.hline(140, ZERO, 1000, C.rule, 1);
  [2, -2].forEach(v => d.hline(140, ZERO - v * PXMW, 1000, C.rule2, 1));
  [[2, '+2'], [0, '0'], [-2, '−2']].forEach(([v, s]) => d.text(s,
    { x: 96, y: ZERO - v * PXMW - 7, w: 36, px: 10, lh: 1.3, mono: true,
      color: C.dim2, align: 'right' }));
  S.rows.forEach((r, i) => {
    const x = 158 + i * 110, h = Math.abs(r.diff) * PXMW, up = r.diff >= 0;
    d.rect(x, up ? ZERO - h : ZERO, BW, Math.max(h, 2), up ? C.brass : C.red);
    d.text((r.diff >= 0 ? '+' : '−') + Math.abs(r.diff).toFixed(2),
           { x: x - 14, y: up ? ZERO - h - 17 : ZERO + h + 3, w: BW + 28, px: 10.5, lh: 1.2,
             mono: true, bold: true, color: up ? C.brass : C.red, align: 'center' });
    d.text(r.date.slice(5), { x: x - 14, y: 604, w: BW + 28, px: 10, lh: 1.2,
                              mono: true, color: C.dim2, align: 'center' });
  });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '숫자만 좋아진 게 아닙니다 — *왜 그 숫자인지 설명*할 수 있게 됐습니다.');
};
