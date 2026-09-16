/* v3-03 · 개요 및 추진 배경.
   구획 셋. 우리가 하는 일(전제) / 이 과제를 고른 이유 / 기존 절차.

   2026-09-17 회신이 이 장을 만들었다. 우리 둘은 정비기술팀이고 공급가능용량
   테스트는 발전운영팀 일이다. 남의 팀 업무인데 왜 골랐느냐 — 이 질문에 대한
   답이 곧 '과제 필요성' 이고, 심사 배점에서 문제정의(20점)의 평가내용이다.
   그래서 배경 장의 가운데에 세웠다.                                        */
'use strict';
const A = require('./assets.js');
module.exports = (pptx, T, meta, D) => {
  const { C, G, LW } = T;
  const { d } = T.shell(pptx, { name: '추진 배경', idx: 1, step: 1 });
  T.title(d, '이 과제를 시작한 이유', null, { px: 33 });
  T.lead(d, '발전소는 전기를 팔기 전에 얼마나 낼 수 있는지 미리 알려야 합니다. 그 숫자를 만드는 일입니다.',
         { y: 146, lines: 1 });

  /* 구획 1 — 전제. 온도에 따라 달라지고, 틀리면 손해다. */
  d.section(G.L, 186, G.W, 148, 1, '신고하는 숫자', '온도 61개마다 따로');
  const R = D.profile.rows.filter(r => r.t >= -10 && r.t <= 40);
  const vs = R.map(r => r.theory), lo = Math.min(...vs), hi = Math.max(...vs);
  const X = t => 116 + (t + 10) * 6.4, Y = v => 316 - (v - lo) / (hi - lo) * 76;
  d.hline(110, 320, 340, C.rule, 1);
  for (let i = 0; i < R.length - 1; i++)
    d.seg(X(R[i].t), Y(R[i].theory), X(R[i + 1].t), Y(R[i + 1].theory), C.brass, LW.main);
  d.text('추우면 많이', { x: 110, y: 228, w: 120, px: 12, lh: 1.2, color: C.dim2 });
  d.text('더우면 적게', { x: 336, y: 272, w: 120, px: 12, lh: 1.2, color: C.dim2,
                           align: 'right' });
  d.text('추울 때와 더울 때 낼 수 있는 양이 다릅니다.',
         { x: 490, y: 226, w: 340, px: 14, lh: 1.45, lines: 2, color: C.body });
  d.text('영하 20도부터 40도까지 61개 온도의 숫자를 따로 냅니다.',
         { x: 490, y: 270, w: 350, px: 12.5, lh: 1.4, lines: 2, color: C.dim });
  d.vline(862, 222, 96, C.rule2, 1);
  d.text('알린 숫자가 어긋나면', { x: 890, y: 224, w: 300, px: 12, lh: 1.2, color: C.dim2 });
  d.text('많이 알리고 못 내면', { x: 890, y: 248, w: 190, px: 13, lh: 1.3, color: C.body });
  d.text('벌칙', { x: 1086, y: 246, w: 100, px: 14, lh: 1.3, bold: true, color: C.red,
                    align: 'right' });
  d.text('적게 알리면', { x: 890, y: 278, w: 146, px: 13, lh: 1.3, color: C.body });
  d.text('팔 기회를 놓침', { x: 1046, y: 276, w: 140, px: 14, lh: 1.3, bold: true,
                              color: C.slateL, align: 'right' });

  /* 구획 2 — 우리 팀 일이 아닌데 왜 골랐나 */
  d.section(G.L, 346, 556, 278, 2, '과제 선정 이유', '정비기술팀');
  d.text('공급가능용량 테스트는 발전운영팀 업무입니다.',
         { x: 92, y: 388, w: 516, px: 15, lh: 1.4, bold: true, color: C.ink });
  d.text('우리는 정비기술팀입니다. 절차도 원리도 몰랐습니다.',
         { x: 92, y: 414, w: 516, px: 13.5, lh: 1.4, color: C.dim });
  [['눈에 먼저 보였다', '엑셀 네 개를 오가는 일이 번거로워 보였습니다.'],
   ['수익으로 이어진다', '숫자가 정확해지면 그만큼 손해가 줄어듭니다.']]
    .forEach(([k, v], i) => {
      const y = 458 + i * 62;
      d.rect(92, y + 2, 4, 44, C.brass);
      d.text(k, { x: 112, y, w: 496, px: 15.5, lh: 1.3, bold: true, color: C.brass });
      d.text(v, { x: 112, y: y + 24, w: 496, px: 13, lh: 1.35, color: C.body });
    });
  d.text('그래서 우리 팀 일이 아닌데도 과제로 잡았습니다.',
         { x: 92, y: 594, w: 516, px: 12.5, lh: 1.3, color: C.dim2 });

  /* 구획 3 — 기존 절차 */
  d.section(644, 346, 564, 278, 3, '기존 절차', '엑셀 파일 4개 · 한 회에 1시간');
  const STEP = [['① 계측값 받아오기', A.xl1], ['② 온도별로 계산', A.xl2],
                ['③ 차이를 더하기', A.xl2blt], ['④ 표 완성', A.xl3]];
  STEP.forEach(([name, file], i) => {
    const x = 664 + (i % 2) * 272, y = 388 + Math.floor(i / 2) * 118;
    d.text(name, { x, y, w: 250, px: 12.5, lh: 1.25, bold: true, color: C.brass });
    d.box(x, y + 20, 250, 74, null, C.rule2, 1);
    d.imgFit(file, x + 5, y + 24, 240, 66);
  });
  d.text('값은 손으로 옮겼습니다. 옮겨 적는 값이 61개였습니다.',
         { x: 664, y: 606, w: 524, px: 12, lh: 1.3, color: C.dim2 });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '모르는 업무였지만 비효율이 먼저 보였습니다. 거기서 시작했습니다.');
};
