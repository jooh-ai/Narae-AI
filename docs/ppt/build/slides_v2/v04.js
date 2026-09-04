/* v2-04 · 개요 및 추진 배경 — 요소 2개: 종전 업무 플로우 / 손실 그래프.
   [검토 반영] '왜 일괄 보정을 했나' 가 빠져 있었다. 그 이유를 모르면 종전
   방식이 그냥 대충 한 것처럼 들리는데, 사실은 그때로서는 합리적인 선택이었다.

   핵심 — 테스트는 그날의 온도 **한 점**에서만 한다. 그런데 신고는 −20~40℃
   61개 온도 전부에 해야 한다. 나머지 60개 온도의 차이는 알 방법이 없으니
   한 점에서 잰 차이를 그대로 얹는 것이 가장 안전했다. 이 과제가 한 일은
   테스트를 쌓아 '온도별로 알 수 있게' 만든 것이다.
   출처: docs/concept.txt §1 (엑셀1→2→비교→일괄→엑셀3 절차).                */
'use strict';
const FLOW = [
  ['테스트 1회',    '엑셀 ① 날짜·시각 → RiMS', false],
  ['온도별 계산',   '엑셀 ② 대기압 → 61개 값', false],
  ['차이 1개',      '그날 온도에서 실측 − 계산', false],
  ['61개에 똑같이', '엑셀 ④ 일괄 보정', true],
  ['프로파일 완성', '엑셀 ③ 붙여넣기 → 신고', false],
];
module.exports = (pptx, T, meta, D) => {
  const { C, G, LW } = T;
  const { d } = T.shell(pptx, { sec: '왜 하는가', idx: 1, step: 1 });
  const P = D.profile, R = P.rows, FLAT = D.blanket.flat, B = D.impact.blanket;
  T.title(d, '테스트는 한 점,', '신고는 *61개 온도 전부*');
  T.lead(d, '그 빈 구간을 메우려고, 한 점에서 구한 보정값 하나를 61개 온도에 똑같이 ' +
         '적용한 것이 _일괄 보정_ 입니다.', { lines: 1 });

  /* ① 종전 업무 플로우 */
  d.zone(G.L, 268, G.W, 114);
  d.plab('종전 절차  ·  엑셀 4개를 순서대로', 96, 278, 500, C.slate);
  FLOW.forEach(([k, v, on], i) => {
    const x = 96 + i * 216;
    d.box(x, 298, 196, 44, C.ground, on ? '6B5220' : C.rule, on ? 1.4 : 1);
    d.text(k, { x: x + 12, y: 304, w: 172, px: 13.5, lh: 1.2, bold: true,
                color: on ? C.brass : C.ink });
    d.text(v, { x: x + 12, y: 323, w: 172, px: 10, lh: 1.2, color: C.dim2 });
    if (i < 4) d.text('→', { x: x + 196, y: 312, w: 20, px: 14, lh: 1.2,
                             color: C.dim2, align: 'center' });
  });
  d.text('테스트는 *그날의 온도 한 점*에서만 합니다. 나머지 60개 온도의 차이는 알 수 없으니, ' +
         '같은 값을 얹는 것이 _그때로서는 가장 안전한_ 선택이었습니다.',
         { x: 96, y: 352, w: 1088, px: 12.5, lh: 1.4, color: C.dim });

  /* ② 그래서 어떤 손실이 났나 */
  d.zone(G.L, 394, G.W, 230);
  d.plab('외기온도별 출력  ·  단위 MW  ·  종전 신고(이론값 + ' + FLAT.toFixed(1) +
         ' 하나로) vs 실제 능력', 96, 404, 700);

  const t0 = R[0].t, t1 = R[R.length - 1].t;
  const bid = r => r.theory + FLAT;
  const vs = R.map(bid).concat(R.map(r => r.real));
  const lo = Math.floor(Math.min(...vs) / 20) * 20 - 5;
  const hi = Math.ceil(Math.max(...vs) / 20) * 20 + 5;
  const X = t => 150 + (t - t0) * (1000 / (t1 - t0));
  const Y = v => 572 - (v - lo) * (142 / (hi - lo));
  for (let v = lo + 5; v <= hi; v += 20) {
    d.hline(150, Y(v), 1000, C.rule2, 1);
    d.text(String(v), { x: 96, y: Y(v) - 7, w: 46, px: 10, lh: 1.3, mono: true,
                        color: C.dim2, align: 'right' });
  }
  d.hline(150, 572, 1000, C.rule, 1);
  for (let t = t0; t <= t1; t += 10) {
    d.vline(X(t), 572, 5, C.dim2, 1);
    d.text(t === t0 ? t + '℃' : String(t), { x: X(t) - 24, y: 578, w: 48, px: 10, lh: 1.3,
                                             mono: true, color: C.dim2, align: 'center' });
  }

  /* 두 곡선 사이를 채운다 — 부호가 바뀌는 곳에서 색이 갈린다 */
  const step = X(R[1].t) - X(R[0].t);
  R.slice(0, -1).forEach((r, i) => {
    const n = R[i + 1], y1 = (Y(bid(r)) + Y(bid(n))) / 2, y2 = (Y(r.real) + Y(n.real)) / 2;
    d.rect(X(r.t), Math.min(y1, y2), step + 0.6, Math.max(Math.abs(y2 - y1), 0.6),
           r.corr > FLAT ? C.steel : C.redD);
  });
  for (let i = 0; i < R.length - 1; i++)
    d.seg(X(R[i].t), Y(bid(R[i])), X(R[i + 1].t), Y(bid(R[i + 1])), C.slateL, LW.ref, 'dash');
  for (let i = 0; i < R.length - 1; i++)
    d.seg(X(R[i].t), Y(R[i].real), X(R[i + 1].t), Y(R[i + 1].real), C.brass, LW.main);

  const IN = R.filter(r => r.t >= D.cit_range[0] && r.t <= D.cit_range[1]);
  const up = IN.reduce((a, b) => (b.corr > a.corr ? b : a));
  const dn = IN.reduce((a, b) => (b.corr < a.corr ? b : a));
  const cross = R.find((r, i) => i > 0 && (R[i - 1].corr - FLAT) * (r.corr - FLAT) < 0);
  if (cross) {
    d.vline(X(cross.t), 430, 142, C.dim2, LW.grid, 'dash');
    d.text('여기서 방향이 바뀝니다 (' + cross.t + '℃)',
           { x: X(cross.t) + 8, y: 432, w: 220, px: 11.5, lh: 1.2, color: C.dim });
  }
  d.text('낮게 신고 — ' + up.t + '℃ 에서 ' + (up.corr - FLAT).toFixed(1) + ' MW 못 팜',
         { x: X(up.t) + 14, y: (Y(bid(up)) + Y(up.real)) / 2 - 8, w: 250, px: 12,
           lh: 1.2, bold: true, color: C.slateL });
  d.text('높게 신고 — ' + dn.t + '℃ 에서 ' + (FLAT - dn.corr).toFixed(1) + ' MW 미달',
         { x: X(dn.t) - 264, y: (Y(bid(dn)) + Y(dn.real)) / 2 - 8, w: 250, px: 12,
           lh: 1.2, bold: true, color: C.red, align: 'right' });
  [[150, C.slateL, '종전 신고 (하나의 값)', true], [420, C.brass, '실제 능력', false]]
    .forEach(([x, col, s, dash]) => {
      d.hline(x, 428, 26, col, dash ? LW.ref : LW.main, dash ? 'dash' : 'solid');
      d.text(s, { x: x + 34, y: 421, w: 240, px: 12, lh: 1.3, color: col });
    });

  d.text('종전 누계 — 낮게 신고해 못 판 양 *' + B.opp.toFixed(1) + ' MW*   ·   ' +
         '신고값을 못 채운 *' + B.short + '회* (과대 신고 ' + B.over.toFixed(1) + ' MW)',
         { x: 96, y: 598, w: 1088, px: 13.5, lh: 1.3, color: C.body, align: 'center' });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  /* 금액 환산 기준을 아직 못 받았다(계획서 §9 Q5) — '수익' 이라 단정하지 않는다 */
  T.foot(d, '그때는 최선이었습니다 — 이제 *온도별로 알 수 있는* 데이터가 쌓였습니다.');
};
