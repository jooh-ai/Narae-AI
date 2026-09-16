/* v3-03 · 기존에는 이렇게 했습니다.

   2026-09-16 3차. 회신 두 줄이 핵심이었다.
     "직관적으로 바뀐 것 같아" / "하지만 기존에 있던 성의가 모두 사라진 느낌"
     "텍스트도 주저리 주저리 길어진 것 같고"

   앞 판에서 내가 한 것은 **정교한 차트를 빼고 그 자리에 문단을 넣은 것**이었다.
   말은 길어지고 그림은 초라해졌으니 둘 다 나빠졌다. 방향이 거꾸로였다.

     성의는 그림에서 나온다. 쉬움은 짧은 말에서 나온다.
     그러니 말을 줄이고 그림을 늘려야 한다. 설명을 문단이 아니라 그림이 한다.

   그래서 "시험은 한 점, 신고는 61개" 를 글로 쓰지 않고 **그려** 놓았다.
   온도 눈금 61개를 실제로 찍고, 시험한 자리 하나만 표시하고, 같은 값이
   전 구간에 깔리는 것을 선으로 보인다. 글은 한 줄만 남겼다.                */
'use strict';
const A = require('./assets.js');
const STEP = [['① 값 받아오기', A.xl1], ['② 온도별 계산', A.xl2],
              ['③ 차이 더하기', A.xl2blt], ['④ 프로파일 완성', A.xl3]];
const T0 = -20, T1 = 40, PX0 = 214, PXW = 906;      // 온도축 픽셀
const TX = t => PX0 + (t - T0) * (PXW / (T1 - T0));
const SHOT = 25;                                     // 그림에 표시할 '시험한 온도'

module.exports = (pptx, T, meta, D) => {
  const { C, G, LW } = T;
  const { d } = T.shell(pptx, { sec: '추진 배경', idx: 1, step: 1 });
  T.title(d, '기존에는 이렇게 했습니다', null);

  /* 위 — 파일 네 개를 순서대로 */
  const BW = 266, GAP = 24;
  STEP.forEach(([name, file], i) => {
    const x = G.L + i * (BW + GAP);
    d.text(name, { x, y: 168, w: BW, px: 14.5, lh: 1.3, bold: true, color: C.brass,
                   align: 'center' });
    d.zone(x, 192, BW, 196);
    d.imgFit(file, x + 10, 200, BW - 20, 180);
    if (i < STEP.length - 1) d.arrow(x + BW + 2, 282);
  });

  /* 아래 — 말로 설명하지 않고 그린다 */
  d.zone(G.L, 404, G.W, 220);
  d.plab('시험한 온도는 하루에 한 곳뿐입니다', 96, 416, 500);

  const BASE = 574, LINE = 496;
  for (let t = T0; t <= T1; t++) {                   // 눈금 61개를 실제로 찍는다
    const on = t === SHOT;
    d.vline(TX(t), BASE - (on ? 16 : 7), on ? 16 : 7, on ? C.brass : C.rule, on ? 2 : 1);
  }
  d.hline(PX0 - 8, BASE, PXW + 16, C.rule, 1);
  [T0, -10, 0, 10, 20, 30, T1].forEach(t => d.text((t > 0 ? '+' : '') + t,
    { x: TX(t) - 24, y: BASE + 8, w: 48, px: 10.5, lh: 1.2, mono: true,
      color: C.dim2, align: 'center' }));
  d.text('℃', { x: TX(T1) + 26, y: BASE + 8, w: 24, px: 10.5, lh: 1.2, color: C.dim2 });

  d.hline(PX0, LINE, PXW, C.slateL, LW.ref, 'dash');
  d.dot(TX(SHOT), LINE, 7, C.brass);
  d.vline(TX(SHOT), LINE + 8, BASE - LINE - 24, C.brass, 1, 'dash');
  d.text('여기서 시험했습니다', { x: TX(SHOT) - 140, y: LINE - 30, w: 280, px: 14,
                                  lh: 1.3, bold: true, color: C.brass, align: 'center' });
  d.text('여기서 나온 차이를', { x: 96, y: LINE - 34, w: 240, px: 13.5, lh: 1.4,
                                 color: C.dim });
  d.text('61개 온도 전부에 똑같이 얹었습니다',
         { x: 96, y: LINE + 6, w: 240, px: 13.5, lh: 1.4, lines: 2, color: C.slateL });
  d.text('나머지 60개 온도는 시험해 보지 않았습니다',
         { x: PX0, y: BASE + 30, w: PXW, px: 13, lh: 1.3, color: C.dim, align: 'center' });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '그때는 이게 최선이었습니다.');
};
