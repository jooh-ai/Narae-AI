/* v2-06 · 데이터 분석 및 원인 규명 — 요소 2개: 변수 조합별 성적 표 / 결론.
   요지: 후보 변수를 먼저 세우고, **같은 모델에 변수 조합만 바꿔** 겨뤄서
   '외기 온도 외의 변수를 더 넣으면 예측이 실제로 좋아지는가' 하나만 묻는다.
   답은 아니오였고, 그래서 입력 변수를 외기 온도로 확정한다.

   2026-09-07 전면 재구성 — 종전에는 변수별 부분상관을 3단으로 좁혀 보였다.
   결론은 같았지만 통계 해석을 한 겹씩 더 설명해야 해서, 조합 비교 한 장으로
   바꿨다(부장님 지시). 판단 근거가 '상관계수' 에서 '예측 성능' 으로 바뀐 것이
   오히려 더 직접적이다 — 우리가 쓰는 것이 예측이기 때문이다.

   숫자는 refresh_data → varsel.compare 에서 온다. '외기 온도' 행은 8장 표의
   GP·RBF 값(RMSE 1.678 / MAE 1.301 / R² 0.854)과 **같은 숫자여야** 한다 —
   같은 모델·같은 채점집합이므로, 어긋나면 버그다.                          */
'use strict';
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  const { d } = T.shell(pptx, { sec: '원인 규명', idx: 3, step: 3 });
  const V = D.varsel, R = V.rows, base = R.find(r => r.d === 1), near = V.near;
  const NV = near.vs_base;
  T.title(d, '변수를 더 넣으면 좋아질까 —', '*같은 모델에 조합만 바꿔* 확인했습니다');
  T.lead(d, '보정값에 영향을 줄 수 있는 환경변수로 *외기 온도 · 복수기 진공도 · 대기압 · ' +
         '상대습도* 4개를 후보로 세우고, 온도 외의 변수를 더했을 때 예측이 ' +
         '_실제로_ 좋아지는지 확인했습니다.');

  /* 변수 조합별 성적 — 바뀌는 것은 입력 변수 하나뿐이다 */
  d.zone(G.L, 284, G.W, 206);
  d.plab('같은 모델(GP · RBF 커널) · 같은 조건에서 *변수 조합만* 바꿔 채점  ·  공통 ' +
         base.n + '회', 96, 296, 620);
  d.text('작을수록 좋음 · R² 만 1 에 가까울수록',
         { x: 890, y: 294, w: 294, px: 11.5, lh: 1.2, color: C.dim, align: 'right' });

  const COL = [['RMSE', 470], ['MAE', 590], ['R²', 712], ['AIC', 834]];
  d.plab('모델  ·  입력 변수 조합', 96, 320, 264);
  COL.forEach(([s, xr]) => d.text(s, { x: xr - 80, y: 320, w: 80, px: G.LAB_PX, lh: 1.25,
                                       mono: true, bold: true, color: C.dim2, cs: 1.5,
                                       align: 'right' }));
  d.text('판정', { x: 1104, y: 320, w: 80, px: G.LAB_PX, lh: 1.25, mono: true,
                   bold: true, color: C.dim2, cs: 1.5, align: 'right' });
  d.hline(96, 336, 1088, C.rule, 1);

  R.forEach((r, i) => {
    const y = 344 + i * 22, win = r.d === 1;
    const col = win ? C.brass : C.dim;
    if (win) d.box(88, y - 5, 1104, 25, null, C.brass, 1.4);
    d.text(r.label, { x: 96, y, w: 264, px: 13, lh: 1.25, bold: win,
                      color: win ? C.brass : C.body });
    [r.rmse.toFixed(3), r.mae.toFixed(3), r.r2.toFixed(3), r.aic.toFixed(1)]
      .forEach((s, k) => d.text(s, { x: COL[k][1] - 80, y, w: 80, px: 13, lh: 1.25,
                                     mono: true, bold: win, color: col, align: 'right' }));
    d.text(win ? '★ 최종 선정' : '개선 없음',
           { x: 900, y, w: 284, px: 12.5, lh: 1.25, bold: win,
             color: win ? C.brass : C.dim2, align: 'right' });
  });

  /* 용어 — 네 지표가 처음 나오는 자리다(계획서 §3 규칙 1: 첫 등장에서 한 줄로 풀어 준다) */
  d.text('RMSE 크게 틀린 경우에 벌점을 더 준 평균 오차  ·  MAE 평균 오차  ·  ' +
         'R² 설명력  ·  AIC 적합도와 복잡도를 함께 보는 지표(변수를 늘리면 벌점)',
         { x: 96, y: 456, w: 1088, px: 11, lh: 1.2, color: C.dim2 });
  d.text('커널 점과 점 사이를 어떤 모양으로 이을지 정하는 규칙  ·  ' +
         'LOOCV 한 회를 가리고 나머지로 맞혀보기 — 네 지표 모두 *MW 단위 예측 오차*이고, ' +
         '같은 ' + base.n + '회를 같은 방식으로 쟀습니다.',
         { x: 96, y: 472, w: 1088, px: 11, lh: 1.2, color: C.dim2 });

  /* 결론 — 표의 소수점 차이를 정직하게 짚는다. 여기가 이 장의 핵심이다. */
  d.zone(G.L, 502, G.W, 122);
  d.plab('그래서 무엇을 알았나', 96, 512, 300);
  [['외기 온도를 최종 입력 변수로 선정했습니다',
    '네 지표 중 *셋(RMSE · R² · AIC)에서 온도 단독이 1위*입니다. 온도 외의 변수를 ' +
    '더해도 예측이 좋아지지 않았습니다.'],
   ['가장 근접한 조합도 *구분되지 않습니다*',
    'MAE 만 「' + near.label.replace('외기 온도 + ', '+') + '」가 ' +
    Math.abs(NV.d_mae).toFixed(2) + ' MW 낮은데, 회차별로 짝지어 재면 그 차이가 ' +
    '±' + NV.se.toFixed(2) + ' MW — 우연과 갈리지 않습니다.'],
   ['모델이 *스스로 무시*했습니다',
    '변수마다 따로 길이척도를 줘서 필요 없으면 모델이 버릴 수 있게 뒀는데, 추가 ' +
    '변수는 모두 「영향 없음」 쪽 값이 붙었습니다.']]
    .forEach(([k, v], i) => {
      const x = 96 + i * 368, w = 344;
      d.rect(x, 534, 34, 2, C.brass);
      d.text(k, { x, y: 544, w, px: 14, lh: 1.3, bold: true, color: C.ink });
      d.text(v, { x, y: 570, w, px: 12.5, lh: 1.5, lines: 3, color: C.dim });
    });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '보고 배울 것은 *외기 온도 하나* — 남은 것은 *어떻게 배울지*입니다.');
};
