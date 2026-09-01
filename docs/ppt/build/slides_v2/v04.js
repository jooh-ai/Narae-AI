/* v2-04 · 개요 및 추진 배경 — 요소 2개: 양방향 도식 / 종전 실적 2수치.
   4단 절차와 설명 카드를 걷어내고 '어느 쪽으로 틀려도 손실' 만 남겼다.   */
'use strict';
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  const { d } = T.shell(pptx, { sec: '왜 하는가', idx: 1, step: 1 });
  T.title(d, '매주 신고하는 숫자입니다,', '틀리면 *양쪽으로* 손실입니다');
  T.lead(d, '다음 주에 낼 수 있는 최대 출력을 신고하고, 그 숫자가 _그대로 입찰_ 이 됩니다.',
         { lines: 1 });

  /* 양방향 도식 */
  d.zone(G.L, 284, G.W, 150);
  d.text('실제 발전 능력', { x: 540, y: 300, w: 200, px: 14, lh: 1.3,
                             bold: true, color: C.ink, align: 'center' });
  d.vline(640, 326, 84, C.ink, 2);
  d.hline(200, 368, 400, C.slateL, 2.4);
  d.hline(680, 368, 400, C.red, 2.4);
  d.text('◀', { x: 186, y: 359, w: 20, px: 12, lh: 1.1, color: C.slateL });
  d.text('▶', { x: 1074, y: 359, w: 20, px: 12, lh: 1.1, color: C.red });
  d.sub('낮게 신고', 200, 330, 300, 1, C.slateL);
  d.sub('높게 신고', 880, 330, 300, 1, C.red);
  d.txt('팔 수 있었는데 못 팝니다  ·  기회손실', 200, 384, 400, 1);
  d.text('실제가 못 미칩니다  ·  기준 미달 → 벌점',
         { x: 680, y: 384, w: 400, px: 15, lh: 1.68, color: C.body, align: 'right' });

  /* 종전 실적 — 큰 숫자 2개 */
  const B = D.impact.blanket;
  [[72,  '종전 · 낮게 신고한 양 누계', B.opp.toFixed(1), 'MW',
    '겨울에 이 방향으로 치우쳤습니다'],
   [652, '종전 · 기준 미달 회차',      String(B.short),  '회차',
    '누적 ' + D.n + '회차 중 · 과대 신고 ' + B.over.toFixed(1) + ' MW']]
    .forEach(([x, l, v, u, t]) => {
      d.panel(x, 466, 556, 'bad');
      d.plab(l, x, 480, 556, C.red);
      d.bigUnit(v, u, x, 504, 52, C.red, 17);
      d.txt(t, x, 578, 556, 1);
    });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '어느 쪽으로 틀려도 손실입니다 — *정확도가 곧 수익*입니다.');
};
