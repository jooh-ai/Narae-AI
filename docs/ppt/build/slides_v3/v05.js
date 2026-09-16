/* v3-05 · 차이가 생기는 원인.
   구획 셋. 후보 넷을 놓고 하나만 남긴 과정 / 진공도를 세 번 접은 이야기 /
   결론을 한 번 철회한 이야기.

   통계 용어는 쓰지 않는다. 표 대신 후보 상자 넷을 놓고 셋에 가로줄을 긋는다.
   "무엇을 넣어 봤고 무엇이 남았나" 만 보이면 된다. 숫자는 마지막 한 줄에만.  */
'use strict';
const CAND = [
  ['외기 온도', true,  '이것만 보면 됐습니다.'],
  ['복수기 진공도', false, '온도를 빼면 남는 게 없었습니다.'],
  ['대기압', false, '계산식이 이미 쓰고 있었습니다.'],
  ['상대 습도', false, '넣어도 나아지지 않았습니다.'],
];
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  const { d } = T.shell(pptx, { name: '원인', idx: 3, step: 3 });
  T.title(d, '무엇 때문에 어긋났나', null, { px: 33 });
  T.lead(d, '무엇 때문인지 하나씩 확인했습니다. 결국 온도였습니다.',
         { y: 146, lines: 1 });

  /* 구획 1 — 후보 넷 */
  d.section(G.L, 186, G.W, 196, 1, '넣어 본 것과 남은 것', '후보 4개 → 1개');
  const BW = 258, GAP = 20;
  CAND.forEach(([name, keep, why], i) => {
    const x = 88 + i * (BW + GAP);
    d.box(x, 226, BW, 60, keep ? null : C.groove, keep ? C.brass : C.rule2, keep ? 1.6 : 1);
    d.text(name, { x: x + 14, y: 244, w: BW - 28, px: 17, lh: 1.3, bold: true,
                   color: keep ? C.brass : C.dim2 });
    if (!keep) d.hline(x + 14, 256, Math.min(T.textW(name, 17) + 6, BW - 28), C.dim2, 1.4);
    d.text(keep ? '남았습니다' : '아니었습니다',
           { x: x + 14, y: 296, w: BW - 28, px: 12.5, lh: 1.3, bold: true,
             color: keep ? C.brass : C.dim2 });
    d.text(why, { x: x + 14, y: 318, w: BW - 28, px: 12, lh: 1.5, lines: 3, color: C.dim });
  });

  /* 구획 2 — 진공도. 세 번 의심해 세 번 접은 이야기 */
  d.section(G.L, 394, 556, 230, 2, '겪은 일 · 진공도를 세 번 접었다', '');
  d.text('복수기 진공도를 의심했습니다. 여름에 나빠지니 그럴듯했습니다.',
         { x: 92, y: 434, w: 516, px: 13, lh: 1.55, lines: 3, color: C.body });
  [['첫 번째', '계절 탓인지 설비 탓인지 갈라 봤습니다.', '아니었습니다'],
   ['두 번째', '연도를 나눠 봤습니다.', '한 해만 그랬습니다'],
   ['세 번째', '온도를 걷어내고 다시 봤습니다.', '사라졌습니다']]
    .forEach(([k, v, r], i) => {
      const y = 500 + i * 34;
      d.text(k, { x: 92, y, w: 68, px: 12.5, lh: 1.3, bold: true, color: C.slateL });
      d.text(v, { x: 168, y, w: 300, px: 12.5, lh: 1.3, color: C.body });
      d.text(r, { x: 472, y, w: 136, px: 12.5, lh: 1.3, bold: true, color: C.red,
                  align: 'right' });
    });
  d.text('세 번 다 착각이었습니다.',
         { x: 92, y: 602, w: 516, px: 13, lh: 1.3, lines: 1, color: C.dim2 });

  /* 구획 3 — 결론 철회 */
  d.section(644, 394, 564, 230, 3, '겪은 일 · 결론을 한 번 뒤집었다', '');
  d.text('2025년 봄 시험이 유별나게 낮았습니다. 설비가 오래됐다고 보고 문서까지 썼습니다.',
         { x: 664, y: 434, w: 524, px: 13, lh: 1.55, lines: 3, color: C.body });
  d.rect(664, 500, 4, 92, C.red);
  d.text('다시 파 보니 원인이 달랐습니다.',
         { x: 684, y: 500, w: 504, px: 14.5, lh: 1.4, bold: true, color: C.ink });
  d.text('IGV 를 올리지 않고 시험한 날이었습니다. 결론을 거뒀습니다.\n' +
         '이제 이런 날의 시험은 도구가 걸러냅니다.',
         { x: 684, y: 526, w: 504, px: 13, lh: 1.55, lines: 4, color: C.dim });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '의심을 하나씩 접고 나니 온도만 남았습니다.');
};
