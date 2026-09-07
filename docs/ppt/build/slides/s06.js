/* 슬라이드 5 · 문제 정의 — 하나로는 맞출 수 없다 ★핵심 3장
   실측 36건 (tool/wirye_capacity/data/measurements_seed.json) 전부를 온도 축에
   찍는다. 값이 흩어진 것이 아니라 기울기가 있다는 것이 요점이다.
   수평 점선 = 종전의 일괄 baseline +2.84 (36건 평균 = 최소제곱 최적 상수).
   붉게 표시한 4건은 |보정값 − 2.84| 가 가장 큰 회차 — 코드가 직접 고른다.   */
'use strict';
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  const { d } = T.shell(pptx, { sec: '문제 정의', idx: 2, step: 2 });
  const PT = D.scatter, FLAT = D.blanket.flat;
  const sign = v => (v >= 0 ? '+' : '−') + Math.abs(v).toFixed(1);

  T.title(d, '하나로는 맞출 수 없습니다 —',
          '온도에 따라 *' + sign(D.corr_range[0]) + ' 에서 ' + sign(D.corr_range[1]) + ' 까지* 갈립니다');
  T.lead(d, D.n + '회차의 실제 보정값을 온도 축에 찍었습니다. 값이 흩어진 것이 아닙니다. _한 방향으로 내려가는 기울기_ 가 있습니다.');

  /* ── 산점도 ─────────────────────────────────────────────────── */
  d.zone(G.L, 284, 760, 336);
  d.plab('회차별 실제 보정값  ·  누적 ' + D.n + '회차  ·  가로 외기온도 ℃ / 세로 MW', 88, 298, 700);
  const X = t => 122 + (t + 2) * 17.795;
  const Y = c => 330 + (14 - c) * 11.5;

  [12, 8, 4, -4].forEach(v => d.hline(122, Y(v), 694, C.rule2, 1));
  d.hline(122, Y(0), 694, C.rule, 1);
  d.vline(122, Y(14), 230, C.rule, 1);
  [12, 8, 4, 0, -4].forEach(v => d.text((v > 0 ? '+' : '') + v,
    { x: 84, y: Y(v) - 8, w: 32, px: 10, lh: 1.3, mono: true, color: C.dim2, align: 'right' }));
  [0, 10, 20, 30].forEach(t => {
    d.vline(X(t), 560, 5, C.dim2, 1);
    d.text(t === 0 ? '0℃' : String(t), { x: X(t) - 24, y: 568, w: 48, px: 10, lh: 1.3,
                                          mono: true, color: C.dim2, align: 'center' });
  });

  /* 종전 — 하나의 값 */
  d.hline(122, Y(FLAT), 694, C.slateL, 2.6, 'dash');
  d.text('종전 · 하나의 값 +' + FLAT.toFixed(2), { x: 620, y: Y(FLAT) - 22, w: 196, px: 11.5,
                                     lh: 1.3, mono: true, bold: true, color: C.slateL, align: 'right' });

  /* 실측 전 회차 — 오차 상위 회차만 붉게. 어느 회차인지도 데이터가 고른다 */
  const hotCit = D.blanket.worst.map(w => w.cit);
  PT.forEach(([t, c]) => {
    const hot = hotCit.indexOf(t) >= 0;
    d.dot(X(t), Y(c), hot ? 5 : 3.6, hot ? C.red : C.body);
  });
  d.text('추울수록 크게 더해야 하고', { x: 150, y: 344, w: 250, px: 12.5, lh: 1.4, color: C.dim });
  d.text('더울수록 빼야 합니다', { x: 596, y: 512, w: 220, px: 12.5, lh: 1.4, color: C.dim, align: 'right' });

  /* ── 오차 상위 4건 ──────────────────────────────────────────── */
  const WORST = D.blanket.worst.map(w => [w.date.slice(2), w.err]);
  const SC = 104 / Math.max(...WORST.map(w => Math.abs(w[1])));   // 최대 막대 104 px
  d.panel(852, 284, 356, 'bad');
  d.plab('종전 방식의 오차 상위 ' + WORST.length + '회차  ·  MW', 852, 298, 356);
  /* 좌우 발산 대신 한 방향 막대 — 발산으로 그리면 양수 라벨이 슬라이드 밖
     (1226px)까지 나간다. 방향은 색과 라벨로 구분한다. */
  d.zone(852, 316, 356, 188);
  WORST.forEach(([dt, e], i) => {
      const y = 332 + i * 38, low = e < 0, col = low ? C.slate : C.red;
      d.text(dt, { x: 868, y: y + 1, w: 78, px: 11.5, lh: 1.3, mono: true, color: C.dim });
      d.text(low ? '낮게' : '높게', { x: 952, y: y + 1, w: 56, px: 12, lh: 1.3,
                                      bold: true, color: low ? C.slateL : C.red });
      d.rect(1014, y, Math.abs(e) * SC, 16, col);
      d.text((e > 0 ? '+' : '') + e.toFixed(2), { x: 1124, y: y + 1, w: 60, px: 12.5, lh: 1.3,
                                                  mono: true, bold: true,
                                                  color: low ? C.slateL : C.red, align: 'right' });
    });
  d.text('낮게 = 팔 수 있었는데 못 팜   ·   높게 = 기준 미달',
         { x: 868, y: 476, w: 324, px: 11, lh: 1.3, color: C.dim2 });
  d.sub('겨울과 여름이 *반대로* 틀립니다', 852, 520, 356, 1);
  d.txt('그래서 상수를 올리거나 내려서는 못 고칩니다.', 852, 560, 356, 2);

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '고쳐야 할 것은 값의 크기가 아니라 *온도를 따라가는 기울기*입니다.');
};
