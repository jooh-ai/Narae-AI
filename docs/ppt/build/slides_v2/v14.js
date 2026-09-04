/* v2-14 · 마무리 — 요소 2개: 인사 / 이 과제를 한 장에 담은 그림.
   [검토 반영] '엑셀 4개로 하던…' 요약문과 '질문 받겠습니다' 를 뺐다. 앞에서
   이미 두 번 한 말이고, 마지막 장에서 또 하면 힘이 빠진다.

   남길 그림으로 출력 곡선을 골랐다 — 표지는 '보정값' 곡선(우리가 배운 것)이고
   여기는 '출력' 곡선(그래서 신고하는 값)이다. 같은 데이터의 다른 얼굴이라
   반복으로 읽히지 않고, 실측점 40개가 곡선을 따라가는 그림 하나가 이 과제가
   한 일 전부다.                                                            */
'use strict';
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  const { d } = T.shell(pptx, {});
  const P = D.profile, R = P.rows;
  d.text(meta.org, { x: G.L, y: G.SEC_Y, w: 600, px: 12, lh: 1.25, mono: true,
                     color: C.dim2, cs: 1.8 });
  d.text(meta.when, { x: 1008, y: G.SEC_Y, w: 200, px: 12, lh: 1.25, mono: true,
                      color: C.dim2, cs: 1.8, align: 'right' });

  T.title(d, '감사합니다', null, { y: 104, w: 700, px: 58 });
  d.sub('매주 신고하는 숫자가, 이제 *' + D.n + '회 실적 위에서* 정해집니다.',
        G.L, 186, 900, 1);

  /* 이 과제를 한 장에 — 이론값 곡선과 모델 곡선, 그리고 실측 40회 */
  d.zone(G.L, 250, G.W, 300);
  d.plab('외기온도별 출력  ·  단위 MW  ·  누적 ' + D.n + '회 실적으로 학습한 곡선',
         96, 262, 700);
  const t0 = R[0].t, t1 = R[R.length - 1].t;
  const vs = R.map(r => r.theory).concat(R.map(r => r.real));
  const lo = Math.floor(Math.min(...vs) / 20) * 20 - 5;
  const hi = Math.ceil(Math.max(...vs) / 20) * 20 + 5;
  const X = t => 150 + (t - t0) * (1000 / (t1 - t0));
  const Y = v => 508 - (v - lo) * (222 / (hi - lo));
  for (let v = lo + 5; v <= hi; v += 20) {
    d.hline(150, Y(v), 1000, C.rule2, 1);
    d.text(String(v), { x: 96, y: Y(v) - 7, w: 46, px: 10, lh: 1.3, mono: true,
                        color: C.dim2, align: 'right' });
  }
  d.hline(150, 508, 1000, C.rule, 1);
  for (let t = t0; t <= t1; t += 10) {
    d.vline(X(t), 508, 5, C.dim2, 1);
    d.text(t === t0 ? t + '℃' : String(t), { x: X(t) - 24, y: 516, w: 48, px: 10,
      lh: 1.3, mono: true, color: C.dim2, align: 'center' });
  }
  for (let i = 0; i < R.length - 1; i++)
    d.seg(X(R[i].t), Y(R[i].theory), X(R[i + 1].t), Y(R[i + 1].theory), C.slateL, 2.0, 'dash');
  for (let i = 0; i < R.length - 1; i++)
    d.seg(X(R[i].t), Y(R[i].real), X(R[i + 1].t), Y(R[i + 1].real), C.brass, 3.0);
  /* 실측점은 그 회차의 이론값 위에 그 회차의 차이를 얹어 찍는다 */
  const th = {}; R.forEach(r => { th[r.t] = r.theory; });
  D.scatter.forEach(([t, c]) => {
    const k = Math.max(t0, Math.min(t1, Math.round(t / 2) * 2));
    d.dot(X(t), Y(th[k] + c), 3.4, C.ink);
  });
  [[700, C.slateL, '이론값 (보정 없음)', true], [930, C.brass, '모델이 만든 곡선', false]]
    .forEach(([x, col, s, dash]) => {
      d.hline(x, 285, 24, col, dash ? 2.0 : 3.0, dash ? 'dash' : 'solid');
      d.text(s, { x: x + 32, y: 278, w: 200, px: 12, lh: 1.3, color: col });
    });
  d.dot(706, 305, 3.4, C.ink);
  d.text('실제 테스트 ' + D.n + '회', { x: 720, y: 298, w: 200, px: 12, lh: 1.3,
                                        color: C.ink });

  d.text('사람이 정하던 값이 아니라, 데이터가 만들어 내는 값입니다.',
         { x: G.L, y: 568, w: G.W, px: 15, lh: 1.4, color: C.dim, align: 'center' });

  d.hline(G.L, 634, G.W, C.rule, 1);
  d.text(meta.dept + '  ·  ' + meta.authors.join(' · '),
         { x: G.L, y: G.FOOT_Y, w: 600, px: 12, lh: 1.4, mono: true, color: C.dim, cs: 1.6 });
};
