/* v3-03 · 우리가 하는 일 — 전제를 설명하는 장 (2026-09-16 신규).

   자체 검토에서 가장 크게 걸린 것이 이것이었다. **전제를 아무 데서도 설명하지
   않았다.** 발전소가 전기를 팔기 전에 "얼마나 낼 수 있다" 를 미리 알려야 한다는
   것, 그 숫자가 틀리면 손해가 난다는 것, 낼 수 있는 양이 날씨에 따라 달라진다는
   것. 이 셋을 모르면 뒤의 모든 장이 소용없다.

   그림으로만 설명한다. 글은 칸 이름과 한 줄씩. 목차 항목이 없는 장이므로
   오른쪽 위 눈금도 띄우지 않는다.                                          */
'use strict';
module.exports = (pptx, T, meta, D) => {
  const { C, G, LW } = T;
  const { d } = T.shell(pptx, { sec: '들어가기 전에' });
  T.title(d, '우리가 하는 일', null, { px: 34 });
  T.lead(d, '발전소는 전기를 만들어 팝니다. 팔기 전에 얼마나 낼 수 있는지 미리 알려야 합니다.',
         { y: 150, lines: 1 });

  /* 구획 1 — 파는 순서 */
  d.section(G.L, 192, G.W, 112, 1, '전기를 파는 순서', '');
  [['전기를 만든다', '가스와 증기로 돌립니다.'],
   ['얼마나 낼 수 있는지 알린다', '하루 전에 알립니다.'],
   ['그 숫자로 팔린다', '알린 만큼만 팔립니다.'],
   ['그만큼 실제로 낸다', '못 내면 벌칙이 있습니다.']]
    .forEach(([k, v], i) => {
      const x = 96 + i * 282;
      d.text(String(i + 1), { x, y: 236, w: 22, px: 15, lh: 1.2, mono: true, bold: true,
                              color: C.brass });
      d.text(k, { x: x + 26, y: 234, w: 214, px: 14.5, lh: 1.3, bold: true, color: C.ink });
      d.text(v, { x: x + 26, y: 258, w: 214, px: 12, lh: 1.3, color: C.dim });
      if (i < 3) d.arrow(x + 246, 240);
    });

  /* 구획 2 — 날씨에 따라 달라진다 */
  d.section(G.L, 316, 556, 308, 2, '어려운 점 하나', '날씨에 따라 달라집니다');
  const R = D.profile.rows.filter(r => r.t >= -10 && r.t <= 40);
  const vs = R.map(r => r.theory);
  const lo = Math.min(...vs), hi = Math.max(...vs);
  const X = t => 140 + (t + 10) * 8.9, Y = v => 520 - (v - lo) / (hi - lo) * 124;
  d.hline(132, 528, 480, C.rule, 1);
  d.vline(132, 380, 148, C.rule, 1);
  for (let i = 0; i < R.length - 1; i++)
    d.seg(X(R[i].t), Y(R[i].theory), X(R[i + 1].t), Y(R[i + 1].theory), C.brass, LW.main);
  d.text('많이', { x: 84, y: Y(hi) - 8, w: 44, px: 11.5, lh: 1.2, color: C.dim2,
                    align: 'right' });
  d.text('적게', { x: 84, y: Y(lo) - 8, w: 44, px: 11.5, lh: 1.2, color: C.dim2,
                    align: 'right' });
  d.text('추울 때', { x: 132, y: 534, w: 90, px: 12, lh: 1.2, color: C.dim });
  d.text('더울 때', { x: 520, y: 534, w: 90, px: 12, lh: 1.2, color: C.dim,
                       align: 'right' });
  d.dot(X(-8), Y(R[1].theory), 6, C.brass);
  d.dot(X(38), Y(R[R.length - 2].theory), 6, C.brass);
  d.text('추우면 많이 나옵니다. 더우면 적게 나옵니다.',
         { x: 92, y: 360, w: 516, px: 15.5, lh: 1.4, color: C.body });
  d.text('그래서 온도마다 숫자가 다릅니다.',
         { x: 92, y: 562, w: 516, px: 13, lh: 1.4, color: C.dim });

  /* 구획 3 — 틀리면 손해 */
  d.section(644, 316, 564, 308, 3, '어려운 점 둘', '틀리면 손해가 납니다');
  d.text('알린 숫자가 실제와 어긋나면 손해가 납니다.',
         { x: 664, y: 360, w: 524, px: 15.5, lh: 1.4, color: C.body });
  [[C.red, '많이 알렸는데 못 냈다', '벌칙을 받습니다.'],
   [C.slateL, '적게 알렸는데 더 낼 수 있었다', '팔 기회를 놓칩니다.']]
    .forEach(([col, k, v], i) => {
      const y = 406 + i * 104;
      d.box(664, y, 524, 84, null, col, 1.4);
      d.rect(664, y, 5, 84, col);
      d.text(k, { x: 686, y: y + 16, w: 486, px: 17, lh: 1.3, bold: true, color: C.ink });
      d.text(v, { x: 686, y: y + 46, w: 486, px: 13, lh: 1.3, color: C.dim });
    });
  d.text('그래서 이 숫자를 잘 맞혀야 합니다.',
         { x: 664, y: 600, w: 524, px: 13, lh: 1.3, color: C.dim2 });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '이 숫자를 만드는 일을 바꿨습니다.');
};
