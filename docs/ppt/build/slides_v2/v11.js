/* v2-11 · 향후 계획 및 수평 전개 — 요소 2개: 그대로/갈아끼움 대비 / 타임라인.
   사업소 실명은 확정 전이므로 쓰지 않는다(BUILD_STATE 미결 항목).        */
'use strict';
const KEEP = ['차이를 배우고 방식을 고르는 부분', '의심하고 걸러내는 절차', '프로파일 생성과 화면'];
const SWAP = ['설비별 계산식 (성능 곡선)', '설비 상수'];
const PLAN = [
  ['~ 2026.09', '위례 정착',        '누적 회차로 운영 중'],
  ['2026.10~12', '절차 문서화',      '검증·가드 기준을 사내 문서로'],
  ['2027 상반기', '같은 구조 1곳 시범', '계산식만 바꿔 나란히 운전'],
  ['2027 하반기', '수평 전개',        '계산식 부분을 분리한 뒤 확대'],
];
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  const { d } = T.shell(pptx, { sec: '수평 전개', idx: 7, step: 7 });
  T.title(d, '구조를 둘로 나눈 덕분에,', '*계산식만 갈아끼우면* 옮겨집니다');
  T.lead(d, '배우는 부분은 설비 종류와 상관이 없습니다. 사업소마다 다른 것은 _계산식_ 하나입니다.',
         { lines: 1 });

  /* 그대로 / 갈아끼움 */
  d.zone(G.L, 284, G.W, 148);
  d.vline(640, 306, 104, C.rule, 1);
  d.rect(G.L, 284, 568, 2, C.brass);
  d.rect(640, 284, 568, 2, C.slate);
  d.plab('그대로 가져가는 것', 96, 300, 500, C.brass);
  d.plab('사업소마다 갈아끼우는 것', 664, 300, 500, C.slate);
  KEEP.forEach((s, i) => d.text('·  ' + s, { x: 96, y: 326 + i * 30, w: 500, px: 15.5,
                                             lh: 1.35, bold: true, color: C.ink }));
  SWAP.forEach((s, i) => d.text('·  ' + s, { x: 664, y: 326 + i * 30, w: 500, px: 15.5,
                                             lh: 1.35, bold: true, color: C.slateL }));
  d.text('총 ' + KEEP.length + ' 덩어리', { x: 96, y: 416, w: 500, px: 11.5, lh: 1.2, color: C.dim });
  d.text('바꿀 것은 ' + SWAP.length + ' 덩어리뿐', { x: 664, y: 416, w: 500, px: 11.5,
                                                     lh: 1.2, color: C.dim });

  /* 타임라인 */
  d.zone(G.L, 458, G.W, 166);
  d.plab('전개 순서', 96, 472, 300);
  d.hline(150, 542, 970, C.rule, 1.4);
  PLAN.forEach(([when, what, how], i) => {
    const x = 200 + i * 273, now = i === 0;
    d.text(when, { x: x - 120, y: 500, w: 240, px: 11.5, lh: 1.2, mono: true, bold: true,
                   color: now ? C.brass : C.dim2, align: 'center' });
    d.dot(x, 542, now ? 7 : 5.5, now ? C.brass : C.steel);
    d.text(what, { x: x - 120, y: 558, w: 240, px: 16.5, lh: 1.3, bold: true,
                   color: now ? C.brass : C.ink, align: 'center' });
    d.text(how, { x: x - 124, y: 584, w: 248, px: 12.5, lh: 1.35, color: C.dim, align: 'center' });
  });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '위례에서 검증한 절차 그대로 — *바꿀 것은 계산식 하나*입니다.');
};
