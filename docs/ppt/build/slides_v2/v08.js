/* v2-08 · 해결 방안(2) 모델 선정 — 요소 2개: 종전 대비 2막대 / 후보 7가지 막대.
   방식별 보정곡선 차트를 빼고 '누가 이겼나' 하나만 남겼다.               */
'use strict';
const NAME = {
  'gp:rbf': 'GP · RBF', 'gp:rq': 'Rational Quadratic',
  'gp:matern52': 'Matérn 5/2', 'gp:matern32': 'Matérn 3/2',
  'gp:exp': '지수형', 'curve': '거리가중 평균', 'bin': '온도구간 평균',
};
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  const { d } = T.shell(pptx, { sec: '모델 선정', idx: 4, step: 4 });
  const M = D.methods, B = D.best, nm = k => NAME[k] || k;
  T.title(d, '방식 7가지를 같은 조건에서 겨뤄,', '*가장 잘 맞히는 하나*를 골랐습니다');
  T.lead(d, '정답을 _한 건씩 가리고 나머지로 맞혀_ 보는 방식으로 ' + D.n +
         '번 채점했습니다. 1위는 *' + nm(B.key) + '* 입니다.', { lines: 1 });

  /* 종전 vs 개선 — 평균 오차 */
  d.zone(G.L, 284, G.W, 140);
  d.plab('평균 오차  ·  단위 MW  ·  낮을수록 좋다', 96, 298, 600);
  const SC = 760 / D.blanket.mae;
  d.text('종전 · 하나의 값', { x: 96, y: 336, w: 200, px: 12.5, lh: 1.3,
                               mono: true, bold: true, color: C.slateL });
  d.rect(300, 334, D.blanket.mae * SC, 18, C.slate);
  d.text(D.blanket.mae.toFixed(2), { x: 300 + D.blanket.mae * SC + 12, y: 331, w: 90, px: 20,
                                     lh: 1.2, mono: true, bold: true, color: C.slateL });
  d.text('개선 · ' + nm(B.key), { x: 96, y: 382, w: 200, px: 12.5, lh: 1.3,
                                  mono: true, bold: true, color: C.brass });
  d.rect(300, 378, B.mae * SC, 22, C.brass);
  d.text(B.mae.toFixed(2), { x: 300 + B.mae * SC + 14, y: 370, w: 120, px: 32,
                             lh: 1.2, mono: true, bold: true, color: C.brass });

  /* 후보 7가지 — 확대 비교 */
  d.zone(G.L, 456, G.W, 168);
  const lo = Math.floor(Math.min(...M.map(m => m.mae)) * 20) / 20;
  const hi = Math.max(...M.map(m => m.mae));
  const BX = v => 320 + (v - lo) / (hi - lo) * 620;
  d.plab('후보 ' + M.length + '가지  ·  ' + lo.toFixed(2) + ' ~ ' + hi.toFixed(2) +
         ' 구간만 확대  ·  눈으로는 고를 수 없다', 96, 470, 800);
  const TICK = [];
  for (let v = lo; v <= hi + 1e-9; v += 0.05) TICK.push(Math.round(v * 100) / 100);
  TICK.forEach(v => d.vline(BX(v), 488, 112, C.rule2, 1));
  M.forEach((m, i) => {
    const y = 490 + i * 17, win = i === 0;
    const col = win ? C.brass : i <= 3 ? C.brassD : i < M.length - 1 ? C.steel : C.slate;
    d.text(nm(m.key), { x: 96, y: y - 1, w: 200, px: 12.5, lh: 1.3, bold: win,
                        color: win ? C.brass : C.dim });
    d.rect(320, y, Math.max(BX(m.mae) - 320, 8), 11, col);
    d.text(m.mae.toFixed(3), { x: BX(m.mae) + 8, y: y - 2, w: 62, px: 12.5, lh: 1.3,
                               mono: true, bold: win, color: win ? C.brass : C.dim });
  });
  TICK.forEach(v => d.text(v.toFixed(2), { x: BX(v) - 24, y: 610, w: 48, px: 9.5, lh: 1.3,
                                           mono: true, color: C.dim2, align: 'center' }));

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '방식을 *감으로 정하지 않았습니다* — 같은 조건에서 채점해 1위를 데이터가 지목했습니다.');
};
