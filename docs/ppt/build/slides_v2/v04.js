/* v2-04 · 개요 및 추진 배경 — 요소 2개: 손실 그래프 / 종전 실적 2수치.
   [검토 반영] 화살표 도식을 걷어내고 출력 곡선 위에 손실을 얹었다. 화살표는
   '어느 쪽으로 틀리면 손해' 라는 방향만 말하고 '얼마나' 를 말하지 못했다.

   그래프가 말하는 것 — 종전처럼 온도 구분 없이 하나의 값(+2.5)으로 신고하면
   신고 곡선은 이론 곡선을 그대로 평행이동한 것이 된다. 실제 능력 곡선은 그렇게
   움직이지 않으므로 두 곡선이 벌어지고, 그 벌어진 폭이 곧 손실이다. 겨울에는
   신고가 낮아 못 팔고(슬레이트), 여름에는 신고가 높아 미달(레드)이다.
   두 띠는 세로 막대를 촘촘히 세워 채운다 — 얇아도 색 면이면 눈에 들어온다. */
'use strict';
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  const { d } = T.shell(pptx, { sec: '왜 하는가', idx: 1, step: 1 });
  const P = D.profile, R = P.rows, FLAT = D.blanket.flat, B = D.impact.blanket;
  T.title(d, '매주 신고하는 숫자입니다,', '틀리면 *양쪽으로* 손실입니다');
  T.lead(d, '온도 구분 없이 하나의 값으로 신고하면, _같은 방식인데도 계절에 따라_ ' +
         '어느 쪽으로든 어긋납니다.', { lines: 1 });

  /* 손실 그래프 */
  d.zone(G.L, 284, G.W, 224);
  d.plab('외기온도별 출력  ·  단위 MW  ·  종전 신고(이론값 + ' + FLAT.toFixed(1) +
         ' 하나로) vs 실제 능력', 96, 294, 700);

  const t0 = R[0].t, t1 = R[R.length - 1].t;
  const bid = r => r.theory + FLAT;                    // 종전 방식의 신고값
  const vs = R.map(bid).concat(R.map(r => r.real));
  const lo = Math.floor(Math.min(...vs) / 20) * 20 - 5;
  const hi = Math.ceil(Math.max(...vs) / 20) * 20 + 5;
  const X = t => 150 + (t - t0) * (1000 / (t1 - t0));
  const Y = v => 478 - (v - lo) * (160 / (hi - lo));
  for (let v = lo + 5; v <= hi; v += 20) {
    d.hline(150, Y(v), 1000, C.rule2, 1);
    d.text(String(v), { x: 96, y: Y(v) - 7, w: 46, px: 10, lh: 1.3, mono: true,
                        color: C.dim2, align: 'right' });
  }
  d.hline(150, 478, 1000, C.rule, 1);
  for (let t = t0; t <= t1; t += 10) {
    d.vline(X(t), 478, 5, C.dim2, 1);
    d.text(t === t0 ? t + '℃' : String(t), { x: X(t) - 24, y: 486, w: 48, px: 10, lh: 1.3,
                                             mono: true, color: C.dim2, align: 'center' });
  }

  /* 두 곡선 사이를 채운다 — 부호가 바뀌는 곳에서 색이 갈린다 */
  const step = X(R[1].t) - X(R[0].t);
  R.slice(0, -1).forEach((r, i) => {
    const n = R[i + 1], y1 = (Y(bid(r)) + Y(bid(n))) / 2, y2 = (Y(r.real) + Y(n.real)) / 2;
    const up = r.corr > FLAT;                          // 실제가 신고보다 크다 = 낮게 신고
    d.rect(X(r.t), Math.min(y1, y2), step + 0.6, Math.max(Math.abs(y2 - y1), 0.6),
           up ? C.steel : C.redD);
  });
  for (let i = 0; i < R.length - 1; i++)
    d.seg(X(R[i].t), Y(bid(R[i])), X(R[i + 1].t), Y(bid(R[i + 1])), C.slateL, 2.2, 'dash');
  for (let i = 0; i < R.length - 1; i++)
    d.seg(X(R[i].t), Y(R[i].real), X(R[i + 1].t), Y(R[i + 1].real), C.brass, 2.6);

  /* 가장 크게 벌어지는 두 곳만 숫자로 짚는다 (실측이 있는 온도 범위 안에서) */
  const IN = R.filter(r => r.t >= D.cit_range[0] && r.t <= D.cit_range[1]);
  const up = IN.reduce((a, b) => (b.corr > a.corr ? b : a));
  const dn = IN.reduce((a, b) => (b.corr < a.corr ? b : a));
  d.text('낮게 신고 — ' + up.t + '℃ 에서 ' + (up.corr - FLAT).toFixed(1) + ' MW 못 팜',
         { x: X(up.t) + 14, y: (Y(bid(up)) + Y(up.real)) / 2 - 8, w: 260, px: 12.5,
           lh: 1.2, bold: true, color: C.slateL });
  d.text('높게 신고 — ' + dn.t + '℃ 에서 ' + (FLAT - dn.corr).toFixed(1) + ' MW 미달',
         { x: X(dn.t) - 274, y: (Y(bid(dn)) + Y(dn.real)) / 2 - 8, w: 260, px: 12.5,
           lh: 1.2, bold: true, color: C.red, align: 'right' });
  /* 손실의 방향이 바뀌는 온도 — 이 그래프에서 가장 설명 가치가 큰 지점이다 */
  const cross = R.find((r, i) => i > 0 && (R[i - 1].corr - FLAT) * (r.corr - FLAT) < 0);
  if (cross) {
    d.vline(X(cross.t), 330, 148, C.dim2, 1, 'dash');
    d.text('여기서 방향이 바뀝니다 (' + cross.t + '℃)',
           { x: X(cross.t) + 8, y: 332, w: 220, px: 11.5, lh: 1.2, color: C.dim });
  }
  [[150, C.slateL, '종전 신고 (하나의 값)', true], [420, C.brass, '실제 능력', false]]
    .forEach(([x, col, s, dash]) => {
      d.hline(x, 318, 26, col, dash ? 2.2 : 2.6, dash ? 'dash' : 'solid');
      d.text(s, { x: x + 34, y: 311, w: 240, px: 12, lh: 1.3, color: col });
    });

  /* 그래서 종전에 얼마나 났나 */
  d.zone(G.L, 520, G.W, 104);
  d.vline(640, 540, 64, C.rule, 1);
  [[96, '낮게 신고한 양 누계', B.opp.toFixed(1), 'MW', C.slateL,
    '팔 수 있었는데 못 판 양 — 겨울에 몰립니다'],
   [664, '기준 미달 회차', String(B.short), '회', C.red,
    '누적 ' + D.n + '회 중  ·  과대 신고 ' + B.over.toFixed(1) + ' MW']]
    .forEach(([x, l, v, u, col, t]) => {
      d.plab(l, x, 532, 500, col);
      d.bigUnit(v, u, x, 550, 40, C.brass, 15);
      d.txt(t, x, 600, 500, 1);
    });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  /* [검토 반영] 금액 환산 기준을 아직 못 받았다(계획서 §9 Q5). 근거 없이
     '수익' 이라 단정하지 않는다 — 기준을 받으면 원 단위로 바꿔 넣는다. */
  T.foot(d, '어느 쪽으로 틀려도 손실입니다 — *정확도가 곧 손익*입니다.');
};
