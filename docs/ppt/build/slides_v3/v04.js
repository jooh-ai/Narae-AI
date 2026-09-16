/* v3-04 · ② 현황 파악 및 문제 정의 — 그런데 문제가 있었다.

   요소 하나. 담당자 실적 시트에서 오려낸 세 열, 그것만 크게.
   산점도는 이 장에서 뺐다. 축을 읽어야 이해되는 그림은 이 자리에 맞지 않는다.
   엑셀 칸 두 개를 나란히 보여 주는 쪽이 훨씬 쉽다.

   오른쪽 말은 그림의 색과 짝을 맞춘다. 노란 칸을 가리키는 말에는 노란 표식,
   오른쪽 칸을 가리키는 말에는 회색 표식. 그래서 어디를 보라고 쓰지 않아도 된다. */
'use strict';
const A = require('./assets.js');
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  const { d } = T.shell(pptx, { sec: '문제', idx: 2, step: 2 });
  T.title(d, '그런데 문제가 있었습니다', null);

  d.zone(G.L, 172, 648, 400);
  d.plab('기존 실적 시트에서 세 열만 오렸습니다', 92, 184, 500);
  d.imgFit(A.xl1gap, 92, 208, 608, 336);
  d.text('같은 시트 같은 회차이고, 열 사이 거리만 좁혔습니다.',
         { x: 92, y: 552, w: 608, px: 11.5, lh: 1.2, color: C.dim2 });

  const RX = 752;
  d.rect(RX, 196, 26, 14, C.brass);
  d.text('시험할 때마다 달랐습니다', { x: RX + 38, y: 190, w: 414, px: 21, lh: 1.35,
                                       bold: true, color: C.ink });
  d.text('어떤 날은 11 정도 차이가 났고, 어떤 날은 4밖에 안 났습니다. ' +
         '한 번은 아예 반대로 나온 날도 있었습니다.',
         { x: RX, y: 228, w: 456, px: 15, lh: 1.7, lines: 3, color: C.body });

  d.rect(RX, 344, 26, 14, C.slate);
  d.text('더하는 값은 늘 같았습니다', { x: RX + 38, y: 338, w: 414, px: 21, lh: 1.35,
                                        bold: true, color: C.ink });
  d.text('차이가 얼마로 나오든 4를 더했습니다. 몇 달에 한 번 5나 2로 바꾸기는 했지만, ' +
         '온도마다 다르게 주지는 못했습니다.',
         { x: RX, y: 376, w: 456, px: 15, lh: 1.7, lines: 3, color: C.body });

  d.rect(RX, 480, 456, 1, C.rule);
  d.text('겨울에는 더 낼 수 있는데 적게 신고했고, 여름에는 못 내는데 많이 신고했습니다.',
         { x: RX, y: 496, w: 456, px: 15, lh: 1.7, lines: 3, color: C.dim });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '날씨마다 다른 것을 하나로 맞추려니 맞을 수가 없었습니다.');
};
