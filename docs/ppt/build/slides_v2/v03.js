/* v2-03 · 한 장 요약 — 요소 2개: 큰 숫자 3개 / 종전·현재 한 줄 대비.
   게이지와 설명문을 걷어내고 숫자를 46 → 60px 로 키웠다.               */
'use strict';
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  const { d } = T.shell(pptx, { sec: '한 장 요약' });
  T.title(d, '판단 하나에 기대던 숫자를,', '데이터가 *스스로 갱신합니다*', { w: 1040 });
  T.lead(d, '같은 ' + D.n + '회차를 같은 방식으로 채점했더니 *세 지표가 동시에* 좋아졌습니다.',
         { w: 1060, lines: 1 });

  const I = D.impact;
  [[72,  '예측 오차',      I.gp.mae.toFixed(2),  'MW', '← ' + I.blanket.mae.toFixed(2), C.slateL],
   [467, '기준 미달 회차', String(I.gp.short),   '건',  '← ' + I.blanket.short,          C.red],
   [862, '과대 신고 누계', I.gp.over.toFixed(1), 'MW', '← ' + I.blanket.over.toFixed(1), C.slateL]]
    .forEach(([x, l, v, u, was, wc]) => {
      d.panel(x, 284, 346, wc === C.red ? 'bad' : 'on');
      d.plab(l, x, 298, 346);
      const vw = d.bigUnit(v, u, x, 322, 60, C.brass, 18);
      d.text(was, { x: x + vw + 74, y: 356, w: 140, px: 21, lh: 1.2, mono: true, color: wc });
    });

  /* 종전 / 현재 — 한 덩어리, 키워드만 */
  d.rect(G.L, 460, G.W, 156, C.groove);
  d.rect(G.L, 460, 568, 2, C.slate);
  d.rect(640, 460, 568, 2, C.brass);
  d.vline(640, 488, 100, C.rule, 1);
  d.rect(616, 518, 48, 40, C.groove);
  d.text('→', { x: 616, y: 522, w: 48, px: 32, lh: 1.1, color: C.brass, align: 'center' });

  d.plab('종전  ·  사람의 판단', 96, 484, 500, C.slate);
  d.sub('보정값 ~1개~ 를 정수로', 96, 508, 500, 1, C.slate);
  d.txt('온도를 보지 않는 값이었습니다.', 96, 552, 500, 1);
  d.plab('현재  ·  데이터의 학습', 664, 484, 500, C.brass);
  d.sub('온도별 곡선을 *데이터가 갱신*', 664, 508, 500, 1);
  d.txt('회차가 쌓이면 방식까지 다시 고릅니다.', 664, 552, 500, 1);

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '사람이 정하던 값이 아니라, *' + D.n + '회차 실적이 만들어 내는 값*입니다.');
};
