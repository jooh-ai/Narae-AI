/* v3-04 · 그런데 문제가 있었습니다.

   3차. 앞 판은 오른쪽이 설명 문단 세 덩어리였다. 회신대로 주저리주저리였다.
   각 덩어리를 **한 줄**로 줄이고, 비운 자리에 실측 40회를 찍었다.
   말로 "제각각이다" 라고 쓰는 대신 점이 흩어진 것과 선이 한 줄인 것을 나란히 둔다.

   왼쪽 엑셀 캡처가 '현장 기록', 오른쪽 점들이 '40회를 다 모은 모습' 이다.
   같은 사실을 두 번 말하는 것이 아니라, 한 회차에서 본 것이 40회에서도
   그렇다는 것을 보이는 것이다.                                             */
'use strict';
const A = require('./assets.js');
module.exports = (pptx, T, meta, D) => {
  const { C, G, LW } = T;
  const { d } = T.shell(pptx, { sec: '문제', idx: 2, step: 2 });
  T.title(d, '그런데 문제가 있었습니다', null);

  /* 왼쪽 — 현장 기록 */
  d.zone(G.L, 168, 648, 404);
  d.plab('기존 실적 시트에서 세 열만 오렸습니다', 92, 180, 500);
  d.imgFit(A.xl1gap, 92, 204, 608, 336);
  d.text('같은 시트 같은 회차이고, 열 사이 거리만 좁혔습니다.',
         { x: 92, y: 550, w: 608, px: 11.5, lh: 1.2, color: C.dim2 });

  /* 오른쪽 — 한 줄씩만. 그리고 40회 전부 */
  const RX = 752, RW = 456;
  d.rect(RX, 180, 24, 13, C.brass);
  d.text('시험할 때마다 달랐습니다', { x: RX + 34, y: 174, w: RW - 34, px: 20,
                                       lh: 1.35, bold: true, color: C.ink });
  d.text('11이 나온 날도 있고 4가 나온 날도 있었습니다.',
         { x: RX, y: 206, w: RW, px: 14.5, lh: 1.5, color: C.body });

  d.rect(RX, 256, 24, 13, C.slate);
  d.text('더하는 값은 늘 같았습니다', { x: RX + 34, y: 250, w: RW - 34, px: 20,
                                        lh: 1.35, bold: true, color: C.ink });
  d.text('차이가 얼마든 4를 더했습니다.',
         { x: RX, y: 282, w: RW, px: 14.5, lh: 1.5, color: C.body });

  d.hline(RX, 322, RW, C.rule, 1);
  d.plab('시험 ' + D.n + '회를 온도별로 전부 찍으면', RX, 336, 340);

  const X = t => RX + 24 + (t + 3) * 9.9, Y = c => 372 + (14 - c) * 9.2;
  [12, 8, 4, -4].forEach(v => d.hline(X(-3), Y(v), 414, C.rule2, 1));
  d.hline(X(-3), Y(0), 414, C.rule, 1);
  [12, 8, 4, 0, -4].forEach(v => d.text((v > 0 ? '+' : '') + v,
    { x: RX - 14, y: Y(v) - 7, w: 32, px: 10, lh: 1.2, mono: true, color: C.dim2,
      align: 'right' }));
  [0, 10, 20, 30].forEach(t => { d.vline(X(t), Y(-6), 5, C.dim2, 1);
    d.text(t === 0 ? '0℃' : String(t), { x: X(t) - 22, y: Y(-6) + 8, w: 44, px: 10,
      lh: 1.2, mono: true, color: C.dim2, align: 'center' }); });
  d.hline(X(-3), Y(D.blanket.flat), 414, C.slateL, LW.ref, 'dash');
  d.text('늘 더하던 값', { x: X(24), y: Y(D.blanket.flat) - 20, w: 160, px: 11.5,
                            lh: 1.2, bold: true, color: C.slateL, align: 'right' });
  D.scatter.forEach(([t, c]) => d.dot(X(t), Y(c), 3.2, C.body));
  d.text('점 하나가 시험 한 번입니다.',
         { x: RX, y: Y(-6) + 26, w: RW, px: 11.5, lh: 1.2, color: C.dim2 });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '날씨마다 다른 것을 하나로 맞추려니 맞을 수가 없었습니다.');
};
