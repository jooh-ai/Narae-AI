/* v3-08 · 개선효과 (정량).
   배점이 가장 큰 항목(25점)이라 정량·정성 두 장으로 나눴다. 이 장은 숫자만.
   평가내용의 '시간절감 · 오류감소 · 정량 성과' 에 하나씩 대응한다.

   시간은 2026-09-17 회신에서 받았다 — 종전 한 회에 1시간, 지금은 5분 안팎.   */
'use strict';
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  const I = D.impact, B = I.blanket, GP = I.gp, K = I.cut, P = D.cp;
  const { d } = T.shell(pptx, { name: '개선효과', idx: 6, step: 6 });
  T.title(d, '무엇이 얼마나 좋아졌나', null, { px: 33 });
  T.lead(d, '같은 시험 ' + D.n + '회에 예전 방법과 새 방법을 각각 써 봤습니다.',
         { y: 146, lines: 1 });

  /* 구획 1 — 시간 */
  d.section(G.L, 182, 556, 172, 1, '일 처리 시간', '한 회 기준');
  d.text('1시간', { x: 96, y: 228, w: 138, px: 30, lh: 1.15, mono: true, color: C.slateL });
  d.text('→', { x: 244, y: 238, w: 34, px: 18, lh: 1.2, color: C.dim2 });
  d.text('5분', { x: 288, y: 220, w: 104, px: 44, lh: 1.15, mono: true, bold: true,
                   color: C.brass });
  d.text('안팎', { x: 400, y: 248, w: 70, px: 14, lh: 1.2, color: C.dim });
  d.vline(500, 222, 100, C.rule2, 1);
  d.text('92%', { x: 522, y: 226, w: 90, px: 22, lh: 1.15, mono: true, bold: true,
                   color: C.brass });
  d.text('줄었습니다', { x: 522, y: 254, w: 100, px: 12.5, lh: 1.2, color: C.dim });
  d.text('날짜와 시각만 넣으면 끝납니다.',
         { x: 96, y: 292, w: 516, px: 13.5, lh: 1.3, lines: 1, color: C.body });
  d.text('2주마다 한 번이면 한 해에 24시간쯤 줄어듭니다.',
         { x: 96, y: 318, w: 516, px: 11.5, lh: 1.3, color: C.dim2 });

  /* 구획 2 — 정확도 */
  d.section(644, 182, 564, 172, 2, '숫자 정확도', '시험 ' + D.n + '회 채점');
  [['틀리는 폭', B.mae.toFixed(1), GP.mae.toFixed(1), 'MW', K.mae],
   ['알린 만큼 못 낸 횟수', String(B.short), String(GP.short), '회', K.short],
   ['높게 알린 양', B.over.toFixed(0), GP.over.toFixed(0), 'MW', K.over]]
    .forEach(([k, a, b, u, cut], i) => {
      const y = 224 + i * 38;
      d.text(k, { x: 664, y: y + 3, w: 190, px: 12.5, lh: 1.2, color: C.dim2 });
      const aw = Math.ceil(T.textW(a, 15)) + 4;
      d.text(a, { x: 866, y: y + 2, w: aw, px: 15, lh: 1.2, mono: true, color: C.slateL });
      d.text('→', { x: 866 + aw + 6, y: y + 4, w: 20, px: 12, lh: 1.2, color: C.dim2 });
      const bw = Math.ceil(T.textW(b, 21)) + 4;
      d.text(b, { x: 866 + aw + 30, y, w: bw, px: 21, lh: 1.2, mono: true, bold: true,
                  color: C.brass });
      d.text(u, { x: 866 + aw + 34 + bw, y: y + 6, w: 34, px: 11.5, lh: 1.2, color: C.dim });
      d.text(cut + '%↓', { x: 1120, y: y + 3, w: 68, px: 12.5, lh: 1.2, mono: true,
                            bold: true, color: C.brass, align: 'right' });
      if (i < 2) d.hline(664, y + 32, 524, C.rule2, 1);
    });
  d.text('* 한 회를 가리고 나머지로 그 회를 맞혀 보는 방식으로 채점했습니다. ' +
         '실제로 알린 기록이 아닙니다.',
         { x: 664, y: 334, w: 524, px: 10, lh: 1.3, color: C.dim2 });

  /* 구획 3 — 돈으로 보면 */
  d.section(G.L, 366, G.W, 258, 3, '돈으로 보면', '용량요금 기준');
  d.text('낮게 알려서 못 받던 용량요금', { x: 96, y: 410, w: 420, px: 13, lh: 1.3,
                                            color: C.dim2 });
  const man = v => Math.round(v / 1e4).toLocaleString() + '만원';
  d.text(man(P.lost_before), { x: 96, y: 432, w: 190, px: 24, lh: 1.15, mono: true,
                               color: C.slateL });
  d.text('→', { x: 292, y: 440, w: 30, px: 16, lh: 1.2, color: C.dim2 });
  d.text(man(P.lost_after), { x: 334, y: 428, w: 220, px: 30, lh: 1.15, mono: true,
                              bold: true, color: C.brass });
  d.text('한 해에', { x: 96, y: 470, w: 100, px: 12, lh: 1.2, color: C.dim2 });
  d.rect(96, 500, 4, 56, C.brass);
  d.text('한 해 ' + man(P.recover) + ' 을 되찾습니다', { x: 116, y: 500, w: 440, px: 20,
                                                          lh: 1.3, bold: true,
                                                          color: C.brass });
  d.text('낮게 알린 양이 줄어든 만큼입니다.', { x: 116, y: 532, w: 440, px: 12.5,
                                                lh: 1.3, color: C.dim });
  d.vline(606, 404, 180, C.rule2, 1);
  d.text('계산 조건', { x: 640, y: 406, w: 200, px: 11.5, lh: 1.2, bold: true,
                        color: C.dim2 });
  [['용량요금 단가', P.rate_kw_day.toFixed(0) + ' 원/kW·일'],
   ['입찰하는 날', P.bid_days.toFixed(0) + ' 일 (정비 30일 제외)'],
   ['채점한 시험', D.n_score + ' 회'],
   ['넣지 않은 것', '전력 판매 수익 · 페널티']]
    .forEach(([k, v], i) => {
      const y = 430 + i * 30;
      d.text(k, { x: 640, y, w: 180, px: 12, lh: 1.2, color: C.dim2 });
      d.text(v, { x: 830, y, w: 358, px: 12.5, lh: 1.2, color: C.body });
    });
  d.text('* 단가는 담당자에게 확인 중인 계획값입니다. 확정되면 다시 계산합니다.',
         { x: 640, y: 556, w: 548, px: 10, lh: 1.3, color: C.dim2 });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '일은 줄고 숫자는 맞았습니다. 처음에 바라던 두 가지입니다.');
};
