/* v3-08 · 개선효과 (정량).
   배점이 가장 큰 항목(25점)이라 정량·정성 두 장으로 나눴다. 이 장은 숫자만.
   시간은 2026-09-17 회신에서 받았다 — 종전 한 회에 1시간, 지금은 5분 안팎.

   2026-09-17 회신: "2. 숫자 정확도가 어떻게 나온 숫자인지 설명이 필요."
   종전 판은 표 아래 각주 한 줄(10px)로 "한 회를 가리고 나머지로 맞혀 봤다" 고만
   적어 두었다. 이 장에서 가장 많이 질문받을 숫자인데 근거가 가장 작은 글씨로
   적혀 있었다. 그래서 **채점 방법에 구획을 따로 주었다**(구획 3). 네 칸으로
   끊어 두면 "그 숫자 어디서 나왔습니까" 에 장표를 가리키며 답할 수 있다.    */
'use strict';
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  const I = D.impact, B = I.blanket, GP = I.gp, K = I.cut, P = D.cp;
  const { d } = T.shell(pptx, { name: '개선효과', idx: 6, step: 6 });

  T.title(d, '개선 효과 · 정량', null, { px: 33 });
  T.lead(d, '같은 시험 ' + D.n_score + '회에 예전 방법과 새 방법을 각각 써서 채점했습니다.',
         { y: 134, lines: 1 });

  /* ── 구획 1 · 일 처리 시간 ────────────────────────────────────── */
  const y1 = d.section(G.L, 174, 556, 150, 1, '일 처리 시간', '한 회 기준');
  d.text('1시간', { x: 92, y: y1 + 8, w: 132, px: 30, lh: 1.15, mono: true,
                     color: C.slateL });
  d.text('→', { x: 234, y: y1 + 18, w: 30, px: 18, lh: 1.2, color: C.dim2 });
  d.text('5분', { x: 276, y: y1, w: 104, px: 44, lh: 1.15, mono: true, bold: true,
                   color: C.brass });
  d.text('안팎', { x: 386, y: y1 + 28, w: 60, px: 14, lh: 1.2, color: C.dim });
  d.vline(482, y1 + 2, 84, C.rule2, 1);
  d.text('92%', { x: 504, y: y1 + 6, w: 90, px: 22, lh: 1.15, mono: true, bold: true,
                   color: C.brass });
  d.text('줄었습니다', { x: 504, y: y1 + 34, w: 100, px: 12.5, lh: 1.2, color: C.dim });
  d.text('엑셀 4개를 오가던 일이 날짜·시각 입력으로 바뀌었습니다.',
         { x: 92, y: y1 + 92, w: 516, px: 12.5, lh: 1.35, color: C.body });

  /* ── 구획 2 · 예측 정확도 ─────────────────────────────────────── */
  const y2 = d.section(644, 174, 564, 150, 2, '예측 정확도',
                       '같은 ' + D.n_score + '회 · 왼쪽 종전 → 오른쪽 도구');
  [['틀리는 폭', B.mae.toFixed(1), GP.mae.toFixed(1), 'MW', K.mae],
   ['신고한 만큼 못 낸 횟수', String(B.short), String(GP.short), '회', K.short],
   ['높게 신고한 양 합계', B.over.toFixed(0), GP.over.toFixed(0), 'MW', K.over]]
    .forEach(([k, a, b, u, cut], i) => {
      const y = y2 + i * 36;
      d.text(k, { x: 664, y: y + 3, w: 196, px: 12, lh: 1.2, color: C.dim2 });
      const aw = Math.ceil(T.textW(a, 15)) + 4;
      d.text(a, { x: 868, y: y + 2, w: aw, px: 15, lh: 1.2, mono: true, color: C.slateL });
      d.text('→', { x: 868 + aw + 6, y: y + 4, w: 20, px: 12, lh: 1.2, color: C.dim2 });
      const bw = Math.ceil(T.textW(b, 21)) + 4;
      d.text(b, { x: 868 + aw + 30, y, w: bw, px: 21, lh: 1.2, mono: true, bold: true,
                  color: C.brass });
      d.text(u, { x: 868 + aw + 34 + bw, y: y + 6, w: 34, px: 11.5, lh: 1.2, color: C.dim });
      d.text(cut + '%↓', { x: 1120, y: y + 3, w: 68, px: 12.5, lh: 1.2, mono: true,
                            bold: true, color: C.brass, align: 'right' });
      if (i < 2) d.hline(664, y + 30, 524, C.rule2, 1);
    });

  /* ── 구획 3 · 그 숫자를 어떻게 쟀나 ───────────────────────────── */
  const y3 = d.section(G.L, 330, G.W, 124, 3, '정확도를 어떻게 쟀나',
                       '실제로 신고한 기록이 아니라 되돌려 본 채점입니다');
  [['한 회를 가린다', '시험 ' + D.n + '회 가운데 한 회를 빼 둡니다.'],
   ['나머지로 맞혀 본다', '가린 회차의 온도만 주고 모델이 보정값을 예측하게 합니다.'],
   ['실제와 견준다', '예측한 값과 그날 실제 값의 차이를 적습니다.'],
   ['전부 돌아가며 반복', '한 번씩 다 가려 보고 평균을 냅니다.']]
    .forEach(([k, v], i) => {
      const x = 92 + i * 276;
      d.text(String(i + 1), { x, y: y3, w: 16, px: 12, lh: 1.2, mono: true, bold: true,
                              color: C.brass });
      d.text(k, { x: x + 20, y: y3 - 2, w: 232, px: 13, lh: 1.25, bold: true, color: C.ink });
      d.text(v, { x: x + 20, y: y3 + 18, w: 232, px: 10.5, lh: 1.3, lines: 2, color: C.dim });
      if (i < 3) d.text('→', { x: x + 254, y: y3, w: 18, px: 12, lh: 1.2, color: C.dim2,
                               align: 'center' });
    });
  d.text('종전 방식도 같은 회차에 「늘 같은 값 하나」를 더해 똑같이 채점했습니다. ' +
         '그래서 두 값을 나란히 견줄 수 있습니다. ' + D.n + '회 가운데 ' + D.n_score +
         '회를 썼습니다 — 한 회차는 그 온도 구간에 시험이 하나뿐이라, 가리면 ' +
         '종전 방식이 답을 못 냅니다.',
         { x: 92, y: y3 + 58, w: 1090, px: 10, lh: 1.35, lines: 2, color: C.dim2 });

  /* ── 구획 4 · 돈으로 보면 ─────────────────────────────────────── */
  const y4 = d.section(G.L, 466, G.W, 174, 4, '돈으로 보면', '용량요금 기준');
  const man = v => Math.round(v / 1e4).toLocaleString() + '만원';
  d.text('낮게 신고해서 못 받던 용량요금 (한 해)', { x: 92, y: y4, w: 420, px: 12,
                                                     lh: 1.3, color: C.dim2 });
  d.text(man(P.lost_before), { x: 92, y: y4 + 20, w: 180, px: 22, lh: 1.15, mono: true,
                               color: C.slateL });
  d.text('→', { x: 278, y: y4 + 28, w: 28, px: 15, lh: 1.2, color: C.dim2 });
  d.text(man(P.lost_after), { x: 314, y: y4 + 16, w: 220, px: 28, lh: 1.15, mono: true,
                              bold: true, color: C.brass });
  d.rect(92, y4 + 62, 4, 44, C.brass);
  d.text('한 해 ' + man(P.recover) + '을 되찾습니다', { x: 110, y: y4 + 60, w: 440,
                                                          px: 19, lh: 1.3, bold: true,
                                                          color: C.brass });
  d.text('낮게 신고한 양이 줄어든 만큼입니다.', { x: 110, y: y4 + 88, w: 440, px: 11.5,
                                                  lh: 1.3, color: C.dim });
  d.vline(606, y4 - 2, 120, C.rule2, 1);
  [['용량요금 단가', P.rate_kw_day.toFixed(0) + ' 원/kW·일'],
   ['입찰하는 날', P.bid_days.toFixed(0) + ' 일 (정비 30일 제외)'],
   ['채점한 시험', D.n_score + ' 회'],
   ['넣지 않은 것', '전력 판매 수익 · 벌칙금']]
    .forEach(([k, v], i) => {
      const y = y4 + i * 26;
      d.text(k, { x: 640, y, w: 180, px: 11.5, lh: 1.2, color: C.dim2 });
      d.text(v, { x: 830, y, w: 358, px: 12, lh: 1.2, color: C.body });
    });
  d.text('* 단가는 담당자에게 확인 중인 계획값입니다. 확정되면 다시 계산합니다.',
         { x: 640, y: y4 + 110, w: 548, px: 10, lh: 1.3, color: C.dim2 });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '일은 줄고 숫자는 정확해졌습니다. 처음에 세운 목표 두 가지를 다 이뤘습니다.');
};
