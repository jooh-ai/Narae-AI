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
  ['① 시험 결과 받아오기', A.xl1,  '날짜와 시각을 넣으면 계측값 14개를 시스템에서 끌어옵니다.'],
  ['② 온도별 이론값 계산', A.xl2,  '대기압을 넣으면 영하 20도부터 40도까지 61개 값이 나옵니다.'],
  ['③ 보정값 더하기', A.xl2blt,    '시험한 온도에서 생긴 차이를 61개 값에 모두 더합니다.'],
  ['④ 온도 프로파일 완성', A.xl3,  '이 표를 그대로 옮겨 붙이면 그날 신고할 숫자가 됩니다.'],
];
const T0 = -20, T1 = 40, PX0 = 200, PXW = 920;
const TX = t => PX0 + (t - T0) * (PXW / (T1 - T0));
const SHOT = 25;

module.exports = (pptx, T, meta, D) => {
  const { C, G, LW } = T;
  const { d } = T.shell(pptx, { name: '기존 방식', idx: 1, step: 1 });
  T.title(d, '기존 공급가능용량 산정 방식', null, { px: 33 });
  T.lead(d, '시험 결과를 엑셀 네 개에 차례로 옮겨 담아 신고할 숫자를 만들었습니다.',
         { y: 146, lines: 1 });

  /* 구획 1 — 절차 */
  d.zone(G.L, 190, G.W, 246);
  d.plab('산정 절차', 96, 200, 200);
  d.text('엑셀 파일 4개', { x: 908, y: 199, w: 280, px: 11, lh: 1.2, mono: true,
                             color: C.dim2, align: 'right' });
  const BW = 258, GAP = 20;
  STEP.forEach(([name, file, why], i) => {
    const x = 88 + i * (BW + GAP);
    d.text(name, { x, y: 222, w: BW, px: 13.5, lh: 1.3, bold: true, color: C.brass });
    d.box(x, 244, BW, 114, null, C.rule2, 1);
    d.imgFit(file, x + 6, 250, BW - 12, 102);
    d.text(why, { x, y: 368, w: BW, px: 11.5, lh: 1.5, lines: 3, color: C.dim });
    if (i < STEP.length - 1) d.arrow(x + BW + 1, 292);
  });

  /* 구획 2 — 왜 하나를 전부에 더했나. 글로 쓰지 않고 그린다. */
  d.zone(G.L, 448, G.W, 176);
  d.plab('보정값을 정하는 방법', 96, 458, 260);
  d.text('시험은 하루에 한 곳에서만 합니다. 그 한 곳에서 나온 차이를 나머지 60개 온도에도 ' +
         '똑같이 더했습니다.',
         { x: 380, y: 456, w: 808, px: 13, lh: 1.3, lines: 1, color: C.dim, align: 'right' });

  const BASE = 598, LINE = 528;
  for (let t = T0; t <= T1; t++) {
    const on = t === SHOT;
    d.vline(TX(t), BASE - (on ? 14 : 6), on ? 14 : 6, on ? C.brass : C.rule, on ? 2 : 1);
  }
  d.hline(PX0 - 8, BASE, PXW + 16, C.rule, 1);
  [T0, -10, 0, 10, 20, 30, T1].forEach(t => d.text((t > 0 ? '+' : '') + t,
    { x: TX(t) - 24, y: BASE + 7, w: 48, px: 10.5, lh: 1.2, mono: true, color: C.dim2,
      align: 'center' }));
  d.text('℃', { x: TX(T1) + 26, y: BASE + 7, w: 24, px: 10.5, lh: 1.2, color: C.dim2 });
  d.hline(PX0, LINE, PXW, C.slateL, LW.ref, 'dash');
  d.dot(TX(SHOT), LINE, 7, C.brass);
  d.vline(TX(SHOT), LINE + 8, BASE - LINE - 22, C.brass, 1, 'dash');
  d.text('시험한 온도 1곳', { x: TX(SHOT) - 150, y: LINE - 28, w: 300, px: 13.5, lh: 1.3,
                              bold: true, color: C.brass, align: 'center' });
  d.text('신고 범위 61개 온도', { x: 96, y: LINE - 10, w: 96, px: 12, lh: 1.3, lines: 2,
                                  bold: true, color: C.slateL });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '해보지 않은 온도는 알 방법이 없었으니, 그때는 이게 최선이었습니다.');
};
