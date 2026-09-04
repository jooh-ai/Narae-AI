/* v2-05 · 현황 파악 및 문제 정의 — 요소 2개: 산점도(크게) / BLT 정수 스트립.
   오차 상위 막대 패널을 걷어내고 산점도를 전폭으로 키웠다.               */
'use strict';
const BLT = [[12.5, 4], [7.3, 5], [25.7, 5], [16.0, 5], [18.8, 5], [13.7, 5], [23.5, 1], [21.4, 3],
             [20.0, 6], [27.4, 6], [25.5, 5], [28.9, 5], [29.9, 2], [27.6, 2], [31.9, 1], [36.6, -1]];
module.exports = (pptx, T, meta, D) => {
  const { C, G, LW } = T;
  const { d } = T.shell(pptx, { sec: '문제', idx: 2, step: 2 });
  const more = Math.round(D.corr_range[1]), less = Math.round(-D.corr_range[0]);
  T.title(d, '이론값 하나로는 맞출 수 없습니다 —',
          '보정값이 회차마다 *+' + more + ' ~ −' + less + ' MW* 로 갈립니다');
  T.lead(d, '보정값은 _실제 − 이론값 − W(IGV)_ 입니다. 온도 축에 찍으면 흩어진 게 아니라 ' +
         '온도를 따라 줄줄이 내려갑니다.', { lines: 1 });

  /* 산점도 — 전폭 */
  d.zone(G.L, 284, G.W, 256);
  d.plab('점 하나가 테스트 1회  ·  누적 ' + D.n + '회  ·  가로 외기온도 ℃ / ' +
         '세로 = 보정값 = 실제 − 이론값 − W(IGV)  MW', 96, 298, 800);
  const X = t => 130 + (t + 2) * 25.6, Y = c => 330 + (14 - c) * 9;
  [12, 8, 4, -4].forEach(v => d.hline(130, Y(v), 1050, C.rule2, 1));
  d.hline(130, Y(0), 1050, C.rule, 1);
  d.vline(130, Y(14), 180, C.rule, LW.grid);
  [12, 8, 4, 0, -4].forEach(v => d.text((v > 0 ? '+' : '') + v,
    { x: 92, y: Y(v) - 7, w: 32, px: 10, lh: 1.3, mono: true, color: C.dim2, align: 'right' }));
  [0, 10, 20, 30].forEach(t => { d.vline(X(t), Y(-6), 5, C.dim2, 1);
    d.text(t === 0 ? '0℃' : String(t), { x: X(t) - 24, y: Y(-6) + 9, w: 48, px: 10, lh: 1.3,
                                          mono: true, color: C.dim2, align: 'center' }); });
  d.hline(130, Y(D.blanket.flat), 1050, C.slateL, LW.ref, 'dash');
  d.text('종전 · 온도 구분 없이 +' + D.blanket.flat.toFixed(1) + ' MW',
         { x: 900, y: Y(D.blanket.flat) - 24, w: 280, px: 12.5, lh: 1.3,
           mono: true, bold: true, color: C.slateL, align: 'right' });
  const hot = D.blanket.worst.map(w => w.cit);
  D.scatter.forEach(([t, c]) => d.dot(X(t), Y(c), hot.indexOf(t) >= 0 ? 5 : 3.8,
                                      hot.indexOf(t) >= 0 ? C.red : C.body));
  d.text('추울수록 더 더해야 하고', { x: 190, y: 344, w: 260, px: 14, lh: 1.4, color: C.dim });
  d.text('더울수록 빼야 합니다', { x: 880, y: 470, w: 300, px: 14, lh: 1.4,
                                    color: C.dim, align: 'right' });
  /* [검토 반영] 제목의 +13 / −5 는 평균이 아니라 가장 큰 한 회차 값이다.
     겨울 회차는 2건뿐이라 평균으로 읽히면 과장이 된다. */
  d.text('+' + more + ' 은 ' + D.cit_range[0] + '℃ 한 회차, −' + less +
         ' 는 여름 한 회차 — 가장 큰 값입니다',
         { x: 700, y: 344, w: 480, px: 11.5, lh: 1.3, color: C.dim2, align: 'right' });

  /* 종전엔 이 폭을 정수 하나로 덮었다 */
  /* [검토 반영] '왜 그런가' 가 빠져 있었다. 다만 흡입 공기 밀도·복수기 진공은
     이론식이 이미 보정하고 있고(온도·대기압·습도·복수기압), 진공은 6장에서
     기각됐다. 그래서 기전을 단정하지 않고 '표준 곡선과 실제 특성의 차이' 로
     적는다 — 현장에서 확인된 기전이 나오면 그 문장으로 바꾼다. */
  d.text('이론값은 *제작사 표준 성능 곡선*입니다. 우리 설비의 실제 특성과 온도에 따라 ' +
         '어긋나고, 그 차이가 저온 (+) · 고온 (−) 로 남습니다.',
         { x: 96, y: 546, w: 1088, px: 12.5, lh: 1.4, color: C.dim });

  d.zone(G.L, 570, G.W, 54);
  d.plab('종전 · 실제 적용한 값 16회  ·  회차순  ·  전부 정수 하나', 96, 582, 440, C.slate);
  const CW = 640 / 16;
  BLT.forEach(([cit, v], i) => {
    const x = 560 + i * CW, on = (cit === 7.3 || cit === 25.7);
    d.text(String(v), { x, y: 580, w: CW, px: 17, lh: 1.3, mono: true, bold: true,
                        color: on ? C.red : C.ink, align: 'center' });
    d.text(cit.toFixed(1), { x, y: 602, w: CW, px: 9.5, lh: 1.3, mono: true,
                             color: on ? C.red : C.dim2, align: 'center' });
  });
  d.text('7.3℃ 와 25.7℃ 에 똑같이 +5', { x: 96, y: 602, w: 440, px: 13, lh: 1.4, color: C.red });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '고쳐야 할 것은 값의 크기가 아니라, *온도마다 다르게 주는 것*이었습니다.');
};
