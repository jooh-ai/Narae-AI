/* 슬라이드 10 · 커널 7종 채점 ★핵심 3장
   계획서 §6 커널 7종 LOOCV · 커널별 보정곡선 실측 그대로.

   [정정] 목업과 계획서 §6 주석은 '저온·고온 끝에서 갈린다' 고 적었으나
   실측 곡선표로 검산하면 반대다 — 0℃ 0.11 / 10℃ 0.30 / 20℃ 0.38 / 30℃ 0.10.
   양 끝은 거의 겹치고 가운데(10~20℃)가 가장 벌어진다. 그 값으로 그린다.    */
'use strict';
/* 화면에 쓰는 짧은 이름 — 도구의 정식 라벨을 쉬운 말로 줄인 것뿐이다.
   새 방법이 생기면 여기 없어도 정식 라벨로 그려진다. */
const NAME = {
  'gp:rbf': 'GP · RBF', 'gp:rq': 'Rational Quadratic',
  'gp:matern52': 'Matérn 5/2', 'gp:matern32': 'Matérn 3/2',
  'gp:exp': '지수형', 'curve': '거리가중 평균', 'bin': '온도구간 평균',
};

module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  const { d } = T.shell(pptx, { sec: '모델 개발', idx: 4, step: 4 });

  T.title(d, '잇는 방식 7가지를 똑같은 조건에서 겨뤄', '*가장 잘 맞히는 하나*를 골랐습니다');
  const M = D.methods, BEST = D.best;
  T.lead(d, '정답을 _한 건씩 가리고 나머지로 맞혀보는 방식_ 으로 ' + D.n + '번 채점했습니다. *' +
         (NAME[BEST.key] || BEST.label) + '* 가 평균 오차·큰 오차·설명력 세 지표 모두 1위였습니다.');

  /* ── 좌: 종전 대비 + 후보 7가지 ────────────────────────────── */
  d.panel(G.L, 284, 660, null);
  d.plab('평균 오차  ·  단위 MW  ·  낮을수록 좋음', G.L, 298, 660);

  d.zone(G.L, 322, 660, 106);
  const SC = 560 / D.blanket.mae;              // 종전 막대가 560 px 이 되게
  d.text('종전 · 하나의 값', { x: 88, y: 336, w: 200, px: 11.5, lh: 1.3, mono: true, bold: true, color: C.slateL });
  d.rect(88, 354, D.blanket.mae * SC, 15, C.slate);
  d.text(D.blanket.mae.toFixed(2), { x: 660, y: 350, w: 70, px: 18, lh: 1.2, mono: true, bold: true, color: C.slateL });
  d.text('개선 · ' + (NAME[BEST.key] || BEST.label), { x: 88, y: 380, w: 196, px: 11.5, lh: 1.3, mono: true, bold: true, color: C.brass });
  d.rect(88, 398, BEST.mae * SC, 15, C.brass);
  d.text(BEST.mae.toFixed(2), { x: 88 + BEST.mae * SC + 12, y: 393, w: 90, px: 25, lh: 1.2, mono: true, bold: true, color: C.brass });

  /* 확대 구간은 데이터가 정한다 — 최저값을 0.05 단위로 내림, 최고 막대가 600px */
  const lo = Math.floor(Math.min(...M.map(m => m.mae)) * 20) / 20;
  const hiV = Math.max(...M.map(m => m.mae));
  const BX = v => 260 + (v - lo) / (hiV - lo) * 340;
  const TICK = [];
  for (let v = lo; v <= hiV + 1e-9; v += 0.05) TICK.push(Math.round(v * 100) / 100);
  d.plab('후보 ' + M.length + '가지 정밀 비교  ·  ' + lo.toFixed(2) + ' ~ ' +
         (TICK[TICK.length - 1] + 0.05).toFixed(2) + ' 구간만 확대', G.L, 442, 660);
  TICK.forEach(v => d.vline(BX(v), 462, 140, C.rule2, 1));
  M.forEach((m, i) => {
    const y = 466 + i * 20, win = i === 0;
    const col = win ? C.brass : i <= 3 ? C.brassD : i < M.length - 1 ? C.steel : C.slate;
    d.text(NAME[m.key] || m.label, { x: G.L, y: y - 1, w: 182, px: 12.5, lh: 1.3, bold: win,
                                     color: win ? C.brass : C.dim });
    d.rect(260, y, Math.max(BX(m.mae) - 260, 8), 13, col);
    d.text(m.mae.toFixed(3), { x: BX(m.mae) + 8, y: y - 1, w: 60, px: win ? 13.5 : 12.5,
                               lh: 1.3, mono: true, bold: win, color: win ? C.brass : C.dim });
  });
  TICK.forEach(v => d.text(v.toFixed(2),
    { x: BX(v) - 24, y: 608, w: 48, px: 9.5, lh: 1.3, mono: true, color: C.dim2, align: 'center' }));

  /* ── 우: 방식별 보정 곡선 ──────────────────────────────────── */
  d.panel(772, 284, 436, 'on');
  d.plab('방식별 보정 곡선  ·  0 ~ 30℃  ·  MW', 772, 298, 436);
  d.zone(772, 322, 436, 216);
  const T4 = D.curve_t, KS = Object.keys(D.curves).filter(k => D.curves[k]);
  const X = t => 824 + t * (356 / (T4[T4.length - 1] - T4[0])), Y = c => 430 - c * 10;
  [8, 0, -4].forEach(v => d.hline(816, Y(v), 372, v === 0 ? C.rule : C.rule2, 1));
  [[8, '+8'], [0, '0'], [-4, '−4']].forEach(([v, s]) => d.text(s,
    { x: 788, y: Y(v) - 8, w: 26, px: 9.5, lh: 1.3, mono: true, color: C.dim2, align: 'right' }));
  T4.forEach((t, i) => d.text(i === 0 ? t + '℃' : String(t),
    { x: X(t) - 24, y: 486, w: 48, px: 9.5, lh: 1.3, mono: true, color: C.dim2, align: 'center' }));

  KS.filter(k => k !== BEST.key.replace('gp:', '')).forEach(k => {
    const v = D.curves[k];
    for (let i = 0; i < T4.length - 1; i++) d.seg(X(T4[i]), Y(v[i]), X(T4[i + 1]), Y(v[i + 1]), C.steel, 1.5);
  });
  const r = D.curves[BEST.key.replace('gp:', '')] || D.curves.rbf;
  for (let i = 0; i < T4.length - 1; i++) d.seg(X(T4[i]), Y(r[i]), X(T4[i + 1]), Y(r[i + 1]), C.brass, 2.6);

  /* 어디서 갈리는지도 데이터가 고른다 — 온도마다 방식 간 최대-최소 폭을 재서
     가장 넓은 곳에 괄호를 세운다. (손으로 적으면 데이터가 바뀔 때 틀어진다) */
  const spread = T4.map((t, i) => {
    const vs = KS.map(k => D.curves[k][i]);
    return { t, hi: Math.max(...vs), lo: Math.min(...vs), gap: Math.max(...vs) - Math.min(...vs) };
  });
  const wide = spread.reduce((a, b) => (b.gap > a.gap ? b : a));
  const narrow = spread.reduce((a, b) => (b.gap < a.gap ? b : a));
  d.vline(X(wide.t), Y(wide.hi) - 4, (wide.hi - wide.lo) * 10 + 8, C.red, 1.6);
  d.hline(X(wide.t) - 6, Y(wide.hi) - 4, 12, C.red, 1.6);
  d.hline(X(wide.t) - 6, Y(wide.lo) + 4, 12, C.red, 1.6);
  d.text('여기서 ' + wide.gap.toFixed(2) + ' 갈림',
         { x: X(wide.t) + 10, y: Y((wide.hi + wide.lo) / 2) - 8, w: 130, px: 10.5, lh: 1.3, color: C.red });
  d.text('가장 좁은 곳 ' + narrow.gap.toFixed(2),
         { x: 1060, y: Y(-3.6), w: 128, px: 10.5, lh: 1.3, color: C.dim2, align: 'right' });

  const mid = wide.t !== T4[0] && wide.t !== T4[T4.length - 1];
  d.sub(mid ? '*가운데에서* 갈립니다' : '*' + wide.t + '℃ 에서* 갈립니다', 772, 552, 436, 1);
  d.txt(T4[0] + '℃ 와 ' + T4[T4.length - 1] + '℃ 는 어느 방식이나 거의 같고, ' + wide.t +
        '℃ 부근에서 벌어집니다. 눈으로는 고를 수 없습니다.', 772, 590, 436, 2);

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '방식을 *감으로 정하지 않았습니다* — 같은 조건에서 채점해 1위를 데이터가 지목했습니다.');
};
