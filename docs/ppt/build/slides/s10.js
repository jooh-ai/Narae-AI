/* 슬라이드 9 · 데이터 부족을 어떻게 넘었나
   구간별 건수는 계획서 §6 실측. 20~25℃ 가 1건 — 가장 빈약한 구간을 숨기지 않고
   먼저 보여준 뒤, 그래서 검증 방식을 어떻게 짰는지로 넘어간다.              */
'use strict';
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  const { d } = T.shell(pptx, { sec: '모델 개발', idx: 4, step: 4 });

  T.title(d, '데이터가 36건뿐이라는 제약을,', '*검증 설계*로 넘었습니다');
  T.lead(d, '온도 구간마다 건수가 고르지 않습니다. 가장 빈약한 구간은 _1건_ 입니다. 적은 데이터로 과신하지 않도록 검증 방식을 먼저 정했습니다.');

  /* 좌 — 구간별 건수 */
  d.panel(G.L, 288, 596, 'bad');
  d.plab('온도 구간별 회차 수  ·  누적 ' + D.n + '회차', G.L, 302, 596);
  d.zone(G.L, 322, 596, 250);
  const BINS = D.bins.map(b => [b.label, b.n]);
  const thinN = Math.min(...BINS.map(b => b[1]));
  const SC = 341 / Math.max(...BINS.map(b => b[1]));    // 최대 막대 341 px
  BINS.forEach(([l, n], i) => {
    const y = 340 + i * 32, thin = n === thinN;
    d.text(l, { x: G.L + 16, y: y + 2, w: 92, px: 12.5, lh: 1.3, mono: true,
                color: thin ? C.red : C.dim });
    d.rect(G.L + 120, y, n * SC, 18, thin ? C.red : C.slate);
    d.text(String(n) + '건', { x: G.L + 128 + n * SC, y: y + 2, w: 60, px: 13, lh: 1.2,
                               mono: true, bold: true, color: thin ? C.red : C.body });
  });
  d.txt('_' + BINS.find(b => b[1] === thinN)[0] + ' 구간은 ' + thinN +
        '건_ 입니다. 이 구간을 다른 구간과 같은 무게로 믿으면 안 됩니다.', G.L, 584, 596, 2);

  /* 우 — 검증 설계 3단 */
  d.panel(692, 288, 516, 'on');
  d.plab('그래서 이렇게 검증했습니다', 692, 302, 516);
  [['한 건씩 가리고 맞혀보기',
    '정답 하나를 가리고 나머지 35건으로 맞혀봅니다. 36번 반복하니 모의고사와 같습니다.'],
   ['잇는 방식을 여럿 비교',
    '한 방식만 써서 잘 나왔다고 하지 않습니다. 7가지를 같은 자리에서 채점합니다.'],
   ['온도대별로 골고루 나눠 뽑기',
    '한쪽 온도대가 통째로 빠지면 채점이 왜곡됩니다. 구간마다 섞어 나눕니다.']]
    .forEach(([k, v], i) => {
      const y = 322 + i * 102;
      d.zone(692, y, 516, 88);
      d.big(String(i + 1), 708, y + 14, 40, 26, C.brass);
      d.sub(k, 748, y + 14, 444, 1);
      d.txt(v, 748, y + 46, 444, 2);
    });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '데이터가 적을 때 필요한 것은 더 좋은 수식이 아니라 *더 엄한 채점*입니다.');
};
