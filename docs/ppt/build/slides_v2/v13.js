/* v2-13 · Q & A — 마지막에 남길 것은 세 수치가 아니라 한 문장이다. */
'use strict';
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  const { d } = T.shell(pptx, {});
  d.text(meta.org, { x: G.L, y: G.SEC_Y, w: 600, px: 12, lh: 1.25, mono: true, color: C.dim2, cs: 1.8 });
  d.text(meta.when, { x: 1008, y: G.SEC_Y, w: 200, px: 12, lh: 1.25, mono: true,
                      color: C.dim2, cs: 1.8, align: 'right' });

  T.title(d, '감사합니다', '*질문 받겠습니다*', { y: 148, w: 700, px: 46 });
  d.sub('엑셀 4개로 하던 일을 도구 하나로, 감으로 정한 값을 ' +
        '*데이터가 스스로 갱신하는 값*으로 바꿨습니다.', G.L, 322, 700, 2);

  /* 근거 3수치 — 표지와 같은 형식 */
  d.hline(G.L, 440, G.W, C.rule, 1);
  const I = D.impact, K = I.cut;
  [[72,  '신고값이 실제와 어긋난 정도', K.mae,
    I.blanket.mae.toFixed(2) + ' → ' + I.gp.mae.toFixed(2) + ' MW'],
   [420, '실제가 신고값에 못 미친 횟수', K.short,
    I.blanket.short + ' → ' + I.gp.short + ' 회'],
   [768, '실제보다 높게 신고한 양',     K.over,
    I.blanket.over.toFixed(1) + ' → ' + I.gp.over.toFixed(1) + ' MW']]
    .forEach(([x, l, pct, sub]) => {
      d.plab(l, x, 464, 300);
      d.big(pct + '%↓', x, 488, 220, 54);
      d.text(sub, { x, y: 558, w: 300, px: 16, lh: 1.4, mono: true, color: C.ink });
    });
  [396, 744].forEach(x => d.vline(x, 464, 116, C.rule, 1));
  d.text('한 회를 일부러 가려 놓고 나머지로 그 회를 맞혀 보는 방식으로 ' + D.n +
         '번 채점하고, 시운전 ' + D.commission.n + '회에서 다시 확인했습니다.',
         { x: G.L, y: 596, w: G.W, px: 13.5, lh: 1.4, color: C.dim });

  d.hline(G.L, 634, G.W, C.rule, 1);
  d.text(meta.dept + '  ·  ' + meta.authors.join(' · '),
         { x: G.L, y: G.FOOT_Y, w: 600, px: 12, lh: 1.4, mono: true, color: C.dim, cs: 1.6 });
};
