/* v2-05 · 현황 파악 및 문제 정의 — 요소 2개: 산점도(크게) / BLT 정수 스트립.
   오차 상위 막대 패널을 걷어내고 산점도를 전폭으로 키웠다.               */
'use strict';
const BLT = [[12.5, 4], [7.3, 5], [25.7, 5], [16.0, 5], [18.8, 5], [13.7, 5], [23.5, 1], [21.4, 3],
             [20.0, 6], [27.4, 6], [25.5, 5], [28.9, 5], [29.9, 2], [27.6, 2], [31.9, 1], [36.6, -1]];
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  const { d } = T.shell(pptx, { sec: '문제', idx: 2, step: 2 });
  const sign = v => (v >= 0 ? '+' : '−') + Math.abs(v).toFixed(1);
  T.title(d, '하나로는 맞출 수 없습니다 —',
          '온도에 따라 *' + sign(D.corr_range[0]) + ' ~ ' + sign(D.corr_range[1]) + '* 로 갈립니다');
  T.lead(d, '실제 보정값을 온도 축에 찍으면 흩어진 게 아니라 _한 방향으로 내려갑니다_.',
         { lines: 1 });

  /* 산점도 — 전폭 */
  d.zone(G.L, 284, G.W, 262);
  d.plab('회차별 실제 보정값  ·  누적 ' + D.n + '회차  ·  가로 외기온도 ℃ / 세로 MW',
         96, 298, 700);
  const X = t => 130 + (t + 2) * 25.6, Y = c => 330 + (14 - c) * 9;
  [12, 8, 4, -4].forEach(v => d.hline(130, Y(v), 1050, C.rule2, 1));
  d.hline(130, Y(0), 1050, C.rule, 1);
  d.vline(130, Y(14), 180, C.rule, 1);
  [12, 8, 4, 0, -4].forEach(v => d.text((v > 0 ? '+' : '') + v,
    { x: 92, y: Y(v) - 7, w: 32, px: 10, lh: 1.3, mono: true, color: C.dim2, align: 'right' }));
  [0, 10, 20, 30].forEach(t => { d.vline(X(t), Y(-6), 5, C.dim2, 1);
    d.text(t === 0 ? '0℃' : String(t), { x: X(t) - 24, y: Y(-6) + 9, w: 48, px: 10, lh: 1.3,
                                          mono: true, color: C.dim2, align: 'center' }); });
  d.hline(130, Y(D.blanket.flat), 1050, C.slateL, 2.6, 'dash');
  d.text('종전 · 하나의 값 +' + D.blanket.flat.toFixed(2),
         { x: 950, y: Y(D.blanket.flat) - 24, w: 230, px: 12.5, lh: 1.3,
           mono: true, bold: true, color: C.slateL, align: 'right' });
  const hot = D.blanket.worst.map(w => w.cit);
  D.scatter.forEach(([t, c]) => d.dot(X(t), Y(c), hot.indexOf(t) >= 0 ? 6 : 4.2,
                                      hot.indexOf(t) >= 0 ? C.red : C.body));
  d.text('추울수록 크게 더해야 하고', { x: 190, y: 344, w: 260, px: 14, lh: 1.4, color: C.dim });
  d.text('더울수록 빼야 합니다', { x: 900, y: 470, w: 280, px: 14, lh: 1.4,
                                   color: C.dim, align: 'right' });

  /* 종전엔 이 폭을 정수 하나로 덮었다 */
  d.zone(G.L, 564, G.W, 56);
  d.plab('종전 · 담당자가 적용한 보정값 16회차', 96, 576, 400, C.slate);
  const CW = 640 / 16;
  BLT.forEach(([cit, v], i) => {
    const x = 560 + i * CW, on = (cit === 7.3 || cit === 25.7);
    d.text(String(v), { x, y: 574, w: CW, px: 17, lh: 1.3, mono: true, bold: true,
                        color: on ? C.red : C.ink, align: 'center' });
    d.text(cit.toFixed(1), { x, y: 596, w: CW, px: 9.5, lh: 1.3, mono: true,
                             color: on ? C.red : C.dim2, align: 'center' });
  });
  d.text('7.3℃ 와 25.7℃ 에 똑같이 5', { x: 96, y: 596, w: 440, px: 13, lh: 1.4, color: C.red });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '고쳐야 할 것은 값의 크기가 아니라 *온도를 따라가는 기울기*입니다.');
};
