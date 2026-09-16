/* v3-04 · 기존 방식의 문제점.

   5차. 회신 반영.
     "BLT 값을 차트보다는 표로. 날짜, 실제 차이, 적용한 보정값 세 개로."
       → 막대를 걷어내고 세 열 표로 앉혔다. 헤더 음영·줄 구분·범위 요약 행까지
         theme.table 로 그린다. 숫자를 늘어놓는 것과 표로 앉히는 것은 다르게 읽힌다.
     "설명이 부족하고 내용을 조금 더 추가했으면"
       → 오른쪽에 '왜 문제인가' 를 세 줄로 붙였다. 겨울·여름·결과.
     제목에 주제를 넣었다.                                                   */
'use strict';
const LOG = require('../legacy_log.json');
module.exports = (pptx, T, meta, D) => {
  const { C, G, LW } = T;
  const { d } = T.shell(pptx, { name: '문제점', idx: 2, step: 2 });
  const B = D.impact.blanket;
  const gaps = LOG.rows.map(r => r.gap), aps = LOG.rows.map(r => r.applied);
  const lo = Math.min(...gaps), hi = Math.max(...gaps);
  T.title(d, '기존 방식의 문제점', null, { px: 33 });
  T.lead(d, '시험 결과는 회차마다 달랐지만, 더해 주는 보정값은 거의 하나로 고정돼 있었습니다.',
         { y: 146, lines: 1 });

  /* 왼쪽 — 표 */
  d.section(G.L, 186, 470, 438, 1, '기존 실적 시트 기록', '2월 ~ 4월 13회');
  d.table(100, 232,
    [{ label: '날짜', w: 74 }, { label: '실제 차이', w: 122, align: 'right', mono: true },
     { label: '적용한 보정값', w: 148, align: 'right', mono: true }],
    LOG.rows.map(r => [r.date,
      { t: r.gap.toFixed(1), bold: true, color: r.gap < 0 ? C.red : C.brass },
      { t: String(r.applied), color: C.slateL }]),
    { rh: 22, foot: ['범위', { t: lo.toFixed(1) + ' ~ ' + hi.toFixed(1), bold: true },
                     { t: Math.min(...aps) + ' ~ ' + Math.max(...aps) }] });
  d.text('단위 MW. 기존 실적 시트에서 옮겨 적었습니다.',
         { x: 100, y: 598, w: 344, px: 10.5, lh: 1.2, color: C.dim2 });

  /* 오른쪽 — 40회 전체와 그래서 무엇이 문제인가 */
  const RX = 558, RW = 650;
  d.section(RX, 186, RW, 234, 2, '시험 ' + D.n + '회 전체',
            '가로 외기온도 ℃ / 세로 실제 차이 MW');

  const X = t => RX + 64 + (t + 3) * 13.6, Y = c => 240 + (14 - c) * 7.4;
  [12, 8, 4, -4].forEach(v => d.hline(X(-3), Y(v), 558, C.rule2, 1));
  d.hline(X(-3), Y(0), 558, C.rule, 1);
  [12, 8, 4, 0, -4].forEach(v => d.text((v > 0 ? '+' : '') + v,
    { x: RX + 18, y: Y(v) - 7, w: 36, px: 10, lh: 1.2, mono: true, color: C.dim2,
      align: 'right' }));
  [0, 10, 20, 30].forEach(t => { d.vline(X(t), Y(-6), 5, C.dim2, 1);
    d.text(t === 0 ? '0℃' : String(t), { x: X(t) - 22, y: Y(-6) + 8, w: 44, px: 10,
      lh: 1.2, mono: true, color: C.dim2, align: 'center' }); });
  d.hline(X(-3), Y(D.blanket.flat), 558, C.slateL, LW.ref, 'dash');
  d.text('적용한 보정값', { x: X(20), y: Y(D.blanket.flat) - 19, w: 180, px: 11.5, lh: 1.2,
                            bold: true, color: C.slateL, align: 'right' });
  D.scatter.forEach(([t, c]) => d.dot(X(t), Y(c), 3.3, C.body));

  d.section(RX, 432, RW, 192, 3, '무엇이 문제인가', '미달 ' + B.short + '회');
  [['겨울', C.slateL, '더 낼 수 있는데 적게 신고했습니다. 팔 수 있는 양을 못 팔았습니다.'],
   ['여름', C.red, '못 내는데 많이 신고했습니다. 신고값을 못 채우면 정산에서 불이익을 받습니다.'],
   ['결과', C.brass, '시험 ' + D.n + '회 가운데 ' + B.short + '회가 신고값을 못 채웠고, ' +
    '가장 크게 어긋난 날은 ' + B.max.toFixed(1) + ' MW 였습니다.']]
    .forEach(([k, col, v], i) => {
      const y = 470 + i * 50;
      d.rect(RX + 20, y + 3, 4, 26, col);
      d.text(k, { x: RX + 34, y, w: 54, px: 15, lh: 1.3, bold: true, color: col });
      d.text(v, { x: RX + 96, y: y + 1, w: RW - 136, px: 13, lh: 1.45, lines: 2,
                  color: C.body });
    });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '온도마다 다른 것을 하나로 맞추려니 맞을 수가 없었습니다.');
};
