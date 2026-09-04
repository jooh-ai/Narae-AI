/* v2-11 · 개선 효과 — 요소 2개: 감소율 3수치 / 시운전 회차별 막대.
   정량·정성 두 장을 한 장으로 합치고 정성 효과는 결론 한 줄로 남겼다.    */
'use strict';
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  const { d } = T.shell(pptx, { sec: '효과', idx: 6, step: 6 });
  const I = D.impact, K = I.cut, S = D.commission;
  T.title(d, '일은 간단해지고,', '숫자는 *정확해졌습니다*');
  T.lead(d, '같은 ' + D.n + '회를 종전 방식과 나란히 채점한 결과입니다.', { lines: 1 });

  /* 효과 두 갈래 — 일 처리 / 신고 정확도 */
  d.zone(G.L, 284, G.W, 152);
  d.vline(640, 306, 108, C.rule, 1);
  d.rect(G.L, 284, 568, 2, C.brass);
  d.rect(640, 284, 568, 2, C.brass);

  d.plab('① 일 처리  ·  담당자 업무', 96, 300, 500);
  d.bigUnit('4 → 1', '엑셀 4개 → 도구 1개', 96, 322, 44, C.brass, 15);
  d.txt('순서를 지켜 파일 4개를 돌리던 일이 *날짜·시각 한 번*으로 끝납니다. ' +
        '손으로 옮겨 적던 값 61개는 *0개*.', 96, 388, 520, 2);

  d.plab('② 신고 정확도  ·  실제와 어긋난 정도', 664, 300, 500);
  d.bigUnit(K.mae + '%', '감소', 664, 322, 44, C.brass, 15);
  d.text('평균 ' + I.blanket.mae.toFixed(2) + ' → ' + I.gp.mae.toFixed(2) + ' MW',
         { x: 900, y: 336, w: 284, px: 15, lh: 1.3, mono: true, bold: true, color: C.ink });
  d.txt('실제가 못 미친 횟수 *' + I.blanket.short + ' → ' + I.gp.short + '회*   ·   ' +
        '높게 신고한 양 *' + I.blanket.over.toFixed(1) + ' → ' + I.gp.over.toFixed(1) +
        ' MW*', 664, 388, 520, 2);

  /* 시운전 — walk-forward 재현. [검토 반영] 종전에는 '실측 전에 적어 둔 예측'
     이라고 적었는데 사실이 아니다. trial_log.json 의 pred_corr 가 전부 null 이다.
     실제로 한 것은 각 회차를 그 앞의 데이터만으로 예측하는 것이고(뒤 회차를
     보지 않는다), 이것도 충분히 방어되지만 '미리 적어 뒀다' 와는 다른 말이다. */
  d.zone(G.L, 456, G.W, 168);
  d.plab('시운전 ' + S.n + '회  ·  그 회차 앞의 데이터만으로 예측(walk-forward)  ·  ' +
         '세로 = 실제 − 예측 MW', 96, 470, 700);
  d.text('편차 ' + (S.me >= 0 ? '+' : '−') + Math.abs(S.me).toFixed(3) +
         '  ·  오차 ' + S.mae.toFixed(3) + '  ·  종전 대비 +' +
         Math.round(S.skill * 100) + '%',
         { x: 820, y: 468, w: 364, px: 12.5, lh: 1.3, mono: true, bold: true,
           color: C.brass, align: 'right' });

  const ZERO = 536, PXMW = 20, BW = 46;
  d.hline(140, ZERO, 1000, C.rule, 1);
  [2, -2].forEach(v => d.hline(140, ZERO - v * PXMW, 1000, C.rule2, 1));
  [[2, '+2'], [0, '0'], [-2, '−2']].forEach(([v, s]) => d.text(s,
    { x: 96, y: ZERO - v * PXMW - 7, w: 36, px: 10, lh: 1.3, mono: true,
      color: C.dim2, align: 'right' }));
  S.rows.forEach((r, i) => {
    const x = 158 + i * 110, h = Math.abs(r.diff) * PXMW, up = r.diff >= 0;
    d.rect(x, up ? ZERO - h : ZERO, BW, Math.max(h, 2), up ? C.brass : C.red);
    d.text((r.diff >= 0 ? '+' : '−') + Math.abs(r.diff).toFixed(2),
           { x: x - 14, y: up ? ZERO - h - 17 : ZERO + h + 3, w: BW + 28, px: 10.5, lh: 1.2,
             mono: true, bold: true, color: up ? C.brass : C.red, align: 'center' });
    d.text(r.date.slice(5), { x: x - 14, y: 604, w: BW + 28, px: 10, lh: 1.2,
                              mono: true, color: C.dim2, align: 'center' });
  });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '시간도 줄고 숫자도 맞았습니다 — 그리고 *왜 그 숫자인지 설명*할 수 있게 됐습니다.');
};
