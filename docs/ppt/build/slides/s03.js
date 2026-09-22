/* 슬라이드 2 · 한 장 요약
   직책자 발표의 전제 ① — 결론이 앞에 있어야 한다. 이 장만 보고도 답이 보이게.
   세 지표는 계기 눈금 게이지(종전 눈금 → 개선 침)로, 절차는 종전/현재
   두 덩어리로 갈라 색으로도 구분한다.                                        */
'use strict';
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  const { d } = T.shell(pptx, { sec: '한 장 요약' });

  T.title(d, '판단 하나에 기대던 숫자를,', '데이터가 *스스로 갱신합니다*', { w: 1040 });
  T.lead(d, '온도가 달라도 _같은 보정값 하나_ 를 쓰던 방식을 온도별 실적을 학습하는 모델로 바꿨습니다. 같은 데이터로 채점했을 때 *세 지표가 동시에* 좋아졌습니다.',
         { w: 1060 });

  /* ── 세 지표 · 개방 패널 + 계기 눈금 게이지 ────────────────────── */
  /* 게이지 눈금 폭 = 개선 / 종전 × 322px */
  const I = D.impact, GW = 322;
  const bar = (a, b) => Math.max(Math.round(a / b * GW), 6);
  const PANELS = [
    { x: 72,  kind: 'on',  lab: '예측 오차  ·  MW',      now: I.gp.mae.toFixed(2),  was: '← ' + I.blanket.mae.toFixed(2),
      txt: '평균적으로 몇 MW 틀리는가',       fill: bar(I.gp.mae, I.blanket.mae),     wasCol: C.slateL },
    { x: 467, kind: 'bad', lab: '기준 미달 회차  ·  건', now: String(I.gp.short),   was: '← ' + I.blanket.short,
      txt: '실제가 낮아 _벌점_ 이 걸린 회차', fill: bar(I.gp.short, I.blanket.short), wasCol: C.red },
    { x: 862, kind: 'on',  lab: '과대 신고 누계  ·  MW', now: I.gp.over.toFixed(1), was: '← ' + I.blanket.over.toFixed(1),
      txt: '실제보다 높게 신고한 양의 합계',   fill: bar(I.gp.over, I.blanket.over),   wasCol: C.slateL },
  ];
  PANELS.forEach(p => {
    d.panel(p.x, 282, 346, p.kind);
    d.plab(p.lab, p.x, 296, 346);
    const vw = T.textW(p.now, 42) + 2;            // 숫자 박스를 글자 폭에 맞춘다
    d.big(p.now, p.x, 320, vw, 42);
    d.text(p.was, { x: p.x + vw + 16, y: 342, w: 120, px: 19, lh: 1.2, mono: true, color: p.wasCol });
    d.txt(p.txt, p.x, 375, 346, 1);
    /* 게이지 — 데이터니까 홈 면 위에 */
    d.zone(p.x, 412, 346, 48);
    const gx = p.x + 12, gw = 322;
    d.text('개선', { x: gx + p.fill + 6, y: 421, w: 60, px: 10.5, lh: 1.25, mono: true, bold: true, color: C.brass, cs: 1.2 });
    d.text('종전', { x: gx + gw - 66, y: 421, w: 60, px: 10.5, lh: 1.25, mono: true, color: p.wasCol, cs: 1.2, align: 'right' });
    d.hline(gx, 441, gw, C.rule, 1);
    d.rect(gx, 437, p.fill, 8, C.brass);
    d.vline(gx + gw, 433, 16, p.wasCol, 2.6);
  });

  /* ── 종전 / 현재 대비 ──────────────────────────────────────────
     외곽여백(72~1208)에 딱 맞춘 한 덩어리. 세로 룰(x=640)로 반을 갈라
     좌우 544px 대칭. 상단 룰만 좌=슬레이트 / 우=앰버로 갈라 색으로도 구분.  */
  d.rect(G.L, 486, G.W, 130, C.groove);
  d.rect(G.L, 486, 568, 2, C.slate);
  d.rect(640, 486, 568, 2, C.brass);
  d.vline(640, 510, 82, C.rule, 1);
  d.rect(616, 532, 48, 38, C.groove);
  d.text('→', { x: 616, y: 536, w: 48, px: 30, lh: 1.1, color: C.brass, align: 'center' });

  d.plab('종전  ·  사람의 판단', 96, 503, 500, C.slate);
  d.sub('보정값 ~1개~ 를 사람이 정수로', 96, 526, 500, 1, C.slate);
  d.plab('현재  ·  데이터의 학습', 664, 503, 500, C.brass);
  d.sub('온도별 곡선을 *데이터가 갱신*', 664, 526, 500, 1);

  /* 칩은 각 절반의 전폭을 채운다 — 한쪽으로 쏠리지 않게 */
  [[96, 105, '이론값 계산'], [303, 105, '실적과 비교'], [510, 105, '정수로 판단']]
    .forEach(([x, w, s]) => d.chip(s, x, 570, w, false));
  d.arrow(242, 577); d.arrow(449, 577);
  [[664, 95, '자동 취득'], [849, 105, '온도별 학습'], [1044, 140, '최적 방식 재선정']]
    .forEach(([x, w, s]) => d.chip(s, x, 570, w, true));
  d.arrow(794, 577); d.arrow(989, 577);

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '사람이 정하던 값이 아니라, *' + D.n + '회차 실적이 스스로 만들어 내는 값*입니다.');
};
