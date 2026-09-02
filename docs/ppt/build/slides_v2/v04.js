/* v2-04 · 개요 및 추진 배경 — 요소 2개: 일 처리 절차(엑셀 4개 → 도구 1개) /
   신고 숫자의 양방향 손실. 이 과제의 목적이 둘이었다는 것을 첫 장에서 못박는다.
   근거: docs/concept.txt §2~3 — "4개의 엑셀 파일로 분산화되어 일 처리가
   단조롭지 않다", "날짜 시간만 입력하면 최종 온도 profile 파일을 생성".      */
'use strict';
const OLD = [
  ['대기압 모으기', '외부 사이트 크롤링'],
  ['테스트 결과 계산', '날짜·시각 넣고 RiMS 조회'],
  ['온도별 출력 계산', '−20~40℃ 61개 값'],
  ['프로파일 완성', '61개 값 복사·붙여넣기'],
];
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  const { d } = T.shell(pptx, { sec: '왜 하는가', idx: 1, step: 1 });
  T.title(d, '손이 많이 갔고,', '틀리면 *양쪽으로 손실*이었습니다');
  T.lead(d, '이 과제는 두 가지를 고쳤습니다 — _일 처리 방식_ 과 _신고하는 숫자_.',
         { lines: 1 });

  /* ① 일 처리 — 엑셀 4개를 순서대로 → 도구 하나 */
  d.zone(G.L, 284, G.W, 160);
  d.plab('① 일 처리  ·  온도 프로파일(온도별 신고값 표) 만드는 절차', 96, 298, 700);
  OLD.forEach(([k, v], i) => {
    const x = 96 + i * 222;
    d.box(x, 320, 196, 52, C.ground, C.rule, 1);
    d.text(k, { x: x + 12, y: 328, w: 172, px: 14, lh: 1.25, bold: true, color: C.slateL });
    d.text(v, { x: x + 12, y: 348, w: 172, px: 10.5, lh: 1.2, color: C.dim2 });
    if (i < 3) d.text('→', { x: x + 198, y: 337, w: 24, px: 15, lh: 1.2,
                             color: C.dim2, align: 'center' });
  });
  d.text('엑셀 4개', { x: 984, y: 330, w: 200, px: 15, lh: 1.3, bold: true, color: C.slateL });
  d.text('순서를 지켜 하나씩', { x: 984, y: 350, w: 200, px: 10.5, lh: 1.2, color: C.dim2 });

  d.box(96, 386, 862, 42, C.ground, C.brass, 1.4);
  d.text('*날짜·시각만 입력* → 실행 → 온도 프로파일이 바로 나옵니다',
         { x: 112, y: 397, w: 830, px: 16, lh: 1.3, bold: true, color: C.ink });
  d.text('도구 1개', { x: 984, y: 390, w: 200, px: 15, lh: 1.3, bold: true, color: C.brass });
  d.text('옮겨 적는 값 0개', { x: 984, y: 410, w: 200, px: 10.5, lh: 1.2, color: C.dim });

  /* ② 신고하는 숫자 — 어느 쪽으로 틀려도 손실 */
  const B = D.impact.blanket;
  d.zone(G.L, 466, G.W, 158);
  d.plab('② 신고하는 숫자  ·  다음 주에 낼 수 있는 최대 출력을 매주 신고한다', 96, 480, 700);
  d.text('실제 발전 능력', { x: 540, y: 502, w: 200, px: 14, lh: 1.3,
                             bold: true, color: C.ink, align: 'center' });
  d.vline(640, 524, 30, C.ink, 2);
  d.hline(200, 556, 400, C.slateL, 2.4);
  d.hline(680, 556, 400, C.red, 2.4);
  d.text('◀', { x: 186, y: 547, w: 20, px: 12, lh: 1.1, color: C.slateL });
  d.text('▶', { x: 1074, y: 547, w: 20, px: 12, lh: 1.1, color: C.red });
  d.sub('낮게 신고하면', 200, 518, 300, 1, C.slateL);
  d.text('높게 신고하면', { x: 780, y: 518, w: 300, px: G.SUB_PX, lh: G.SUB_LH,
                            bold: true, color: C.red, align: 'right' });
  d.txt('팔 수 있었는데 못 팝니다   ·   종전 누계 ' + B.opp.toFixed(1) + ' MW',
        200, 570, 420, 1);
  d.text('실제가 못 미쳐 벌점입니다   ·   종전 ' + D.n + '회 중 ' + B.short + '회',
         { x: 660, y: 570, w: 420, px: G.TXT_PX, lh: G.TXT_LH, color: C.body, align: 'right' });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '*일은 간단하게*, *숫자는 정확하게* — 이 두 가지가 목적이었습니다.');
};
