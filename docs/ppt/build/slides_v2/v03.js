/* v2-03 · 한 장 요약 — 요소 2개: 큰 숫자 3개 / 종전·현재 한 줄 대비.
   게이지와 설명문을 걷어내고 숫자를 46 → 60px 로 키웠다.               */
'use strict';
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  const { d } = T.shell(pptx, { sec: '한 장 요약' });
  T.title(d, '엑셀 4개로 하던 일을 도구 하나로,', '감으로 정한 값을 *데이터로*', { w: 1040 });
  T.lead(d, '일 처리는 *날짜·시각 한 번 입력*으로 끝나고, 신고 숫자는 *' + D.n +
         '회 실적*이 정합니다.', { w: 1060, lines: 1 });

  const I = D.impact;
  [[72,  '예측 오차  ·  MAE', I.gp.mae.toFixed(2),  'MW',
    '← ' + I.blanket.mae.toFixed(2), C.slateL,
    '신고할 값을 미리 계산했을 때 실제와 벌어진 폭의 평균입니다. 작을수록 좋습니다.'],
   [467, '기준 미달 회차', String(I.gp.short),   '회',
    '← ' + I.blanket.short,          C.red,
    '실제 출력이 신고값에 못 미친 횟수입니다. ' + D.n + '회 중 몇 번이었나.'],
   [862, '과대 신고 누계', I.gp.over.toFixed(1), 'MW',
    '← ' + I.blanket.over.toFixed(1), C.slateL,
    D.n + '회 동안 실제보다 높게 신고한 양을 모두 더한 값입니다.']]
    .forEach(([x, l, v, u, was, wc, why]) => {
      d.panel(x, 284, 346, wc === C.red ? 'bad' : 'on');
      d.plab(l, x, 298, 346);
      const vw = d.bigUnit(v, u, x, 322, 60, C.brass, 18);
      d.text(was, { x: x + vw + 74, y: 356, w: 140, px: 21, lh: 1.2, mono: true, color: wc });
      d.text(why, { x, y: 400, w: 346, px: 12.5, lh: 1.55, lines: 2, color: C.dim });
    });

  /* 종전 / 현재 — 한 덩어리, 키워드만 */
  d.rect(G.L, 460, G.W, 156, C.groove);
  d.rect(G.L, 460, 568, 2, C.slate);
  d.rect(640, 460, 568, 2, C.brass);
  d.vline(640, 488, 100, C.rule, 1);
  d.rect(616, 518, 48, 40, C.groove);
  d.text('→', { x: 616, y: 522, w: 48, px: 32, lh: 1.1, color: C.brass, align: 'center' });

  d.plab('종전  ·  엑셀 4개  ·  사람의 판단', 96, 484, 500, C.slate);
  d.sub('온도와 무관한 값 ~1개~ 를 손으로', 96, 508, 500, 1, C.slate);
  d.txt('엑셀 4개를 순서대로 돌려 만들었습니다.', 96, 552, 500, 1);
  d.plab('현재  ·  도구 1개  ·  데이터의 학습', 664, 484, 500, C.brass);
  d.sub('온도별 곡선을 *데이터가 갱신*', 664, 508, 500, 1);
  d.txt('날짜·시각만 넣으면 바로 나옵니다.', 664, 552, 500, 1);

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '일은 *실행 한 번*으로, 숫자는 *' + D.n + '회 실적이 만들어 내는 값*으로 바꿨습니다.');
};
