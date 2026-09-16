/* v3-03 · ① 개요 및 추진 배경 — 종전에는 이렇게 했다.
   요소 하나: 엑셀 네 개를 순서대로 돌리던 흐름. 각 칸에 **실물 캡처**가 들어간다.

   말은 최소로. 이 장의 일은 "파일이 넷이었다" 를 눈에 박는 것과, 왜 차이 하나를
   전부에 얹었는지 한 문장으로 밝히는 것 두 가지다. 담당자를 탓하는 자리가
   아니므로 결론은 "그때는 그게 최선이었다" 로 닫는다.

   절차 출처: docs/concept.txt §1. 캡처 판독은 STORY.md §8.                */
'use strict';
const A = require('./assets.js');
const STEP = [
  ['① RiMS 에서 값 가져오기', A.xl1,
   '날짜와 시각을 넣으면 태그 *14개*를 끌어와 한 줄로 정리합니다'],
  ['② 온도별 이론값 만들기', A.xl2,
   '대기압을 넣으면 −20 ~ 40℃ 를 1도 단위로 *60개* 계산합니다'],
  ['③ 차이 하나를 전부에 얹기', A.xl2blt,
   '테스트한 *그 한 점*의 차이를 60개 전부에 똑같이 더합니다'],
  ['④ 온도 프로파일 완성', A.xl3,
   '복사해 붙여 넣으면 이것이 그날의 *입찰값*이 됩니다'],
];
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  const { d } = T.shell(pptx, { sec: '추진 배경', idx: 1, step: 1 });
  T.title(d, '엑셀 네 개를 순서대로 돌렸습니다', null);
  T.lead(d, '테스트가 끝나면 파일을 옮겨 다니며 값을 넘겼습니다. ' +
         '여기에 대기압을 받아 오는 파일이 하나 더 붙습니다.', { y: 176, lines: 1 });

  const BW = 266, GAP = 24;
  STEP.forEach(([name, file, why], i) => {
    const x = G.L + i * (BW + GAP);
    d.zone(x, 236, BW, 250);
    d.text(name, { x: x + 12, y: 248, w: BW - 24, px: 13, lh: 1.3, bold: true,
                   color: C.brass });
    d.imgFit(file, x + 10, 274, BW - 20, 152);
    d.text(why, { x: x + 12, y: 436, w: BW - 24, px: 12, lh: 1.45, lines: 2,
                  color: C.dim });
    if (i < STEP.length - 1) d.arrow(x + BW + 2, 342);
  });

  /* 왜 하나를 전부에 얹었나 — 이유가 없으면 대충 한 것처럼 들린다 */
  d.zone(G.L, 502, G.W, 122);
  d.plab('왜 차이 하나를 전부에 얹었나', 96, 512, 400);
  d.text('테스트는 *그날의 온도 한 점*에서 합니다. 신고는 *61개 온도 전부*입니다.',
         { x: 96, y: 534, w: 700, px: 17, lh: 1.5, lines: 1, color: C.ink });
  d.text('나머지 60개 온도의 차이는 알 방법이 없었습니다. 같은 값을 얹는 것이 ' +
         '그때로서는 가장 안전했습니다.',
         { x: 96, y: 562, w: 700, px: 13.5, lh: 1.5, lines: 2, color: C.dim });
  d.rect(836, 528, 3, 74, C.brass);
  d.text('파일 4개\n옮겨 적는 값 61개\n입력 지점 여러 곳',
         { x: 856, y: 528, w: 330, px: 13.5, lh: 1.7, lines: 3, color: C.body });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '온도별로 알 방법이 없었으니, *그때는 그게 최선*이었습니다.');
};
