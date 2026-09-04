/* v2-02 · 목차 — 이름과 장 번호만. 한 줄 설명은 걷어냈다.               */
'use strict';
/* 본문 페이지 — 슬라이드를 늘리거나 줄이면 여기도 같이 고친다.
   2026-09-05: 가설 검증 장을 없애면서 04번 항목이 3장(07~09)이 되고
   05·06·07 이 한 칸씩 밀렸는데 이 줄이 그대로였다. */
const PAGE = ['04', '05', '06', '07 ~ 09', '10', '11', '12'];
module.exports = (pptx, T) => {
  const { C, G, INDEX } = T;
  const { d } = T.shell(pptx, { sec: '목차' });
  T.title(d, '오늘 말씀드릴 순서입니다', null, { y: 96 });
  T.lead(d, '앞의 세 항목이 _왜_, 뒤의 네 항목이 *무엇을 어떻게 바꿨는지* 입니다.',
         { y: 164, lines: 1 });

  INDEX.forEach((name, i) => {
    const y = 240 + i * 54;
    d.big(String(i + 1).padStart(2, '0'), G.L, y + 4, 56, 30);
    d.sub(name, 148, y + 6, 800, 1);
    d.text(PAGE[i], { x: 1068, y: y + 12, w: 140, px: 14, lh: 1.3,
                      mono: true, color: C.dim2, align: 'right' });
    if (i < 6) d.hline(G.L, y + 46, G.W, C.rule2, 1);
  });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '본문 *10장* · 발표 10분 + Tool 시연 4분');
};
