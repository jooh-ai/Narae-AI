/* 슬라이드 4 · 현황 — 정수 하나로 메워 왔다
   BLT 적용값 16회차 실측 (담당자 Base Load 실적표 2026-08 수령분,
   tool/scripts/period_check.py H1_2025 그대로). 평균 +3.69 · 범위 −1 ~ +6.
   결정적 장면: 7.3℃ 와 25.7℃ 에 똑같이 5 — 온도가 18.4℃ 달라도 같은 값. */
'use strict';
module.exports = (pptx, T) => {
  const { C, G } = T;
  const { d } = T.shell(pptx, { sec: '현황', idx: 2, step: 2 });

  T.title(d, '이론값과 실적의 차이를,', '*정수 하나*로 메워 왔습니다');
  T.lead(d, '이론 계산값과 실제 발전량의 차이를 담당자가 판단해 정수 하나로 정하고, _온도와 무관하게_ 그 값을 그대로 적용해 왔습니다.');

  /* 좌 — 종전 절차 */
  d.panel(G.L, 288, 420, null);
  d.plab('종전 절차  ·  엑셀 3개', G.L, 302, 420);
  [['온도별 이론 출력표', 328], ['주간 실적과 대조', 382], ['신고서 작성·제출', 436]]
    .forEach(([s, y], i) => d.chip(s, G.L, y, 250, false));
  [362, 416].forEach(y => d.text('↓', { x: G.L + 14, y, w: 20, px: 14, lh: 1.2, color: C.dim2 }));
  d.txt('가운데 _대조_ 단계에서 보정값이 정해집니다. 계산이 아니라 담당자의 판단이었고, 근거는 문서로 남지 않았습니다.',
        G.L, 486, 420, 3);

  /* 우 — BLT 적용값 16회차 스트립 */
  const BLT = [[12.5, 4], [7.3, 5], [25.7, 5], [16.0, 5], [18.8, 5], [13.7, 5], [23.5, 1], [21.4, 3],
               [20.0, 6], [27.4, 6], [25.5, 5], [28.9, 5], [29.9, 2], [27.6, 2], [31.9, 1], [36.6, -1]];
  const ZX = 516, ZW = 692;
  d.panel(ZX, 288, ZW, null);
  d.plab('담당자가 적용한 보정값  ·  2025 상반기 16회차  ·  단위 MW', ZX, 302, ZW);
  d.zone(ZX, 320, ZW, 104);
  const CW = 660 / 16, X0 = ZX + 16;
  BLT.forEach(([cit, v], i) => {
    const x = X0 + i * CW, hot = (cit === 7.3 || cit === 25.7);
    d.text(String(v), { x, y: 334, w: CW, px: 17, lh: 1.35, mono: true, bold: true,
                        color: hot ? C.red : C.ink, align: 'center' });
    d.text(cit.toFixed(1), { x, y: 372, w: CW, px: 10, lh: 1.3, mono: true,
                             color: hot ? C.red : C.dim2, align: 'center' });
  });
  d.hline(X0, 364, 660, C.rule, 1);
  d.plab('아래 줄은 그 회차의 외기온도 ℃', X0, 392, 400);
  d.sub('*7.3℃ 와 25.7℃ 에 똑같이 5* — 18℃ 차이인데 같은 값', ZX, 438, ZW, 1);

  d.zone(ZX, 484, ZW, 76);
  [['평균', '+3.69', 'MW'], ['범위', '−1 ~ +6', 'MW'], ['적용 온도 폭', '7.3 ~ 36.6', '℃']]
    .forEach(([l, v, u], i) => {
      const x = ZX + 20 + i * 224;
      d.plab(l, x, 496, 200);
      d.bigUnit(v, u, x, 518, 24);
    });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '온도가 달라져도 값이 거의 그대로입니다 — *온도를 보지 않는 값*이었습니다.');
};
