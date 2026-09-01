/* v2-09 · 향후 추이 분석 — 요소 2개: 갱신 순환 4단계 / 자동 가드 3개.
   시운전 함정 3개 설명을 '가드' 로 압축했다.                             */
'use strict';
const STEP = [
  ['회차 추가',   '새 실측 한 줄'],
  ['다시 채점',   '7가지 전부 재채점'],
  ['방식 재선정', '1위가 바뀌면 교체'],
  ['신고값 갱신', '근거와 함께 출력'],
];
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  const { d } = T.shell(pptx, { sec: '모니터링', idx: 5, step: 5 });
  T.title(d, '회차가 쌓이면 스스로 다시 고르고,', '*의심은 코드가 합니다*');
  T.lead(d, '사람이 다시 손대야 하는 상수가 없습니다. _추가 → 재채점 → 재선정_ 이 한 바퀴입니다.',
         { lines: 1 });

  /* 갱신 순환 */
  d.zone(G.L, 284, G.W, 150);
  STEP.forEach(([k, v], i) => {
    const x = 104 + i * 268;
    d.box(x, 312, 212, 68, C.ground, C.rule, 1);
    d.rect(x, 312, 212, 2, i === 0 ? C.brass : C.rule);
    d.plab('STEP ' + (i + 1), x + 14, 322, 120);
    d.text(k, { x: x + 14, y: 340, w: 184, px: 16.5, lh: 1.3, bold: true, color: C.ink });
    d.text(v, { x: x + 14, y: 362, w: 184, px: 11.5, lh: 1.2, color: C.dim });
    if (i < 3) d.text('→', { x: x + 220, y: 336, w: 44, px: 20, lh: 1.2,
                             color: C.brass, align: 'center' });
  });
  d.hline(210, 400, 800, C.brassD, 1.4, 'dash');
  d.text('↺   회차가 늘면 다시 처음으로 — 사람이 누르는 버튼은 없습니다',
         { x: 210, y: 406, w: 800, px: 13, lh: 1.3, color: C.dim, align: 'center' });

  /* 자동 가드 3개 */
  const K = D.commission;
  [[72,  '자동 기각 문턱', '80', '%',
    '한 건을 빼도 결론이 유지되는 비율이 *80% 미달* 이면 코드가 기각합니다.'],
   [467, '유의 판정',      '0.05', 'α',
    '임계 상관을 넘지 못하면 _관계 없음_ 으로 봅니다. 눈에 보이는 관계도 통과해야 합니다.'],
   [862, '시운전 대조',    String(K.n), '회차',
    '예측을 *먼저 남기고* 실측과 대조합니다. 사후에 맞추는 것을 막습니다.']]
    .forEach(([x, l, v, u, t]) => {
      d.panel(x, 470, 346, 'on');
      d.plab(l, x, 484, 346);
      d.bigUnit(v, u, x, 506, 44, C.brass, 16);
      d.txt(t, x, 566, 346, 2);
    });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '사람이 다시 정할 상수가 없습니다 — *틀린 설명은 코드가 걸러냅니다*.');
};
