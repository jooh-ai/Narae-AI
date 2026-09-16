/* v3-04 · ② 현황 파악 및 문제 정의 — 차이는 매번 다른데 얹는 값은 하나였다.
   요소 둘: 담당자 실적 시트에서 오려낸 세 열(왼쪽) / 누적 40회 산점도(오른쪽).

   왼쪽이 주인공이다. 우리가 그린 산점도보다 **담당자 본인의 파일**이 세다.
   숫자를 읽어 주지 않는다 — "위 칸은 매번 다른데 아래 칸은 같은 값" 한 문장.
   오른쪽은 "그게 40회 전부에서 이렇게 보인다" 로 받는다.               */
'use strict';
const A = require('./assets.js');
module.exports = (pptx, T, meta, D) => {
  const { C, G, LW } = T;
  const { d } = T.shell(pptx, { sec: '문제', idx: 2, step: 2 });
  const more = Math.round(D.corr_range[1]), less = Math.round(-D.corr_range[0]);
  T.title(d, '차이는 매번 달랐습니다', '그런데 얹는 값은 *하나*였습니다');
  T.lead(d, '왼쪽은 담당자가 쓰던 실적 시트입니다. ' +
         '노란 칸은 회차마다 달라지는데, 오른쪽 칸은 같은 값입니다.',
         { y: 190, lines: 1 });

  /* 왼쪽 — 실물. 20열이 넘는 시트라 세 열만 오려 나란히 붙였다(crop_shot.py) */
  d.zone(G.L, 256, 560, 368);
  d.plab('엑셀①「Base Load Test 실적」 에서 세 열만 오렸습니다', 92, 268, 520);
  d.imgFit(A.xl1gap, 92, 290, 520, 286);
  d.text('같은 시트, 같은 회차. 열 사이 거리만 좁혔습니다.',
         { x: 92, y: 588, w: 520, px: 11, lh: 1.2, color: C.dim2 });

  /* 오른쪽 — 40회 전부 */
  d.zone(648, 256, 560, 368);
  d.plab('누적 ' + D.n + '회  ·  점 하나가 테스트 한 번', 668, 268, 300);
  d.text('가로 외기온도 ℃ / 세로 차이 MW',
         { x: 968, y: 266, w: 220, px: 10.5, lh: 1.2, color: C.dim2, align: 'right' });
  const X = t => 700 + (t + 3) * 11.4, Y = c => 306 + (14 - c) * 11.0;
  [12, 8, 4, -4].forEach(v => d.hline(700, Y(v), 480, C.rule2, 1));
  d.hline(700, Y(0), 480, C.rule, 1);
  d.vline(700, Y(14), 220, C.rule, LW.grid);
  [12, 8, 4, 0, -4].forEach(v => d.text((v > 0 ? '+' : '') + v,
    { x: 660, y: Y(v) - 7, w: 32, px: 10, lh: 1.3, mono: true, color: C.dim2,
      align: 'right' }));
  [0, 10, 20, 30].forEach(t => { d.vline(X(t), Y(-6), 5, C.dim2, 1);
    d.text(t === 0 ? '0℃' : String(t), { x: X(t) - 24, y: Y(-6) + 9, w: 48, px: 10,
      lh: 1.3, mono: true, color: C.dim2, align: 'center' }); });
  d.hline(700, Y(D.blanket.flat), 480, C.slateL, LW.ref, 'dash');
  d.text('종전 · 온도 구분 없이 +' + D.blanket.flat.toFixed(1),
         { x: 900, y: Y(D.blanket.flat) - 22, w: 280, px: 11.5, lh: 1.3, mono: true,
           bold: true, color: C.slateL, align: 'right' });
  D.scatter.forEach(([t, c]) => d.dot(X(t), Y(c), 3.4, C.body));
  /* 폭을 한 번만 말한다 */
  d.text('추울수록 더 나오고, 더울수록 덜 나옵니다. 가장 큰 회차는 *+' + more +
         '* 과 *−' + less + ' MW* 였습니다.',
         { x: 668, y: 568, w: 500, px: 12.5, lh: 1.5, lines: 2, color: C.dim });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '고쳐야 할 것은 값의 크기가 아니라 *온도마다 다르게 주는 것*이었습니다.');
};
