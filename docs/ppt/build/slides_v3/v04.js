/* v3-04 · 기존 방식의 문제점.

   2026-09-17 회신이 이 장을 다시 짰다.
     "2번의 표와 3번의 시험 40회의 그래프를 결합해서 보이면 더 좋을듯.
      3/4 같은 경우 실제 차이가 11.5 인데 보정값은 4였음. 담당자가 잘못
      선정한 건지?"

   뒤쪽 물음이 이 장의 구조를 바꿨다. 종전 표는 3열(날짜·실제 차이·더한 값)로
   13행을 늘어놓았는데, 그 13행은 실은 **7일 × 2구간**이다. 시험은 15~18시
   3시간이고 데이터 취득을 16~17시와 17~18시로 나눠 받는다. 한 일자의 두 값을
   섞어 세로로 늘어놓았으니 "11.5 인데 4를 더했다 = 7 MW 나 틀렸다" 로 읽힌다.
   실제로는 같은 날 앞 구간이 8.0 이고, 앞 구간만 모으면 평균 4.8 로 적용값 4 와
   거의 같다. 담당자는 두 값 가운데 **낮은 쪽**을 기준으로 잡은 것이다 — 많이
   신고하고 못 내면 벌칙이므로 낮게 잡는 것이 합리적인 판단이다.

   그래서 이 장은 "담당자가 틀렸다" 가 아니라 "한 값으로 끝내는 구조가
   문제였다" 로 닫는다. 표(기록 7일)와 그래프(누적 40회)를 한 구획에 나란히
   두어 그 구조가 한눈에 보이게 했다.                                       */
