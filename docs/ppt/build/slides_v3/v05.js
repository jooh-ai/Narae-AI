/* v3-04 · 기존 방식의 문제점.

   6차. 회신: "내 생각에 문제는 셋이다. 일괄보정 하는 문제, 여러 개의 엑셀을
   다루며 번거로운 절차, 일괄보정에 따른 예측값 오차. 근데 보정에 관한 것만
   포커싱이 되어 있는 느낌이야."

   맞는 지적이었다. 이 장이 보정값 이야기 하나로만 차 있었다. 셋으로 갈랐다.
     1  번거로운 절차     — 파일과 손으로 옮기는 값의 개수
     2  일괄 보정        — 실적 시트 기록 표
     3  예측값 오차      — 시험 40회 전체와 그 결과
   과정 이야기는 이 장에 넣지 않는다. 여기는 '무엇이 문제였나' 만 다룬다.     */
'use strict';
const LOG = require('../legacy_log.json');
module.exports = (pptx, T, meta, D) => {
  const { C, G, LW } = T;
  const { d } = T.shell(pptx, { name: '문제점', idx: 2, step: 2 });
  const B = D.impact.blanket;
  const gaps = LOG.rows.map(r => r.gap), aps = LOG.rows.map(r => r.applied);
  const lo = Math.min(...gaps), hi = Math.max(...gaps);
  T.title(d, '기존 방식의 문제점', null, { px: 33 });
  T.lead(d, '문제는 세 가지였습니다. 절차가 번거롭고, 더하는 값이 하나로 고정되며, ' +
         '그래서 숫자가 어긋났습니다.', { y: 146, lines: 1 });

  /* 구획 1 — 번거로운 절차 */
  d.section(G.L, 186, G.W, 92, 1, '번거로운 절차', '한 회차마다 되풀이');
  [['엑셀 파일', '4', '개'], ['손으로 옮기는 값', '61', '개'],
   ['사람이 넣는 값', '3', '곳'], ['자동으로 되는 것', '0', '개']]
    .forEach(([k, v, u], i) => {
      const x = 96 + i * 278;
      d.text(k, { x, y: 226, w: 190, px: 12, lh: 1.2, color: C.dim2 });
      const nw = Math.ceil(T.textW(v, 26)) + 4;
      d.text(v, { x, y: 240, w: nw, px: 26, lh: 1.15, mono: true, bold: true,
                  color: C.brass });
      d.text(u, { x: x + nw + 4, y: 250, w: 40, px: 12.5, lh: 1.2, color: C.dim });
      if (i < 3) d.vline(x + 250, 224, 42, C.rule2, 1);
    });

  /* 구획 2 — 일괄 보정 */
  d.section(G.L, 290, 470, 334, 2, '똑같은 값 더하기', '2월 ~ 4월 13회 · 단위 MW');
  d.table(100, 328,
    [{ label: '날짜', w: 74 }, { label: '실제 차이', w: 122, align: 'right', mono: true },
     { label: '더한 값', w: 148, align: 'right', mono: true }],
    LOG.rows.map(r => [r.date,
      { t: r.gap.toFixed(1), px: 11.5, bold: true, color: r.gap < 0 ? C.red : C.brass },
      { t: String(r.applied), px: 11.5, color: C.slateL }]),
    { rh: 19, hh: 24,
      foot: ['범위', { t: lo.toFixed(1) + ' ~ ' + hi.toFixed(1), px: 11.5, bold: true },
             { t: Math.min(...aps) + ' ~ ' + Math.max(...aps), px: 11.5 }] });
  /* 구획 3 — 예측값 오차 */
  const RX = 558, RW = 650;
  d.section(RX, 290, RW, 334, 3, '얼마나 어긋났나', '가로 바깥 온도 ℃ / 세로 차이 MW');
  const X = t => RX + 64 + (t + 3) * 13.6, Y = c => 330 + (14 - c) * 7.0;
  [12, 8, 4, -4].forEach(v => d.hline(X(-3), Y(v), 558, C.rule2, 1));
  d.hline(X(-3), Y(0), 558, C.rule, 1);
  [12, 4, 0, -4].forEach(v => d.text((v > 0 ? '+' : '') + v,
    { x: RX + 18, y: Y(v) - 7, w: 36, px: 10, lh: 1.2, mono: true, color: C.dim2,
      align: 'right' }));
  [0, 10, 20, 30].forEach(t => { d.vline(X(t), Y(-6), 4, C.dim2, 1);
    d.text(t === 0 ? '0℃' : String(t), { x: X(t) - 22, y: Y(-6) + 6, w: 44, px: 10,
      lh: 1.2, mono: true, color: C.dim2, align: 'center' }); });
  d.hline(X(-3), Y(D.blanket.flat), 558, C.slateL, LW.ref, 'dash');
  d.text('더한 값', { x: X(21), y: Y(D.blanket.flat) - 18, w: 180, px: 11, lh: 1.2,
                            bold: true, color: C.slateL, align: 'right' });
  D.scatter.forEach(([t, c]) => d.dot(X(t), Y(c), 2.9, C.body));
  [['겨울', C.slateL, '더 낼 수 있는데 적게 알렸습니다. 팔 수 있는 양을 못 팔았습니다.'],
   ['여름', C.red, '못 내는데 많이 알렸습니다. 알린 만큼 못 내면 벌칙을 받습니다.'],
   ['결과', C.brass, '시험 ' + D.n + '회 가운데 ' + B.short + '회가 알린 만큼 못 냈습니다.']]
    .forEach(([k, col, v], i) => {
      const y = 496 + i * 44;
      d.rect(RX + 20, y + 3, 4, 26, col);
      d.text(k, { x: RX + 34, y, w: 54, px: 14.5, lh: 1.3, bold: true, color: col });
      d.text(v, { x: RX + 94, y: y + 1, w: RW - 134, px: 12.5, lh: 1.45, lines: 2,
                  color: C.body });
    });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '온도마다 다른 것을 하나로 맞추려니 맞을 수가 없었습니다.');
};
