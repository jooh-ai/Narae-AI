/* v2-10 · 향후 추이 분석 — 요소 2개: 갱신 순환 4단계 / 자동 가드 3개.
   시운전 함정 3개 설명을 '가드' 로 압축했다.                             */
'use strict';
const STEP = [
  ['새 결과 넣기',   '테스트 1회 = 한 줄'],
  ['다시 채점',      '방식 7가지 전부'],
  ['더 잘 맞는 쪽으로', '1위가 바뀌면 교체'],
  ['신고값 갱신',    '근거와 함께 출력'],
];
module.exports = (pptx, T, meta, D) => {
  const { C, G, LW } = T;
  const { d } = T.shell(pptx, { sec: '모니터링', idx: 5, step: 5 });
  T.title(d, '테스트가 쌓이면 스스로 다시 고르고,', '*의심도 도구가 합니다*');
  T.lead(d, '사람이 다시 정해야 하는 숫자가 없습니다. _넣기 → 채점 → 고르기_ 가 한 바퀴입니다.',
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
  d.hline(210, 400, 800, C.brassD, LW.ref, 'dash');
  d.text('↺   테스트가 늘면 다시 처음으로 — 사람이 손으로 정하는 값은 없습니다',
         { x: 210, y: 406, w: 800, px: 13, lh: 1.3, color: C.dim, align: 'center' });

  /* 자동 가드 3개 */
  const K = D.commission;
  [[72,  '한 회만 빼도 뒤집히면 버린다', '80', '%',
    '한 회씩 빼 보며 다시 계산합니다. *열 번 중 여덟 번* 이상 같은 결론이 나와야 믿습니다.'],
   [467, '우연일 수 있으면 안 믿는다',   '20', '번에 1번',
    '우연히 그렇게 보일 확률이 *이보다 크면* 관계가 없다고 봅니다.'],
   [862, '뒤를 보지 않고 예측한다',      String(K.n), '회',
    '각 회차를 *그 앞의 데이터만으로* 예측했습니다. 뒤 회차를 미리 보지 않습니다.']]
    .forEach(([x, l, v, u, t]) => {
      d.panel(x, 470, 346, 'on');
      d.plab(l, x, 484, 346);
      d.bigUnit(v, u, x, 506, 44, C.brass, 16);
      d.txt(t, x, 566, 346, 2);
    });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '사람이 다시 정할 숫자가 없습니다 — *틀린 설명은 도구가 걸러냅니다*. ' +
        '앞으로는 실측 전에 예측을 남기는 기능도 씁니다.');
};
