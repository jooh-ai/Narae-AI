/* 슬라이드 3 · 추진 배경 — 틀리면 양쪽으로 손실이 나는 숫자
   방향에 따라 손실의 종류가 다르다는 것이 이 장의 전부다.
     낮게 신고 → 팔 수 있었는데 못 판다 (기회손실)
     높게 신고 → 실제가 못 미친다 = 기준 미달 (페널티)
   두 수치는 실측이다. 겨울 0℃ 4.7 MW (종전 +2.84 vs 실제 +7.50),
   종전 방식 기준 미달 14회차 / 36회차.                                     */
'use strict';
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  const { d } = T.shell(pptx, { sec: '추진 배경', idx: 1, step: 1 });

  T.title(d, '매주 신고하는 숫자입니다,', '틀리면 *양쪽으로 손실*이 납니다');
  T.lead(d, '다음 주에 낼 수 있는 최대 출력을 매주 신고합니다. 그 숫자가 그대로 입찰이 되므로, 실제와 어긋나면 _어긋난 방향에 따라_ 다른 손실이 생깁니다.');

  /* 신고 절차 4단 */
  d.zone(G.L, 288, G.W, 78);
  d.plab('주간 신고 절차', 96, 300, 400);
  [[96, 100, '기상 예보'], [362, 200, '온도별 이론 출력 계산'],
   [728, 130, '보정값 적용'], [1024, 155, '주간 신고 확정']]
    .forEach(([x, w, s], i) => d.chip(s, x, 322, w, i === 2));
  [269, 635, 931].forEach(x => d.arrow(x, 329));

  /* 양방향 손실 — 두 장의 카드 */
  /* 겨울에 낮게 잡힌 폭 = 개선 곡선 − 종전 하나의 값 (가장 추운 기준 온도에서) */
  const FLAT = D.blanket.flat, RBF = D.curves.rbf, T4 = D.curve_t;
  const wGap = RBF[0] - FLAT;
  const CARD = [
    { x: 72,  kind: 'bad', lab: '낮게 신고하면  ·  기회손실',
      sub: '팔 수 있었는데 *못 팝니다*',
      txt: '실제로 낼 수 있는 출력보다 낮게 신고하면 그만큼 입찰에서 빠집니다. 종전 방식은 _겨울에_ 이 방향으로 치우쳤습니다.',
      big: wGap.toFixed(1), unit: 'MW',
      note: '겨울 ' + T4[0] + '℃ 에서 낮게 잡힌 폭\n종전 +' + FLAT.toFixed(2) +
            ' vs 실제 +' + RBF[0].toFixed(2) },
    { x: 652, kind: 'bad', lab: '높게 신고하면  ·  페널티',
      sub: '기준 미달로 *벌점이 걸립니다*',
      txt: '신고값에 실제가 못 미치면 미달입니다. 종전 방식은 _여름에_ 이 방향으로 치우쳤습니다.',
      big: String(D.impact.blanket.short), unit: '회차',
      note: '종전 방식의 기준 미달 회차\n누적 ' + D.n + '회차 가운데' },
  ];
  CARD.forEach(c => {
    d.panel(c.x, 396, 556, c.kind);
    d.plab(c.lab, c.x, 410, 556, C.red);
    d.sub(c.sub, c.x, 432, 556, 2);
    d.txt(c.txt, c.x, 502, 556, 2);
    d.zone(c.x, 566, 556, 54);
    d.bigUnit(c.big, c.unit, c.x + 16, 576, 26, C.red);
    d.text(c.note, { x: c.x + 150, y: 574, w: 390, px: 11.5, lh: 1.5, mono: true, color: C.dim2, lines: 2 });
  });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '어느 쪽으로 틀려도 손실입니다 — 그래서 *정확도가 곧 수익*입니다.');
};
