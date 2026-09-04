/* v2-08 · 해결 방안(2) 커널 7종 채점 — 요소 2개: 7종 3지표 표 / 커널별 보정 곡선.
   요지: 실측점을 그대로 잇거나 온도 구간 평균으로 뭉개지 않는다. 방식 7가지
   (구간평균 · 커널회귀 · GP 커널 5종)를 같은 조건에서 채점해 1위를 데이터가
   지목한다. GP 는 곡선의 길이척도·잡음까지 학습 데이터로 정한다(gp.py — 주변
   우도). 사람이 고르는 것은 커널 하나이고, 그 커널조차 LOOCV 가 고른다.

   전문용어(MAE·RMSE·R²·커널·LOOCV)를 그대로 쓰되 이 장에서 한 번 풀어 준다 —
   계획서 §3 규칙 1.                                                        */
'use strict';
const NAME = {
  'gp:rbf': 'GP · RBF (제곱지수)', 'gp:rq': 'GP · Rational Quadratic',
  'gp:matern52': 'GP · Matérn 5/2', 'gp:matern32': 'GP · Matérn 3/2',
  'gp:exp': 'GP · 지수 (Matérn 1/2)', 'curve': '커널회귀 (거리가중 평균)',
  'bin': '구간평균 (온도 구간별 평균)',
};
module.exports = (pptx, T, meta, D) => {
  const { C, G, LW } = T;
  const { d } = T.shell(pptx, { sec: '모델 선정', idx: 4, step: 4 });
  const M = D.methods, B = D.best, nm = k => NAME[k] || k;
  T.title(d, '눈대중으로 고르지 않았습니다 —', '방식 *7가지를 겨뤄* 곡선을 골랐습니다');
  T.lead(d, '한 회를 가리고 나머지로 맞혀보는 방식(LOOCV)으로 채점했습니다. ' +
         '세 지표 모두 *' + nm(B.key) + '* 가 1위입니다.');

  /* 7종 3지표 */
  d.zone(G.L, 284, G.W, 206);
  d.plab('LOOCV 채점 결과  ·  7가지가 모두 예측 가능한 ' + D.n_score +
         '회 공통 집합  ·  종전(하나의 값)은 MAE ' + D.blanket.mae.toFixed(2) + ' MW',
         96, 296, 780);
  d.text('작을수록 좋음 · R² 는 1 에 가까울수록',
         { x: 890, y: 294, w: 294, px: 11.5, lh: 1.2, color: C.dim, align: 'right' });

  const lo = Math.floor(Math.min(...M.map(m => m.mae)) * 20) / 20;
  const hi = Math.max(...M.map(m => m.mae));
  const BX = v => 340 + (v - lo) / (hi - lo) * 420;
  d.plab('순위', 96, 322, 30);
  d.plab('보정값 산출 방식', 140, 322, 200);
  d.plab('MAE  (MW)  ·  ' + lo.toFixed(2) + ' ~ ' + hi.toFixed(2) + ' 구간 확대', 340, 322, 340);
  d.text('RMSE', { x: 856, y: 322, w: 80, px: G.LAB_PX, lh: 1.25, mono: true, bold: true,
                   color: C.dim2, cs: 1.5, align: 'right' });
  d.text('R²', { x: 976, y: 322, w: 80, px: G.LAB_PX, lh: 1.25, mono: true, bold: true,
                 color: C.dim2, cs: 1.5, align: 'right' });
  d.hline(96, 338, 1088, C.rule, 1);
  M.forEach((m, i) => {
    const y = 344 + i * 18, win = i === 0;
    const col = win ? C.brass : i <= 3 ? C.brassD : i < M.length - 1 ? C.steel : C.slate;
    d.text(String(i + 1), { x: 96, y, w: 30, px: 12.5, lh: 1.2, mono: true, bold: win,
                            color: win ? C.brass : C.dim2, align: 'right' });
    d.text(nm(m.key), { x: 140, y, w: 194, px: 12.5, lh: 1.2, bold: win,
                        color: win ? C.brass : C.body });
    d.rect(340, y + 2, Math.max(BX(m.mae) - 340, 6), 11, col);
    d.text(m.mae.toFixed(3), { x: BX(m.mae) + 8, y, w: 60, px: 12.5, lh: 1.2,
                               mono: true, bold: win, color: win ? C.brass : C.dim });
    d.text(m.rmse.toFixed(3), { x: 856, y, w: 80, px: 12.5, lh: 1.2, mono: true, bold: win,
                                color: win ? C.brass : C.dim, align: 'right' });
    d.text(m.r2.toFixed(3), { x: 976, y, w: 80, px: 12.5, lh: 1.2, mono: true, bold: win,
                              color: win ? C.brass : C.dim, align: 'right' });
  });
  d.text('MAE 평균 오차  ·  RMSE 크게 틀린 경우에 벌점을 더 준 오차  ·  R² 설명력  ·  ' +
         '커널 점과 점 사이를 어떤 모양으로 이을지 정하는 규칙',
         { x: 96, y: 472, w: 1088, px: 11.5, lh: 1.2, color: C.dim2 });

  /* 커널별 보정 곡선 — 커널을 바꾸면 곡선의 성격이 바뀐다 */
  d.zone(G.L, 500, G.W, 124);
  d.plab('커널별 보정 곡선  ·  ' + D.curve_t[0] + ' ~ ' +
         D.curve_t[D.curve_t.length - 1] + '℃  ·  MW', 96, 510, 400);
  const T4 = D.curve_t, KS = Object.keys(D.curves).filter(k => D.curves[k]);
  const all = KS.flatMap(k => D.curves[k]);
  const cl = Math.floor(Math.min(...all) / 2) * 2, ch = Math.ceil(Math.max(...all) / 2) * 2;
  const X = t => 200 + (t - T4[0]) * (500 / (T4[T4.length - 1] - T4[0]));
  const Y = v => 604 - (v - cl) * (74 / (ch - cl));
  [ch, 0, cl].forEach(v => { d.hline(200, Y(v), 500, v === 0 ? C.rule : C.rule2, 1);
    d.text((v > 0 ? '+' : '') + v, { x: 150, y: Y(v) - 6, w: 42, px: 9.5, lh: 1.2,
                                     mono: true, color: C.dim2, align: 'right' }); });
  T4.forEach(t => d.text(t === T4[0] ? t + '℃' : String(t),
    { x: X(t) - 24, y: 608, w: 48, px: 9.5, lh: 1.2, mono: true, color: C.dim2,
      align: 'center' }));
  const WIN = B.key.replace('gp:', '');
  KS.filter(k => k !== WIN).forEach(k => {
    const v = D.curves[k];
    for (let i = 0; i < T4.length - 1; i++)
      d.seg(X(T4[i]), Y(v[i]), X(T4[i + 1]), Y(v[i + 1]), C.steel, LW.aux);
  });
  const w = D.curves[WIN] || D.curves.rbf;
  for (let i = 0; i < T4.length - 1; i++)
    d.seg(X(T4[i]), Y(w[i]), X(T4[i + 1]), Y(w[i + 1]), C.brass, LW.main);

  /* 어디서 갈리는지는 데이터가 고른다 — 손으로 적으면 회차가 쌓일 때 틀어진다 */
  const sp = T4.map((t, i) => {
    const vv = KS.map(k => D.curves[k][i]);
    return { t, hi: Math.max(...vv), lo: Math.min(...vv), gap: Math.max(...vv) - Math.min(...vv) };
  });
  const wide = sp.reduce((a, b) => (b.gap > a.gap ? b : a));
  d.vline(X(wide.t), Y(wide.hi) - 4, (Y(wide.lo) - Y(wide.hi)) + 8, C.red, LW.mark);
  d.text('커널을 바꾸면 곡선이 갈립니다 — 가장 벌어지는 곳은 *' + wide.t + '℃, ' +
         wide.gap.toFixed(2) + ' MW*.  눈으로는 고를 수 없어서 *위 표로 채점*했습니다.',
         { x: 740, y: 540, w: 444, px: 13, lh: 1.5, lines: 3, color: C.body });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '곡선의 성격(길이척도·잡음)은 *데이터가 학습*하고, 커널은 *채점으로* 골랐습니다.');
};
