/* v3-06 · 온도별로 배우는 보정 모델.
   구획 셋. 어떻게 바꿨나(2층 구조) / 결과 곡선 / 겪은 일(모델을 몰라 겨루게 했다).

   이 장의 그림은 도구가 그린 실제 곡선이다. 점선이 계산값, 주황이 실제,
   흰 점이 시험 결과. 흰 점이 주황 곡선을 따라가는 것이 이 과제가 한 일 전부다. */
'use strict';
module.exports = (pptx, T, meta, D) => {
  const { C, G, LW } = T;
  const A = require('./assets.js');
  const { d } = T.shell(pptx, { name: '개선 방안', idx: 4, step: 4 });
  const M = D.methods;
  T.title(d, '온도마다 다르게 배우기', null, { px: 33 });
  T.lead(d, '계산식은 그대로 두고, 계산한 값과 실제의 차이만 온도마다 따로 배우게 했습니다.',
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
  d.text('계산한 값과 실제의 차이만 넘깁니다', { x: 124, y: 310, w: 320, px: 12, lh: 1.3,
                                              color: C.dim });
  d.box(92, 338, 360, 74, null, C.brass, 1.6);
  d.text('새로 만든 것', { x: 106, y: 348, w: 200, px: 11.5, lh: 1.2, bold: true,
                            color: C.brass });
  d.text('온도마다 다른 값', { x: 106, y: 368, w: 330, px: 17, lh: 1.3, bold: true,
                                color: C.ink });
  d.text('시험 ' + D.n + '회를 학습해 온도마다 다른 값을 줍니다.',
         { x: 106, y: 390, w: 330, px: 12, lh: 1.3, color: C.dim });

  /* 구획 2 — 도구가 실제로 그려 주는 화면. 내가 다시 그리지 않고 캡처를 쓴다.
     회신 "중간중간에 Tool 캡쳐를 섞어 쓰면 좋을 듯" 반영. */
  d.section(488, 186, 720, 232, 2, '도구가 그려 주는 화면', '주황이 배운 값, 흰 점이 시험 결과');
  d.imgFit(A.toolGap, 500, 222, 696, 162);
  d.text('온도마다 더할 값이 다릅니다. 흰 점이 실제 시험 결과이고, 주황 선이 도구가 배운 값입니다.',
         { x: 500, y: 392, w: 696, px: 12, lh: 1.3, color: C.dim2 });

  /* 구획 3 — 겪은 일 */
  d.section(G.L, 430, G.W, 194, 3, '겪은 일 · 어떤 방법을 써야 하는지 몰랐다', '후보 7가지');
  d.text('이런 예측을 처음 다뤘습니다. 무엇을 써야 하는지 몰라서 후보 일곱 가지를 ' +
         '늘어놓고 같은 데이터로 겨루게 했습니다.\n' +
         '한 회를 가리고 나머지로 그 회를 맞혀 봅니다. 사람이 아니라 성적이 골랐습니다.',
         { x: 92, y: 470, w: 470, px: 13, lh: 1.6, lines: 4, color: C.body });

  const lo = Math.floor(Math.min(...M.map(m => m.mae)) * 10) / 10 - 0.1;
  const hi = Math.max(...M.map(m => m.mae));
  const BX = v => 700 + (v - lo) / (hi - lo) * 330;
  M.forEach((m, i) => {
    const y = 468 + i * 21, win = i === 0;
    const NAME = { 'gp:rbf': 'RBF', 'gp:rq': 'RQ', 'gp:matern52': 'Matern 5/2',
                   'gp:matern32': 'Matern 3/2', 'gp:exp': '지수',
                   'curve': '거리가중', 'bin': '구간평균' };
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
