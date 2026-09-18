/* 슬라이드 2 · 목차
   7개 항목은 theme.js 의 INDEX 상수에서 온다. 본문 15장의 머리글도 같은
   상수를 쓰므로, 표현을 바꾸면 목차와 머리글이 함께 바뀐다.               */
'use strict';
/* 오른쪽 한 줄 설명 — 목차 명칭이 길어 폭이 좁다. 20자 안쪽으로 쓴다. */
const ROW = [
  ['매주 신고하는 숫자, 양쪽 손실', '04'],
  ['정수 하나로는 맞출 수 없다', '05 ~ 06'],
  ['가설 4개 중 3개를 기각', '07 ~ 08'],
  ['이론 동결 · 방식 7가지 채점', '09 ~ 11'],
  ['회차가 쌓이면 다시 고른다', '12 ~ 13'],
  ['정량 3지표 · 정성 4관점', '14 ~ 15'],
  ['마일스톤과 수평 전개', '16'],
];

module.exports = (pptx, T) => {
  const { C, G, INDEX } = T;
  const { d } = T.shell(pptx, { sec: '목차' });

  T.title(d, '오늘 말씀드릴 순서입니다', null, { y: 96 });
  T.lead(d, '앞의 세 항목이 _왜 바꿔야 했는지_, 뒤의 네 항목이 *무엇을 어떻게 바꿨고 무엇이 좋아졌는지* 입니다.',
         { y: 160, lines: 1 });

  INDEX.forEach((name, i) => {
    const y = 236 + i * 55;
    d.big(String(i + 1).padStart(2, '0'), G.L, y + 8, 52, 26);
    d.sub(name, 140, y + 10, 600, 1);
    d.text(ROW[i][0], { x: 760, y: y + 15, w: 330, px: 14, lh: 1.4, color: C.body });
    d.text(ROW[i][1], { x: 1108, y: y + 16, w: 100, px: 12, lh: 1.3,
                        mono: true, color: C.dim2, align: 'right' });
    if (i < 6) d.hline(G.L, y + 48, G.W, C.rule2, 1);
  });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '발표 10분 + *Tool 시연 4분* · 오른쪽 숫자는 해당 장입니다.');
};
