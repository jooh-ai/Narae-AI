/* v2-09 · 해결 방안(2) 곡선 비교 ★ — 요소 2개: 2단 곡선 차트 / 차이 한 줄.
   Tool [📈 출력곡선 비교] 탭과 같은 2단 구성이다. 위는 출력 곡선(이론 vs
   모델), 아래는 그 차이를 확대한 곡선 + 실측점. 데이터도 그 탭이 부르는
   profile.build_profile 을 그대로 불러 만든다(refresh_data.profile_cmp).

   왜 2단인가 — 출력은 온도에 따라 100 MW 넘게 움직인다. 그 축에 8 MW 차이를
   얹으면 두 곡선이 겹쳐 보인다. 그래서 위에서 '거의 같아 보인다'를 보이고,
   아래에서 확대해 '온도마다 이만큼 다르다'를 보인다. 이 순서가 설명이다.

   후보 7가지 확대 막대는 걷어냈다 — 1.30 vs 1.31 을 눈으로 보는 장은
   처음 보는 사람에게 아무것도 설명하지 못한다.                              */
'use strict';
module.exports = (pptx, T, meta, D) => {
  const { C, G, LW } = T;
  const { d } = T.shell(pptx, { sec: '곡선 비교', idx: 4, step: 4 });
  const P = D.profile, R = P.rows;
  T.title(d, '겉보기엔 같은 곡선인데,', '확대하면 온도마다 *달랐습니다*');
  T.lead(d, '앞에서 본 그 점들입니다. 이제 _채점으로 고른 곡선_ 이 그 점들을 따라 지나갑니다.',
         { lines: 1 });

  d.zone(G.L, 284, G.W, 268);
  d.plab('Tool [출력곡선 비교] 화면과 같은 곡선  ·  가로 외기온도 ℃', 96, 296, 700);

  const t0 = R[0].t, t1 = R[R.length - 1].t;
  const X = t => 150 + (t - t0) * (1000 / (t1 - t0));

  /* ── 위: 출력 곡선 (MW) — 온도에 따라 100 MW 넘게 움직인다 ── */
  const vs = R.map(r => r.theory).concat(R.map(r => r.real));
  const lo1 = Math.floor(Math.min(...vs) / 20) * 20, hi1 = Math.ceil(Math.max(...vs) / 20) * 20;
  const Y1 = v => 424 - (v - lo1) * (106 / (hi1 - lo1));
  d.text('출력  MW', { x: 150, y: 310, w: 100, px: 10, lh: 1.2, mono: true, color: C.dim2 });
  for (let v = lo1; v <= hi1; v += 40) {
    d.hline(150, Y1(v), 1000, C.rule2, 1);
    d.text(String(v), { x: 96, y: Y1(v) - 6, w: 46, px: 10, lh: 1.2, mono: true,
                        color: C.dim2, align: 'right' });
  }
  for (let i = 0; i < R.length - 1; i++)
    d.seg(X(R[i].t), Y1(R[i].theory), X(R[i + 1].t), Y1(R[i + 1].theory), C.slateL, LW.ref, 'dash');
  for (let i = 0; i < R.length - 1; i++)
    d.seg(X(R[i].t), Y1(R[i].real), X(R[i + 1].t), Y1(R[i + 1].real), C.brass, LW.main);
  [['이론 출력 (IGV 포함 · 보정 없음)', C.slateL, true], ['모델이 만든 곡선', C.brass, false]]
    .forEach(([s, col, dash], i) => {
      const y = 320 + i * 19;
      d.hline(918, y + 7, 26, col, dash ? LW.ref : LW.main, dash ? 'dash' : 'solid');
      d.text(s, { x: 952, y, w: 230, px: 12, lh: 1.3, color: col });
    });
  d.text('두 곡선이 거의 붙어 보입니다 — 아래는 그 차이만 확대한 것입니다',
         { x: 560, y: 400, w: 480, px: 12, lh: 1.3, color: C.dim, align: 'right' });

  /* ── 아래: 차이만 확대 (실제 − 이론값) ── */
  d.hline(G.L, 436, G.W, C.rule, 1);
  const cs = R.map(r => r.corr).concat(D.scatter.map(p => p[1]));
  const lo2 = Math.floor(Math.min(...cs) / 5) * 5, hi2 = Math.ceil(Math.max(...cs) / 5) * 5;
  const Y2 = v => 528 - (v - lo2) * (78 / (hi2 - lo2));
  for (let v = lo2; v <= hi2; v += 5) {
    d.hline(150, Y2(v), 1000, v === 0 ? C.rule : C.rule2, 1);
    d.text((v > 0 ? '+' : '') + v, { x: 96, y: Y2(v) - 6, w: 46, px: 10, lh: 1.2,
                                     mono: true, color: C.dim2, align: 'right' });
  }
  for (let t = t0; t <= t1; t += 10) {
    d.vline(X(t), 528, 5, C.dim2, 1);
    d.text(t === t0 ? t + '℃' : String(t), { x: X(t) - 24, y: 534, w: 48, px: 10, lh: 1.3,
                                             mono: true, color: C.dim2, align: 'center' });
  }
  d.text('차이 = 보정값 (실제 − 이론값 − W)', { x: 150, y: 441, w: 260, px: 11.5,
                                                 lh: 1.2, color: C.dim2 });
  d.dot(402, 447, 3.2, C.ink);
  d.text('점 = 테스트 ' + D.n + '회', { x: 414, y: 441, w: 170, px: 11.5, lh: 1.2,
                                        color: C.ink });
  d.text('위쪽일수록 더 나온 것', { x: 600, y: 441, w: 270, px: 11.5, lh: 1.2,
                                    color: C.brass });
  d.hline(886, 447, 24, C.slateL, LW.ref, 'dash');
  d.text('종전 · 온도 구분 없이 +' + D.blanket.flat.toFixed(1),
         { x: 914, y: 441, w: 236, px: 11.5, lh: 1.2, color: C.slateL });
  d.hline(150, Y2(D.blanket.flat), 1000, C.slateL, LW.ref, 'dash');
  D.scatter.forEach(([t, c]) => d.dot(X(t), Y2(c), 3.2, C.ink));
  for (let i = 0; i < R.length - 1; i++)
    d.seg(X(R[i].t), Y2(R[i].corr), X(R[i + 1].t), Y2(R[i + 1].corr), C.brass, LW.main);

  /* 실측이 있는 온도 범위 안에서 가장 많이 더/덜 나온 곳만 짚는다.
     데이터 밖(양 끝)은 곡선이 평평하게 연장되는 구간이라 거기를 가리키면
     "가장 큰 차이" 를 잘못 짚는다. */
  const IN = R.filter(r => r.t >= D.cit_range[0] && r.t <= D.cit_range[1]);
  const up = IN.reduce((a, b) => (b.corr > a.corr ? b : a));
  const dn = IN.reduce((a, b) => (b.corr < a.corr ? b : a));

  /* 이 장에서 남길 문장 */
  d.zone(G.L, 564, G.W, 60);
  d.text('이론 출력보다 *' + up.t + '℃ 는 ' + up.corr.toFixed(1) + ' MW 더*, *' + dn.t +
         '℃ 는 ' + Math.abs(dn.corr).toFixed(1) + ' MW 덜* 나왔습니다.   ' +
         '종전에는 이 차이를 온도 구분 없이 ~하나의 값 +' + D.blanket.flat.toFixed(1) +
         '~ 로 덮었습니다.',
         { x: 96, y: 576, w: 1088, px: 15, lh: 1.5, lines: 2, color: C.body,
           align: 'center' });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '이 차이를 온도마다 배웁니다 — 방식 7가지를 겨뤄 *가장 잘 맞는 곡선*을 골랐습니다.');
};
