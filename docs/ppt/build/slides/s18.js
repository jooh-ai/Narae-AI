/* 슬라이드 18 · Q & A
   마지막에 남길 것은 세 수치가 아니라 한 문장이다. 수치는 그 근거로 둔다. */
'use strict';
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  const { d } = T.shell(pptx, {});

  d.text(meta.org, { x: G.L, y: G.SEC_Y, w: 600, px: 12, lh: 1.25, mono: true, color: C.dim2, cs: 1.8 });
  d.text(meta.when, { x: 1008, y: G.SEC_Y, w: 200, px: 12, lh: 1.25, mono: true,
                      color: C.dim2, cs: 1.8, align: 'right' });

  T.title(d, '감사합니다', '*질문 받겠습니다*', { y: 132, w: 700, px: 46 });

  d.sub('사람의 판단 하나였던 보정값을, *데이터가 스스로 갱신하는 모델*로 바꿨습니다.',
        G.L, 300, 700, 2);
  d.txt('이 과제가 바꾼 것은 숫자가 아니라 숫자를 정하는 방법입니다. 같은 구조의 사업소라면 이론만 갈아끼워 그대로 씁니다.',
        G.L, 380, 660, 2);

  /* 근거 3수치 — 표지와 같은 자리, 같은 형식 */
  d.hline(G.L, 470, G.W, C.rule, 1);
  const I = D.impact, K = I.cut;
  [[72,  '예측 오차',      K.mae + '%↓',   I.blanket.mae.toFixed(2) + ' → ' + I.gp.mae.toFixed(2) + ' MW'],
   [306, '기준 미달 회차', K.short + '%↓', I.blanket.short + ' → ' + I.gp.short + ' 건'],
   [540, '과대 신고 누계', K.over + '%↓',  I.blanket.over.toFixed(1) + ' → ' + I.gp.over.toFixed(1) + ' MW']]
    .forEach(([x, l, n, sub]) => {
      d.plab(l, x, 490, 208);
      d.big(n, x, 514, 208, 44);
      d.text(sub, { x, y: 572, w: 208, px: 15, lh: 1.4, mono: true, color: C.ink });
    });
  [280, 514, 748].forEach(x => d.vline(x, 490, 106, C.rule, 1));
  d.plab('검증 방식', 774, 490, 434);
  d.txt('누적 ' + D.n + '회차를 _한 건씩 가리고_ 맞혀본 결과입니다. 시운전 ' +
        D.commission.n + '회차에서 다시 확인했습니다.', 774, 514, 434, 2);

  d.hline(G.L, 634, G.W, C.rule, 1);
  d.text(meta.dept + '  ·  ' + meta.authors.join(' · '),
         { x: G.L, y: G.FOOT_Y, w: 600, px: 12, lh: 1.4, mono: true, color: C.dim, cs: 1.6 });
};
