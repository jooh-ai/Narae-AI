/* v3-04 · 현황 파악 및 문제정의 — 문제 셋과 해결 목표.

   배점표의 '문제정의 및 과제 적절성(20점)' 평가내용 네 개 가운데 마지막이
   **해결 목표의 타당성** 이다. 앞 판에는 목표 선언이 없어서 문제에서 바로
   방안으로 넘어갔다. 그래서 이 장 끝에 목표 구획을 세웠다.               */
'use strict';
const LOG = require('../legacy_log.json');
module.exports = (pptx, T, meta, D) => {
  const { C, G, LW } = T;
  const { d } = T.shell(pptx, { name: '문제점', idx: 2, step: 2 });
  const B = D.impact.blanket;
  const gaps = LOG.rows.map(r => r.gap), aps = LOG.rows.map(r => r.applied);
  const lo = Math.min(...gaps), hi = Math.max(...gaps);
  T.title(d, '무엇이 문제였나', null, { px: 33 });
  T.lead(d, '불편한 점이 세 가지 있었습니다.', { y: 146, lines: 1 });

  /* 구획 1 — 번거로운 절차 */
  d.section(G.L, 182, 556, 130, 1, '절차가 번거로웠다', '한 회에 1시간');
  [['엑셀 파일', '4', '개'], ['손으로 옮기는 값', '61', '개'],
   ['자동으로 되는 것', '0', '개']].forEach(([k, v, u], i) => {
    const x = 96 + i * 176;
    d.text(k, { x, y: 224, w: 166, px: 11.5, lh: 1.2, color: C.dim2 });
    const nw = Math.ceil(T.textW(v, 26)) + 4;
    d.text(v, { x, y: 240, w: nw, px: 26, lh: 1.15, mono: true, bold: true, color: C.brass });
    d.text(u, { x: x + nw + 4, y: 250, w: 40, px: 12.5, lh: 1.2, color: C.dim });
    if (i < 2) d.vline(x + 160, 222, 44, C.rule2, 1);
  });
  d.text('파일을 오가며 값을 옮겼습니다.', { x: 96, y: 282, w: 500, px: 12.5, lh: 1.3,
                                             color: C.dim });

  /* 구획 2 — 같은 값을 더했다 */
  d.section(G.L, 324, 556, 300, 2, '같은 값을 더했다', '2월 ~ 4월 13회 · 단위 MW');
  d.table(96, 360,
    [{ label: '날짜', w: 68 }, { label: '실제 차이', w: 112, align: 'right', mono: true },
     { label: '더한 값', w: 132, align: 'right', mono: true }],
    LOG.rows.map(r => [r.date,
      { t: r.gap.toFixed(1), px: 11, bold: true, color: r.gap < 0 ? C.red : C.brass },
      { t: String(r.applied), px: 11, color: C.slateL }]),
    { rh: 17, hh: 22,
      foot: ['범위', { t: lo.toFixed(1) + ' ~ ' + hi.toFixed(1), px: 11, bold: true },
             { t: Math.min(...aps) + ' ~ ' + Math.max(...aps), px: 11 }] });
  d.text('시험 결과는 매번 달랐습니다.', { x: 428, y: 400, w: 190, px: 14.5, lh: 1.4,
                                            lines: 2, bold: true, color: C.ink });
  d.text('그런데 더하는 값은 거의 그대로였습니다.',
         { x: 428, y: 452, w: 190, px: 13, lh: 1.45, lines: 3, color: C.body });
  d.text('기존 실적 시트에서 옮겨 적었습니다.',
         { x: 428, y: 560, w: 190, px: 10.5, lh: 1.3, lines: 2, color: C.dim2 });

  /* 구획 3 — 그래서 숫자가 어긋났다 */
  d.section(644, 182, 564, 258, 3, '그래서 숫자가 어긋났다', '시험 ' + D.n + '회');
  const X = t => 700 + (t + 3) * 12.2, Y = c => 226 + (14 - c) * 5.4;
  [12, 8, 4, -4].forEach(v => d.hline(X(-3), Y(v), 500, C.rule2, 1));
  d.hline(X(-3), Y(0), 500, C.rule, 1);
  [12, 4, 0, -4].forEach(v => d.text((v > 0 ? '+' : '') + v,
    { x: 660, y: Y(v) - 7, w: 32, px: 10, lh: 1.2, mono: true, color: C.dim2,
      align: 'right' }));
  [0, 10, 20, 30].forEach(t => d.text(t === 0 ? '0℃' : String(t),
    { x: X(t) - 20, y: Y(-6) + 5, w: 40, px: 10, lh: 1.2, mono: true, color: C.dim2,
      align: 'center' }));
  d.hline(X(-3), Y(D.blanket.flat), 500, C.slateL, LW.ref, 'dash');
  d.text('더한 값', { x: X(22), y: Y(D.blanket.flat) - 17, w: 140, px: 11, lh: 1.2,
                       bold: true, color: C.slateL, align: 'right' });
  D.scatter.forEach(([t, c]) => d.dot(X(t), Y(c), 2.8, C.body));
  d.text('가로 외기온도 ℃ / 세로 실제 차이 MW · 점 하나가 시험 한 번',
         { x: 660, y: 354, w: 540, px: 10.5, lh: 1.2, color: C.dim2 });
  [['겨울', C.slateL, '더 낼 수 있었는데 적게 알렸습니다.'],
   ['여름', C.red, '못 내는데 많이 알렸습니다.'],
   ['결과', C.brass, '시험 ' + D.n + '회 가운데 ' + B.short + '회가 알린 만큼 못 냈습니다.']]
    .forEach(([k, col, v], i) => {
      const y = 374 + i * 21;
      d.text(k, { x: 664, y, w: 50, px: 12.5, lh: 1.2, bold: true, color: col });
      d.text(v, { x: 722, y, w: 470, px: 12.5, lh: 1.2, color: C.body });
    });

  /* 구획 4 — 해결 목표. 배점표의 '해결 목표의 타당성' 에 대응한다. */
  d.section(644, 452, 564, 172, 4, '그래서 세운 목표', '이 두 가지만 한다');
  [['흩어진 과정을 하나로', '엑셀 4개를 도구 하나로 합친다.'],
   ['숫자를 온도마다 다르게', '시험 결과를 쌓아 온도별로 다른 값을 쓴다.']]
    .forEach(([k, v], i) => {
      const y = 492 + i * 64;
      d.rect(664, y + 2, 4, 48, C.brass);
      d.text(String(i + 1), { x: 682, y, w: 20, px: 13, lh: 1.2, mono: true, bold: true,
                              color: C.brass });
      d.text(k, { x: 708, y: y - 2, w: 484, px: 16.5, lh: 1.3, bold: true, color: C.ink });
      d.text(v, { x: 708, y: y + 24, w: 484, px: 12.5, lh: 1.35, color: C.dim });
    });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '하나의 숫자로는 맞출 수가 없었습니다.');
};
