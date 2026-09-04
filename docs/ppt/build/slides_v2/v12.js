/* v2-12 · 향후 계획 및 수평 전개 — 요소 2개: 학습 곡선 / 전개 순서.
   [검토 반영] '절차 문서화' 를 빼고, 테스트를 계속 쌓아 예측을 고도화한다는
   내용을 넣었다. 그리고 그 주장을 말로만 하지 않고 **데이터로** 보인다.

   학습 곡선은 walk-forward 다 — 각 회차를 그 앞의 회차만으로 예측해 오차를
   구하고, 시간 순 네 구간의 평균을 낸다. 누적 평균을 쓰지 않은 이유: 앞의 큰
   오차가 뒤로 갈수록 희석되어 무조건 내려간다. 그건 나아진 게 아니라 평균의
   성질이다. 구간 평균은 오르내림도 그대로 드러난다 — 실제로 마지막 구간은
   조금 올라갔고, 그것까지 보이는 것이 정직하다.                            */
'use strict';
const PLAN = [
  ['~ 2026.09', '위례 정착',        '누적 회차로 운영 중'],
  ['2026.10 ~', '테스트 누적 · 고도화', '회차마다 다시 학습 — 쌓을수록 오차가 줄어듭니다'],
  ['2027 상반기', '같은 구조 1곳 시범', '이론식만 바꿔 나란히 운전'],
  ['2027 하반기', '수평 전개',        '이론식 부분을 분리한 뒤 확대'],
];
module.exports = (pptx, T, meta, D) => {
  const { C, G, LW } = T;
  const { d } = T.shell(pptx, { sec: '수평 전개', idx: 7, step: 7 });
  const L = D.learning;
  T.title(d, '테스트는 계속 쌓입니다,', '쌓일수록 *예측이 정확해집니다*');
  T.lead(d, '공급가능용량 테스트는 앞으로도 주기적으로 합니다. 회차가 들어올 때마다 ' +
         '_다시 학습_ 하므로, 데이터가 쌓이는 것 자체가 개선입니다.');

  /* ① 학습 곡선 — 주장을 데이터로 */
  d.zone(G.L, 284, G.W, 186);
  d.plab('회차 구간별 예측 오차  ·  단위 MW  ·  각 회차를 그 앞의 회차만으로 예측' +
         '(walk-forward)  ·  낮을수록 좋음', 96, 292, 900);
  d.text('*' + L.first.toFixed(2) + ' → ' + L.last.toFixed(2) + ' MW*  ·  ' + L.cut +
         '% 줄었습니다. 구간마다 오르내림은 있습니다 — 어려운 회차가 몰리면 올라갑니다.',
         { x: 96, y: 310, w: 1088, px: 13, lh: 1.3, color: C.body });
  const B = L.blocks, BASE = 442, PXMW = 92 / Math.max(...B.map(b => b.mae));
  d.hline(150, BASE, 1000, C.rule, LW.grid);
  B.forEach((b, i) => {
    const x = 210 + i * 220, w = 96, h = Math.max(b.mae * PXMW, 2);
    d.rect(x, BASE - h, w, h, i === B.length - 1 ? C.brass : C.brassD);
    d.text(b.mae.toFixed(2), { x: x - 30, y: BASE - h - 20, w: w + 60, px: 16, lh: 1.2,
                               mono: true, bold: true,
                               color: i === B.length - 1 ? C.brass : C.dim, align: 'center' });
    d.text(b.from + ' ~ ' + b.to + '회차', { x: x - 30, y: BASE + 9, w: w + 60, px: 11.5,
                                             lh: 1.2, color: C.dim2, align: 'center' });
    if (i < B.length - 1) d.text('→', { x: x + w + 32, y: BASE - 22, w: 60, px: 15, lh: 1.2,
                                        color: C.dim2, align: 'center' });
  });

  /* ② 전개 순서 */
  d.zone(G.L, 482, G.W, 142);
  d.plab('전개 순서', 96, 492, 300);
  d.hline(150, 556, 970, C.rule, LW.ref);
  PLAN.forEach(([when, what, how], i) => {
    const x = 200 + i * 273, now = i <= 1;
    d.text(when, { x: x - 124, y: 516, w: 248, px: 11.5, lh: 1.2, mono: true, bold: true,
                   color: now ? C.brass : C.dim2, align: 'center' });
    d.dot(x, 556, now ? 6.5 : 5, now ? C.brass : C.steel);
    d.text(what, { x: x - 124, y: 570, w: 248, px: 15.5, lh: 1.3, bold: true,
                   color: now ? C.brass : C.ink, align: 'center' });
    d.text(how, { x: x - 124, y: 592, w: 248, px: 11.5, lh: 1.3, lines: 2, color: C.dim,
                  align: 'center' });
  });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '배우는 부분은 그대로 옮겨집니다 — 사업소마다 바꿀 것은 *이론식 하나*입니다.');
};
