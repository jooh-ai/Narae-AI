/* v3-07 · 바꾼 것 두 가지.

   2026-09-16 회신이 이 장을 다시 쓰게 했다.
     "내가 이 Tool을 개발한 이유는 단순해. 여러가지로 반복되는 과정을 합치고,
      결과의 정확도를 높인다. 하지만 이 단순한 내용을 PPT는 어렵게 풀어내."

   맞는 말이었다. 이 장이 '정확도' 이야기만 하고 있었다. 만든 이유가 둘인데
   하나만 적어 놓았으니 읽는 사람은 왜 만들었는지 절반만 알게 된다.
   그래서 구획 1 을 **두 기둥**으로 다시 세웠다. 합친 것과 정확해진 것.       */
'use strict';
const A = require('./assets.js');
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  const M = D.methods;
  const { d } = T.shell(pptx, { name: '개선 방안', idx: 4, step: 4 });
  T.title(d, '바꾼 것 두 가지', null, { px: 33 });
  T.lead(d, '하나는 흩어진 과정을 합친 것입니다. 다른 하나는 숫자를 온도마다 다르게 한 것입니다.',
         { y: 146, lines: 1 });

  /* 구획 1 — 두 기둥 */
  d.section(G.L, 186, 400, 232, 1, '무엇을 바꿨나', '');
  [['흩어진 과정을 합쳤다', '엑셀 4개', '도구 1개'],
   ['숫자를 온도마다 다르게', '값 1개', '온도별 곡선']].forEach(([k, a, b], i) => {
    const y = 226 + i * 88;
    d.rect(92, y, 4, 62, C.brass);
    d.text(String(i + 1), { x: 108, y, w: 20, px: 13, lh: 1.2, mono: true, bold: true,
                            color: C.brass });
    d.text(k, { x: 132, y: y - 2, w: 306, px: 17.5, lh: 1.3, bold: true, color: C.ink });
    const aw = Math.ceil(T.textW(a, 15)) + 4;
    d.text(a, { x: 132, y: y + 30, w: aw, px: 15, lh: 1.25, color: C.slateL });
    d.text('→', { x: 132 + aw + 8, y: y + 32, w: 22, px: 13, lh: 1.2, color: C.dim2 });
    d.text(b, { x: 132 + aw + 34, y: y + 28, w: 452 - (132 + aw + 34), px: 17, lh: 1.25, bold: true,
                color: C.brass });
  });
  d.text('제작사 계산식은 손대지 않았습니다.',
         { x: 92, y: 392, w: 360, px: 13, lh: 1.3, color: C.dim });

  /* 구획 2 — 도구가 실제로 그려 주는 화면 */
  d.section(488, 186, 720, 232, 2, '도구가 그려 주는 화면', '주황이 배운 값, 흰 점이 시험 결과');
  d.imgFit(A.toolGap, 500, 222, 696, 162);
  d.text('온도마다 더할 값이 다릅니다.',
         { x: 500, y: 392, w: 696, px: 13, lh: 1.3, color: C.dim });

  /* 구획 3 — 겪은 일 */
  d.section(G.L, 430, G.W, 194, 3, '겪은 일 · 어떤 방법을 써야 하는지 몰랐다', '후보 7가지');
  d.text('이런 예측을 해 본 적이 없었습니다. 그래서 후보 일곱 가지를 늘어놓고 ' +
         '같은 데이터로 겨루게 했습니다.\n한 회를 가리고 나머지로 그 회를 맞혀 봅니다. ' +
         '사람이 아니라 성적이 골랐습니다.',
         { x: 92, y: 472, w: 470, px: 13.5, lh: 1.6, lines: 4, color: C.body });

  const lo = Math.floor(Math.min(...M.map(m => m.mae)) * 10) / 10 - 0.1;
  const hi = Math.max(...M.map(m => m.mae));
  const BX = v => 700 + (v - lo) / (hi - lo) * 330;
  const NAME = { 'gp:rbf': 'RBF', 'gp:rq': 'RQ', 'gp:matern52': 'Matern 5/2',
                 'gp:matern32': 'Matern 3/2', 'gp:exp': '지수',
                 'curve': '거리가중', 'bin': '구간평균' };
  M.forEach((m, i) => {
    const y = 468 + i * 21, win = i === 0;
    d.text(NAME[m.key] || m.key, { x: 574, y, w: 122, px: 11.5, lh: 1.2, bold: win,
                                   color: win ? C.brass : C.dim2, align: 'right' });
    d.rect(700, y + 2, Math.max(BX(m.mae) - 700, 4), 10, win ? C.brass : C.steel);
    d.text(m.mae.toFixed(2), { x: BX(m.mae) + 8, y, w: 52, px: 11, lh: 1.2, mono: true,
                               bold: win, color: win ? C.brass : C.dim });
    if (win) d.text('← 이것을 씁니다', { x: 1050, y, w: 158, px: 11.5, lh: 1.2,
                                          bold: true, color: C.brass });
  });
  d.text('막대가 짧을수록 잘 맞힌 것입니다. 단위 MW.',
         { x: 574, y: 616, w: 440, px: 11, lh: 1.2, color: C.dim2 });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '계산식을 그대로 두었으니 다른 발전소에도 옮겨 쓸 수 있습니다.');
};
