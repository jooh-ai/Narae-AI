/* v3-11 · 마무리 — 인사와 그림 하나.
   그림은 도구가 그린 출력 곡선이다. 흰 점 40개가 곡선을 따라가는 그림 하나가
   이 과제가 한 일 전부다. 요약문을 다시 쓰지 않는다. 앞에서 다 했다.       */
'use strict';
module.exports = (pptx, T, meta, D) => {
  const { C, G, LW } = T;
  const { d } = T.shell(pptx, { topRight: false });
  const R = D.profile.rows;
  /* 우상단은 shell() 이 쓰고 있다. 소속과 일자는 왼쪽 한 줄로 합친다. */
  d.text(meta.org + '   ·   ' + meta.when,
         { x: G.L, y: G.SEC_Y, w: 700, px: 12, lh: 1.25, mono: true,
           color: C.dim2, cs: 1.8 });

  T.title(d, '감사합니다', null, { y: 106, w: 700, px: 56 });
  d.text('시험 ' + D.n + '회가 만든 곡선입니다.',
         { x: G.L, y: 190, w: 900, px: 17, lh: 1.4, color: C.body });

  d.section(G.L, 244, G.W, 316, null, '외기온도별 신고 출력', '단위 MW · 검은 점은 실제 시험');
  const seg = R.filter(r => r.t >= -10 && r.t <= 40);
  const vs = seg.flatMap(r => [r.theory, r.real]);
  const lo = Math.floor(Math.min(...vs) / 10) * 10, hi = Math.ceil(Math.max(...vs) / 10) * 10;
  const X = t => 180 + (t + 10) * 19.8, Y = v => 520 - (v - lo) / (hi - lo) * 220;
  for (let v = lo; v <= hi; v += 25) {
    d.hline(176, Y(v), 1008, C.rule2, 1);
    d.text(String(v), { x: 120, y: Y(v) - 7, w: 46, px: 10.5, lh: 1.2, mono: true,
                        color: C.dim2, align: 'right' });
  }
  [0, 10, 20, 30, 40].forEach(t => d.text(t === 0 ? '0℃' : String(t),
    { x: X(t) - 24, y: 528, w: 48, px: 10.5, lh: 1.2, mono: true, color: C.dim2,
      align: 'center' }));
  for (let i = 0; i < seg.length - 1; i++) {
    d.seg(X(seg[i].t), Y(seg[i].theory), X(seg[i + 1].t), Y(seg[i + 1].theory),
          C.slateL, LW.ref, 'dash');
    d.seg(X(seg[i].t), Y(seg[i].real), X(seg[i + 1].t), Y(seg[i + 1].real), C.brass, LW.main);
  }
  D.scatter.forEach(([t, c]) => {
    if (t < -10 || t > 40) return;
    const row = seg.reduce((a, b) => (Math.abs(b.t - t) < Math.abs(a.t - t) ? b : a));
    d.dot(X(t), Y(row.theory + c), 3.2, C.body);
  });
  d.rect(196, 276, 18, 3, C.slateL);
  d.text('계산값', { x: 222, y: 269, w: 90, px: 12, lh: 1.2, color: C.slateL });
  d.rect(310, 276, 18, 3, C.brass);
  d.text('도구가 신고하는 값', { x: 336, y: 269, w: 200, px: 12, lh: 1.2, color: C.brass });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  d.text(meta.authors.join('   ·   '), { x: G.L, y: G.FOOT_Y, w: 600, px: 14, lh: 1.4,
                                          color: C.dim });
  d.text('위례열병합발전소  ·  공급가능용량 입찰 산정 Tool',
         { x: 708, y: G.FOOT_Y + 2, w: 500, px: 12, lh: 1.4, mono: true, color: C.dim2,
           cs: 1.4, align: 'right' });
};
