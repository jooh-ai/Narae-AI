/* v3-03 · 기존 공급가능용량 산정 방식.

   5차. 회신 네 가지를 반영했다.
     "'기존 방식' 만 있으면 뭘 했던 기존 방식인지 인식이 안 된다"
       → 제목에 주제를 넣는다. 단어를 유지하되 무엇에 대한 장인지 밝힌다.
     "전반적으로 설명이 부족해 보이고, 내용을 조금 더 추가했으면"
       → 단계마다 설명을 되살렸다. 다만 구획(zone)으로 묶어 산만해지지 않게 한다.
     "내용은 쉽지만 잘 만든 PPT 느낌을 내고 싶어"
       → 목표를 이렇게 읽었다. 포스터가 아니라 **쉬운 말로 쓴 잘 만든 보고서**다.
         비우는 것이 답이 아니고, 채우되 구조가 보이게 하는 것이 답이다.       */
'use strict';
const A = require('./assets.js');
const STEP = [
  ['① 계측값 받아오기', A.xl1,  '시험한 날의 계측값을 받아옵니다.'],
  ['② 온도별로 계산', A.xl2,  '온도별로 계산값이 나옵니다.'],
  ['③ 차이를 더하기', A.xl2blt,    '시험 결과와의 차이를 더합니다.'],
  ['④ 표 완성', A.xl3,  '옮겨 붙이면 끝입니다.'],
];
const T0 = -20, T1 = 40, PX0 = 200, PXW = 920;
const TX = t => PX0 + (t - T0) * (PXW / (T1 - T0));
const SHOT = 25;

module.exports = (pptx, T, meta, D) => {
  const { C, G, LW } = T;
  const { d } = T.shell(pptx, { name: '기존 방식', idx: 1, step: 1 });
  T.title(d, '예전에 숫자를 만든 방법', null, { px: 33 });
  T.lead(d, '엑셀 네 개를 차례로 열어야 했습니다. 값은 손으로 옮겼습니다.',
         { y: 146, lines: 1 });

  /* 구획 1 — 절차 */
  d.section(G.L, 186, G.W, 206, 1, '숫자를 만드는 순서', '엑셀 파일 4개');
  const BW = 258, GAP = 20;
  STEP.forEach(([name, file, why], i) => {
    const x = 88 + i * (BW + GAP);
    d.text(name, { x, y: 222, w: BW, px: 13.5, lh: 1.3, bold: true, color: C.brass });
    d.box(x, 242, BW, 88, null, C.rule2, 1);
    d.imgFit(file, x + 6, 246, BW - 12, 80);
    d.text(why, { x, y: 338, w: BW, px: 11.5, lh: 1.5, lines: 3, color: C.dim });
    if (i < STEP.length - 1) d.arrow(x + BW + 1, 280);
  });

  /* 구획 2 — 보정값을 어떻게 정했나.
     회신: "한눈에 차트가 이해되지 않아. 좀 더 쉽고 구체적으로."
     종전에는 점 하나와 점선 하나였다. 무엇을 보라는 것인지 알 수 없었다.
     이번에는 **61개 온도에 실제로 들어간 값을 막대 61개로 세운다.**
     전부 같은 높이인데 근거가 있는 것은 한 개뿐이라는 것이 바로 보인다.   */
  d.section(G.L, 404, G.W, 220, 2, '더할 값을 정하는 방법', '시험 1곳 → 61개 온도');
  d.text('시험은 하루에 한 번뿐입니다. 나머지 온도는 시험해 본 적이 없었습니다.',
         { x: 96, y: 438, w: 700, px: 14, lh: 1.3, lines: 1, color: C.body });

  const BASE = 580, MWPX = 18, VAL = 4;
  const BY = v => BASE - v * MWPX;
  [0, 2, 4, 6].forEach(v => {
    d.hline(196, BY(v), PXW + 12, v === 0 ? C.rule : C.rule2, 1);
    d.text(String(v), { x: 150, y: BY(v) - 7, w: 36, px: 10.5, lh: 1.2, mono: true,
                        color: C.dim2, align: 'right' });
  });
  d.text('더한 값\nMW', { x: 96, y: BY(6) - 4, w: 46, px: 10, lh: 1.3, lines: 2,
                           color: C.dim2, align: 'right' });
  for (let t = T0; t <= T1; t++) {
    const on = t === SHOT;
    d.rect(TX(t) - 4.5, BY(VAL), 9, VAL * MWPX, on ? C.brass : C.slate);
  }
  [T0, -10, 0, 10, 20, 30, T1].forEach(t => d.text((t > 0 ? '+' : '') + t,
    { x: TX(t) - 24, y: BASE + 6, w: 48, px: 10.5, lh: 1.2, mono: true, color: C.dim2,
      align: 'center' }));
  d.text('℃', { x: TX(T1) + 26, y: BASE + 6, w: 24, px: 10.5, lh: 1.2, color: C.dim2 });

  d.vline(TX(SHOT), BY(VAL) - 24, 20, C.brass, 1);
  d.text('이 온도만 시험했습니다', { x: TX(SHOT) - 150, y: BY(VAL) - 42, w: 300, px: 13,
                                    lh: 1.3, bold: true, color: C.brass, align: 'center' });
  d.rect(210, BY(6) + 2, 14, 7, C.slate);
  d.text('나머지는 같은 값을 썼습니다',
         { x: 230, y: BY(6) - 2, w: 400, px: 12.5, lh: 1.3, color: C.slateL });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '해보지 않은 온도는 알 방법이 없었으니, 그때는 이게 최선이었습니다.');
};
