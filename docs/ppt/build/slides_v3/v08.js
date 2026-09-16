/* v3-07 · 신고 정확도와 업무 시간.
   구획 셋. 정확도 / 업무 / 겪은 일(우리 규칙이 엑셀과 달랐다).

   숫자를 크게 쓰는 유일한 장이다. 대신 종전 값을 나란히 놓아 크기를 짐작하게
   한다. 큰 숫자 셋을 넘기지 않는다.                                        */
'use strict';
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  const { d } = T.shell(pptx, { name: '개선 효과', idx: 5, step: 5 });
  const I = D.impact, B = I.blanket, GP = I.gp, K = I.cut;
  T.title(d, '얼마나 좋아졌나', null, { px: 33 });
  T.lead(d, '시험 ' + D.n + '회에 예전 방법과 새 방법을 각각 써 보고 채점한 결과입니다.',
         { y: 146, lines: 1 });

  /* 구획 1 — 정확도 */
  d.section(G.L, 186, 700, 232, 1, '숫자가 얼마나 맞았나', '시험 ' + D.n + '회');
  [['틀리는 폭', B.mae.toFixed(1), GP.mae.toFixed(1), 'MW', K.mae],
   ['알린 만큼 못 낸 횟수', String(B.short), String(GP.short), '회', K.short],
   ['실제보다 높게 알린 양', B.over.toFixed(0), GP.over.toFixed(0), 'MW', K.over]]
    .forEach(([k, before, after, unit, cut], i) => {
      const x = 92 + i * 232;
      d.text(k, { x, y: 226, w: 210, px: 12, lh: 1.3, lines: 1, color: C.dim2 });
      const bw = Math.ceil(T.textW(before, 18)) + 4;
      d.text(before, { x, y: 256, w: bw, px: 18, lh: 1.2, mono: true, color: C.slateL });
      d.text('→', { x: x + bw + 6, y: 259, w: 22, px: 13, lh: 1.2, color: C.dim2 });
      const nw = Math.ceil(T.textW(after, 36)) + 4;
      d.text(after, { x: x + bw + 34, y: 246, w: nw, px: 36, lh: 1.15, mono: true,
                      bold: true, color: C.brass });
      d.text(unit, { x: x + bw + 38 + nw, y: 268, w: 40, px: 13, lh: 1.2, color: C.dim });
      d.rect(x, 316, 204, 8, C.groove);
      d.rect(x, 316, Math.round(204 * (100 - cut) / 100), 8, C.slate);
      d.text(cut + '% 줄었습니다', { x, y: 330, w: 204, px: 12.5, lh: 1.3, bold: true,
                                     color: C.brass });
      d.text('종전 ' + before + ' ' + unit, { x, y: 352, w: 204, px: 11.5, lh: 1.3,
                                               color: C.dim2 });
      if (i < 2) d.vline(x + 218, 226, 140, C.rule2, 1);
    });
  d.text('한 회를 가리고 나머지로 그 회를 맞혀 보는 방식으로 채점했습니다.\n' +
         '실제로 알린 기록이 아니라, 같은 데이터에 두 방법을 써 본 값입니다.',
         { x: 92, y: 384, w: 660, px: 11.5, lh: 1.3, lines: 2, color: C.dim2 });

  /* 구획 2 — 업무 */
  d.section(788, 186, 420, 232, 2, '일이 얼마나 줄었나', '한 번 할 때 기준');
  [['엑셀 파일', '4개', '1개'], ['손으로 옮기는 값', '61개', '0개'],
   ['사람이 넣는 값', '3곳', '날짜와 시각']]
    .forEach(([k, a, b], i) => {
      const y = 232 + i * 56;
      d.text(k, { x: 808, y, w: 240, px: 12.5, lh: 1.3, color: C.dim2 });
      const aw = Math.ceil(T.textW(a, 17)) + 4;
      d.text(a, { x: 808, y: y + 20, w: aw, px: 17, lh: 1.25, color: C.slateL });
      d.text('→', { x: 808 + aw + 8, y: y + 22, w: 22, px: 13, lh: 1.2, color: C.dim2 });
      d.text(b, { x: 808 + aw + 36, y: y + 18, w: 1184 - (808 + aw + 36), px: 18,
                  lh: 1.25, bold: true, color: C.brass });
      if (i < 2) d.hline(808, y + 46, 380, C.rule2, 1);
    });
  d.text('날짜와 시각을 넣고 실행하면 끝납니다.',
         { x: 808, y: 396, w: 380, px: 12, lh: 1.3, color: C.dim });

  /* 구획 3 — 겪은 일 */
  d.section(G.L, 430, G.W, 194, 3, '겪은 일 · 우리 계산이 엑셀과 달랐다', '');
  d.text('도구가 기존 엑셀과 같은 답을 내는지 맞춰 보다가 드러났습니다.\n' +
         '공기 압력을 우리는 7일 평균으로 쓰고 있었는데, 엑셀 수식은 5일 평균이었습니다.',
         { x: 92, y: 470, w: 540, px: 13.5, lh: 1.6, lines: 4, color: C.body });
  d.rect(664, 466, 4, 130, C.brass);
  d.text('처방도 한 번 틀렸습니다.', { x: 684, y: 466, w: 504, px: 15, lh: 1.35,
                                       bold: true, color: C.ink });
  d.text('처음에는 "고를 수 있게 만들자" 고 했습니다. 그런데 실무는 하나로 정해져 있어 ' +
         '고를 여지가 없었습니다.\n선택을 빼고 엑셀과 똑같이 맞췄습니다.',
         { x: 684, y: 494, w: 504, px: 13, lh: 1.55, lines: 5, color: C.dim });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '숫자가 좋아진 것보다, 왜 그 숫자인지 말할 수 있게 된 것이 더 큽니다.');
};
