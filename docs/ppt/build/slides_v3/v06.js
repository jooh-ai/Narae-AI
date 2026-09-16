/* v3-06 · 온도별로 배우는 보정 모델.
   구획 셋. 어떻게 바꿨나(2층 구조) / 결과 곡선 / 겪은 일(모델을 몰라 겨루게 했다).

   이 장의 그림은 도구가 그린 실제 곡선이다. 점선이 계산값, 주황이 실제,
   흰 점이 시험 결과. 흰 점이 주황 곡선을 따라가는 것이 이 과제가 한 일 전부다. */
'use strict';
module.exports = (pptx, T, meta, D) => {
  const { C, G, LW } = T;
  const { d } = T.shell(pptx, { name: '개선 방안', idx: 4, step: 4 });
  const P = D.profile, R = P.rows, M = D.methods, B = D.best;
  T.title(d, '온도별로 배우는 보정 모델', null, { px: 33 });
  T.lead(d, '계산식은 그대로 두고, 계산값과 실제의 차이만 온도별로 배우게 했습니다.',
         { y: 146, lines: 1 });

  /* 구획 1 — 2층 구조 */
  d.section(G.L, 186, 400, 232, 1, '바꾼 것과 두고 온 것', '');
  d.box(92, 226, 360, 74, null, C.slate, 1.4);
  d.text('그대로 둔 것', { x: 106, y: 236, w: 200, px: 11.5, lh: 1.2, bold: true,
                            color: C.slateL });
  d.text('제작사 계산식', { x: 106, y: 256, w: 330, px: 17, lh: 1.3, bold: true,
                            color: C.ink });
  d.text('검증된 식입니다. 손대지 않았습니다.',
         { x: 106, y: 278, w: 330, px: 12, lh: 1.3, color: C.dim });
  d.text('↓', { x: 92, y: 306, w: 30, px: 18, lh: 1.2, color: C.brass });
  d.text('계산값과 실제의 차이만 넘깁니다', { x: 124, y: 310, w: 320, px: 12, lh: 1.3,
                                              color: C.dim });
  d.box(92, 338, 360, 74, null, C.brass, 1.6);
  d.text('새로 만든 것', { x: 106, y: 348, w: 200, px: 11.5, lh: 1.2, bold: true,
                            color: C.brass });
  d.text('온도별 보정 곡선', { x: 106, y: 368, w: 330, px: 17, lh: 1.3, bold: true,
                                color: C.ink });
  d.text('시험 ' + D.n + '회를 학습해 온도마다 다른 값을 줍니다.',
         { x: 106, y: 390, w: 330, px: 12, lh: 1.3, color: C.dim });

  /* 구획 2 — 결과 곡선 */
  d.section(488, 186, 720, 232, 2, '온도별 보정값', '−10 ~ 40℃ · 단위 MW');
  const X = t => 540 + (t + 10) * 12.6, Y = v => 340 - v * 6.4;
  [8, 4, 0, -4].forEach(v => { d.hline(536, Y(v), 648, v === 0 ? C.rule : C.rule2, 1);
    d.text((v > 0 ? '+' : '') + v, { x: 496, y: Y(v) - 7, w: 34, px: 10, lh: 1.2,
      mono: true, color: C.dim2, align: 'right' }); });
  [0, 10, 20, 30, 40].forEach(t => d.text(t === 0 ? '0℃' : String(t),
    { x: X(t) - 22, y: 388, w: 44, px: 10, lh: 1.2, mono: true, color: C.dim2,
      align: 'center' }));
  d.hline(536, Y(D.blanket.flat), 648, C.slateL, LW.ref, 'dash');
  d.text('종전 · 하나로 고정', { x: 1000, y: Y(D.blanket.flat) - 19, w: 184, px: 11,
                                  lh: 1.2, bold: true, color: C.slateL, align: 'right' });
  const seg = R.filter(r => r.t >= -10 && r.t <= 40);
  for (let i = 0; i < seg.length - 1; i++)
    d.seg(X(seg[i].t), Y(seg[i].corr), X(seg[i + 1].t), Y(seg[i + 1].corr), C.brass, LW.main);
  D.scatter.filter(([t]) => t >= -10 && t <= 40)
    .forEach(([t, c]) => d.dot(X(t), Y(c), 3, C.body));
  d.text('주황 선이 도구가 배운 곡선이고 흰 점이 실제 시험 결과입니다.',
         { x: 536, y: 404, w: 648, px: 11.5, lh: 1.2, color: C.dim2 });

  /* 구획 3 — 겪은 일 */
  d.section(G.L, 430, G.W, 194, 3, '겪은 일 · 어떤 모델을 써야 하는지 몰랐다', '후보 7가지');
  d.text('회귀 모델이라는 것을 처음 다뤘습니다. 무엇을 써야 하는지 몰라서, ' +
         '후보를 늘어놓고 같은 데이터로 겨루게 했습니다. 한 회를 가리고 나머지로 ' +
         '그 회를 맞혀 보는 방식입니다. 사람이 고른 것이 아니라 성적이 골랐습니다.',
         { x: 92, y: 470, w: 470, px: 13, lh: 1.6, lines: 4, color: C.body });

  const lo = Math.floor(Math.min(...M.map(m => m.mae)) * 10) / 10 - 0.1;
  const hi = Math.max(...M.map(m => m.mae));
  const BX = v => 700 + (v - lo) / (hi - lo) * 330;
  M.forEach((m, i) => {
    const y = 468 + i * 21, win = i === 0;
    const NAME = { 'gp:rbf': 'RBF', 'gp:rq': 'RQ', 'gp:matern52': 'Matern 5/2',
                   'gp:matern32': 'Matern 3/2', 'gp:exp': '지수',
                   'curve': '커널회귀', 'bin': '구간평균' };
    const nm = NAME[m.key] || m.key;
    d.text(nm, { x: 574, y, w: 122, px: 11.5, lh: 1.2, bold: win,
                 color: win ? C.brass : C.dim2, align: 'right' });
    d.rect(700, y + 2, Math.max(BX(m.mae) - 700, 4), 10, win ? C.brass : C.steel);
    d.text(m.mae.toFixed(2), { x: BX(m.mae) + 8, y, w: 52, px: 11, lh: 1.2, mono: true,
                               bold: win, color: win ? C.brass : C.dim });
    if (win) d.text('← 1위. 이것을 씁니다', { x: 1050, y, w: 158, px: 11.5, lh: 1.2,
                                              bold: true, color: C.brass });
  });
  d.text('막대가 짧을수록 잘 맞힌 것입니다. 단위 MW.',
         { x: 574, y: 616, w: 440, px: 11, lh: 1.2, color: C.dim2 });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '계산식은 그대로 두었으니, 다른 발전소로도 그대로 옮길 수 있습니다.');
};
