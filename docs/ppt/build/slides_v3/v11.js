/* v3-10 · 정착과 수평 전개.
   구획 둘. 쌓일수록 나아진다는 증거(학습 곡선) / 앞으로 할 일.
   마지막 본문 장이므로 여기서 미래를 말한다. 과장하지 않고 이미 그러고 있다는
   것만 보인다.                                                            */
'use strict';
module.exports = (pptx, T, meta, D) => {
  const { C, G, LW } = T;
  const { d } = T.shell(pptx, { name: '향후 계획', idx: 8, step: 8 });
  const L = D.learning, BK = L.blocks;
  T.title(d, '다른 발전소에도 쓰기', null, { px: 33 });
  T.lead(d, '시험은 계속합니다. 회차가 쌓이면 예측은 더 정확해집니다. 이미 그러고 있습니다.',
         { y: 146, lines: 1 });

  /* 구획 1 — 학습 곡선 */
  d.section(G.L, 186, 700, 438, 1, '쌓일수록 나아지고 있습니다',
            '시험 순서대로 앞부터 배워 뒤를 맞혀 본 결과');
  const hi = Math.max(...BK.map(b => b.mae)) * 1.15;
  const BW2 = 128, X0 = 140;
  const BH = v => Math.round(v / hi * 220);
  BK.forEach((b, i) => {
    const x = X0 + i * (BW2 + 38), h = BH(b.mae);
    const y = 520 - h;
    d.rect(x, y, BW2, h, i === 0 ? C.slate : C.brass);
    d.text(b.mae.toFixed(2), { x, y: y - 24, w: BW2, px: 17, lh: 1.2, mono: true,
                               bold: true, color: i === 0 ? C.slateL : C.brass,
                               align: 'center' });
    d.text(b.from + ' ~ ' + b.to + '회', { x, y: 530, w: BW2, px: 12, lh: 1.3,
                                            color: C.dim, align: 'center' });
  });
  d.hline(X0 - 20, 520, 660, C.rule, 1);
  d.text('틀리는 폭  MW', { x: 92, y: 300, w: 46, px: 10.5, lh: 1.3, lines: 2,
                             color: C.dim2, align: 'right' });
  d.text('처음 구간 ' + L.first.toFixed(2) + ' 에서 ' + L.last.toFixed(2) + ' 로 ' +
         L.cut + '% 줄었습니다. 시험이 늘어난 것 말고 바뀐 것은 없습니다.',
         { x: 92, y: 560, w: 660, px: 13, lh: 1.5, lines: 2, color: C.body });
  d.text('마지막 구간이 그 앞보다 조금 올라간 것은 겨울 회차가 적게 섞인 탓입니다. ' +
         '있는 대로 적었습니다.',
         { x: 92, y: 598, w: 660, px: 11.5, lh: 1.3, color: C.dim2 });

  /* 구획 2 — 앞으로 */
  d.section(788, 186, 420, 438, 2, '앞으로 할 일', '');
  [['지금', '위례에 정착', '2주마다 시험하고 그 결과를 도구에 넣습니다. ' +
    '회차가 쌓이는 만큼 곡선이 좋아집니다.'],
   ['다음', '같은 구조 발전소로', '계산식은 손대지 않았으니 그대로 옮겨 쓸 수 있습니다. ' +
    '그 사업소의 시험 결과만 따로 쌓으면 됩니다.'],
   ['그다음', '절차로 굳히기', '시험 결과를 넣고 숫자를 내는 순서를 사업소 표준으로 정리합니다.']]
    .forEach(([when, what, why], i) => {
      const y = 232 + i * 128;
      d.text(when, { x: 808, y, w: 90, px: 11.5, lh: 1.2, mono: true, bold: true,
                     color: C.brass, cs: 1.2 });
      d.text(what, { x: 808, y: y + 20, w: 380, px: 18, lh: 1.3, bold: true, color: C.ink });
      d.text(why, { x: 808, y: y + 48, w: 380, px: 12.5, lh: 1.5, lines: 3, color: C.dim });
      if (i < 2) d.hline(808, y + 108, 380, C.rule2, 1);
    });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '한 번 만들고 끝나는 도구가 아니라, 쓸수록 나아지는 도구입니다.');
};