'use strict';
const LOG = require('../legacy_log.json');
const avg = a => a.reduce((x, y) => x + y, 0) / a.length;
module.exports = (pptx, T, meta, D) => {
  const { C, G, LW } = T;
  const { d } = T.shell(pptx, { name: '문제점', idx: 2, step: 2 });
  const B = D.impact.blanket;
  const P = LOG.pairs;
  const m1 = avg(P.map(p => p.dev1)), ma = avg(P.map(p => p.applied));

  T.title(d, '기존 방식의 문제점', null, { px: 33 });
  T.lead(d, '절차가 번거로웠고, 더하는 값을 하나로 끝냈습니다. 그래서 신고한 숫자가 어긋났습니다.',
         { y: 134, lines: 1 });

  /* ── 구획 1 · 번거로운 절차 ───────────────────────────────────── */
  let y1 = d.section(G.L, 174, 556, 116, 1, '번거로운 절차', '한 회에 1시간');
  [['엑셀 파일', '4', '개'], ['손으로 옮긴 값', '61', '개'],
   ['자동으로 되는 것', '0', '개']].forEach(([k, v, u], i) => {
    const x = 92 + i * 174;
    d.text(k, { x, y: y1, w: 164, px: 11.5, lh: 1.2, color: C.dim2 });
    const nw = Math.ceil(T.textW(v, 28)) + 4;
    d.text(v, { x, y: y1 + 18, w: nw, px: 28, lh: 1.15, mono: true, bold: true,
                color: C.brass });
    d.text(u, { x: x + nw + 4, y: y1 + 30, w: 40, px: 12.5, lh: 1.2, color: C.dim });
    if (i < 2) d.vline(x + 158, y1 - 2, 48, C.rule2, 1);
  });

  /* ── 구획 2 · 개선 목표 (배점표 '해결 목표의 타당성') ─────────── */
  let y2 = d.section(644, 174, 564, 116, 2, '개선 목표', '이 두 가지만 한다');
  /* 2026-09-17 회신: "온도마다 다르게 — '시험 실적을 쌓아 온도별 값으로' 라고
     텍스트가 있는데 목적어가 없음. PPT 전반적으로 검토해서 주어나 목적어가
     없는 텍스트는 문장이 되도록 수정." 서술을 문장으로 고쳤다. */
  [['하나로 합치기', '엑셀 파일 4개로 하던 일을 도구 하나로 합친다.'],
   ['온도마다 다르게', '시험 실적을 쌓아, 더하는 값을 온도마다 다르게 만든다.']]
    .forEach(([k, v], i) => {
    const x = 664 + i * 272;
    d.rect(x, y2, 4, 42, C.brass);
    d.text(k, { x: x + 16, y: y2 - 2, w: 240, px: 15.5, lh: 1.25, bold: true, color: C.ink });
    d.text(v, { x: x + 16, y: y2 + 20, w: 240, px: 11.5, lh: 1.3, lines: 2, color: C.dim });
  });

  /* ── 구획 3 · 표와 그래프를 한자리에 ──────────────────────────── */
  const y3 = d.section(G.L, 306, G.W, 334, 3, '더하는 값은 하나, 실제 차이는 매번 달랐다',
                       '왼쪽 기존 실적 7일 · 오른쪽 누적 ' + D.n + '회');

  /* 왼쪽 — 기존 실적 시트 기록.
     2026-09-17 회신: "날짜별로 16~17시, 17~18시 데이터 대신 이론값, 실제값으로
     변경 후 그 차이로 인한 보정값으로 표를 만들면 좋을 것 같음."
     그래서 시트의 네 열을 그대로 옮긴다 — 공급가능 용량 CC(Net)[이론값],
     Actual Data CC(Net)[실제값], Dev.(MW)[차이], BLT 적용값[더한 값].
     한 일자에 행이 두 개인데, 담당자가 실제로 기준 삼은 **앞 구간(16~17시)**
     한 줄만 싣는다. 둘을 섞어 늘어놓으면 오독된다(legacy_log.json `_구조`). */
  d.text('기존 실적 시트 · 단위 MW · 데이터 취득 ' + LOG.win1,
         { x: 92, y: y3, w: 400, px: 11, lh: 1.2, color: C.dim2 });
  const f1 = v => v.toFixed(1);
  d.table(92, y3 + 18,
    [{ label: '날짜', w: 56 },
     { label: '이론값', w: 86, align: 'right', mono: true },
     { label: '실제값', w: 86, align: 'right', mono: true },
     { label: '차이', w: 98, align: 'right', mono: true },
     { label: '더한 값', w: 74, align: 'right', mono: true }],
    P.map(p => [p.date,
      { t: f1(p.theory1), px: 11, color: C.slateL },
      { t: f1(p.actual1), px: 11, color: C.body },
      { t: (p.dev1 > 0 ? '+' : '−') + Math.abs(p.dev1).toFixed(1), px: 11, bold: true,
        color: p.dev1 < 0 ? C.red : C.ink },
      { t: '+' + p.applied, px: 11, bold: true, color: C.brass }]),
    { rh: 17, hh: 22,
      foot: ['범위', '', '',
             { t: '−' + Math.abs(Math.min(...P.map(p => p.dev1))).toFixed(1) + ' ~ +' +
                  Math.max(...P.map(p => p.dev1)).toFixed(1), px: 10.5, bold: true },
             { t: '+' + Math.min(...P.map(p => p.applied)) + ' ~ +' +
                  Math.max(...P.map(p => p.applied)), px: 10.5, bold: true,
               color: C.brass }] });
  d.text('*이론값*은 그날 온도·대기압·습도로 계산한 값, *실제값*은 시험에서 실제로 낸 값입니다. ' +
         '차이는 날마다 −4.6 ~ +8.7 로 흔들리는데, 더한 값은 시즌 내내 거의 하나였습니다.',
         { x: 92, y: y3 + 202, w: 400, px: 11, lh: 1.4, lines: 4, color: C.body });

  /* 오른쪽 — 누적 40회. 점은 시험 한 번, 점선은 늘 같던 '더한 값'. */
  const X = t => 548 + (t + 4) * 14.0, Y = c => y3 + 30 + (13 - c) * 7.4;
  [12, 8, 4, -4].forEach(v => d.hline(X(-4), Y(v), X(40) - X(-4), C.rule2, 1));
  d.hline(X(-4), Y(0), X(40) - X(-4), C.rule, 1);
  [12, 8, 4, 0, -4].forEach(v => d.text((v > 0 ? '+' : '') + v,
    { x: 508, y: Y(v) - 7, w: 32, px: 10, lh: 1.2, mono: true, color: C.dim2,
      align: 'right' }));
  [0, 10, 20, 30, 40].forEach(t => d.text(t === 0 ? '0℃' : String(t),
    { x: X(t) - 20, y: Y(-6) + 4, w: 40, px: 10, lh: 1.2, mono: true, color: C.dim2,
      align: 'center' }));
  d.hline(X(-4), Y(D.blanket.flat), X(40) - X(-4), C.slateL, LW.ref, 'dash');
  d.text('더한 값 (늘 하나)', { x: X(30), y: Y(D.blanket.flat) - 17, w: 168, px: 11,
                                 lh: 1.2, bold: true, color: C.slateL, align: 'right' });
  D.scatter.forEach(([t, c]) => d.dot(X(t), Y(c), 2.8, C.body));
  d.text('가로 외기온도 ℃ · 세로 실제 차이 MW · 점 하나가 시험 한 번',
         { x: 508, y: Y(-6) + 22, w: 560, px: 10.5, lh: 1.2, color: C.dim2 });

  /* 두 그림을 잇는 한 줄 — 왜 어긋나는지 */
  const yc = y3 + 212;
  d.rect(508, yc, 4, 76, C.red);
  d.text('겨울에는 적게 신고하고, 여름에는 못 내는데 많이 신고하게 됩니다.',
         { x: 526, y: yc, w: 656, px: 14.5, lh: 1.4, bold: true, color: C.ink });
  d.text('시험 ' + D.n + '회 가운데 *' + B.short + '회*가 신고한 만큼 못 냈습니다. ' +
         '가장 크게 어긋난 회차는 *' + B.max.toFixed(1) + ' MW* 였습니다.',
         { x: 526, y: yc + 26, w: 656, px: 12.5, lh: 1.45, lines: 2, color: C.body });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '더하는 값을 잘못 고른 것이 아니라, 하나로 끝내는 구조가 문제였습니다.');
};
