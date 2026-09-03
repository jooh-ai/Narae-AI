/* v2-16 · Q & A — 표지에서 이미 보인 3수치를 반복하지 않는다.
   마지막에 남길 것은 수치가 아니라 한 문장이다.                          */
'use strict';
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  const { d } = T.shell(pptx, {});
  d.text(meta.org, { x: G.L, y: G.SEC_Y, w: 600, px: 12, lh: 1.25, mono: true, color: C.dim2, cs: 1.8 });
  d.text(meta.when, { x: 1008, y: G.SEC_Y, w: 200, px: 12, lh: 1.25, mono: true,
                      color: C.dim2, cs: 1.8, align: 'right' });

  T.title(d, '감사합니다', '*질문 받겠습니다*', { y: 232, w: 700, px: 52 });
  d.sub('엑셀 4개로 하던 일을 도구 하나로, 감으로 정한 값을 *데이터가 갱신하는 값*으로.',
        G.L, 406, 900, 1);

  d.hline(G.L, 634, G.W, C.rule, 1);
  d.text(meta.dept + '  ·  ' + meta.authors.join(' · '),
         { x: G.L, y: G.FOOT_Y, w: 600, px: 12, lh: 1.4, mono: true, color: C.dim, cs: 1.6 });
};
