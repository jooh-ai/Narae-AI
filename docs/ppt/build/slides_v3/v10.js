/* v3-10 · 향후 계획.

   2026-09-17 회신이 이 장에 물음 하나를 얹었다.
     "다른 발전소도 사용한다는 내용이 있는데 다른 발전소 SIEMENS 다른 모델일
      경우 특성 곡선이 다른데 가능한지? 추가로 데이터를 쌓으면서 정확도를
      높인다는 내용이 있으면 좋겠음. 차트로 있지만 말로 설명해도 좋을 듯."

   답은 코드에 있다. `tool/wirye_capacity/theory.py:23 load_base_table(path)` 는
   경로를 받는다. 특성 곡선은 코드에 박혀 있지 않고 61행 표 파일(base_table.json)
   로 읽는다. 그러니 그 발전소 곡선표만 바꿔 넣으면 된다. 옮겨 가는 것은 곡선이
   아니라 **절차**다 — 이 구분을 구획 2 에 그대로 적었다. 곡선을 복사해 쓰는
   것처럼 읽히면 안 된다.

   학습 곡선은 막대만 있고 말이 없었다. 숫자를 문장으로도 한 번 적었다.      */
'use strict';
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  const { d } = T.shell(pptx, { name: '향후 계획', idx: 7, step: 7 });
  const L = D.learning, BK = L.blocks;

  T.title(d, '향후 계획', null, { px: 33 });
  T.lead(d, '두 가지입니다. 실적을 쌓아 더 정확하게, 그리고 다른 발전소로.',
         { y: 134, lines: 1 });

  /* ── 구획 1 · 실적을 쌓아 더 정확하게 ────────────────────────── */
  const y1 = d.section(G.L, 174, 556, 300, 1, '실적을 쌓아 더 정확하게',
                       '앞부터 배워 뒤를 맞혀 본 결과');
  const hi = Math.max(...BK.map(b => b.mae)) * 1.18;
  const YB = 372, BW = 88;
  BK.forEach((b, i) => {
    const x = 116 + i * 116, h = Math.round(b.mae / hi * 128), y = YB - h;
    /* 첫 구간보다 **뚜렷하게** 나아진 구간만 빨강. 둘째 구간은 2.259 로
       첫 구간(2.264)보다 0.005 낮을 뿐이라 좋아졌다고 색을 줄 수 없다.
       흔들림보다 작은 차이에 색을 주면 장표가 거짓말을 한다. */
    const good = BK[0].mae - b.mae > 0.1;
    d.rect(x, y, BW, h, good ? C.brass : C.slate);
    d.text(b.mae.toFixed(2), { x, y: y - 22, w: BW, px: 15, lh: 1.2, mono: true,
                               bold: true, color: good ? C.brass : C.slateL,
                               align: 'center' });
    d.text(b.from + '~' + b.to + '회', { x, y: YB + 8, w: BW, px: 11, lh: 1.25,
                                          color: C.dim, align: 'center' });
  });
  d.hline(96, YB, 512, C.rule, 1);
  d.text('세로 — 틀리는 폭 (MW, 작을수록 좋다)',
         { x: 92, y: y1, w: 300, px: 10.5, lh: 1.25, color: C.dim2 });
  /* 줄을 직접 끊는다 — 칸 폭에 맡기면 '입니다' 가 갈려 다음 줄로 떨어진다.
     한 문자열 안에서 \n 과 강조 마크업(*…*)을 같이 쓰면 안 된다. pptxgenjs 가
     \n 에서 단락을 끊을 때 뒤따르는 런을 새 단락으로 밀어 버려서, 강조한
     숫자만 혼자 다음 줄로 내려간다(생성된 XML 로 확인). 그래서 줄마다
     따로 부른다. */
  [['시험이 늘어난 것 말고 바꾼 것은 없습니다.', 394],
   ['처음에는 평균 *' + L.first.toFixed(2) + ' MW* 틀렸고, 지금은 *' +
    L.last.toFixed(2) + ' MW* 입니다.', 414],
   ['앞으로도 2주마다 한 회씩 쌓입니다.', 434]]
    .forEach(([t, y]) => d.text(t, { x: 92, y, w: 516, px: 12.5, lh: 1.45,
                                     color: C.body }));
  d.text('마지막 구간이 조금 올라간 것은 겨울 시험이 적게 섞인 탓입니다. 있는 대로 적었습니다.',
         { x: 92, y: 456, w: 516, px: 10.5, lh: 1.3, color: C.dim2 });

  /* ── 구획 2 · 다른 발전소로. 기종이 달라도 되는 이유 ──────────── */
  const y2 = d.section(644, 174, 564, 300, 2, '다른 발전소로', '기종이 달라도 됩니다');
  d.text('다른 발전소는 기종이 달라 특성 곡선이 다릅니다.',
         { x: 664, y: y2, w: 524, px: 12.5, lh: 1.4, color: C.dim });
  d.rect(664, y2 + 26, 4, 24, C.brass);
  d.text('옮겨 가는 것은 곡선이 아니라 *절차*입니다.',
         { x: 682, y: y2 + 24, w: 506, px: 15.5, lh: 1.3, bold: true, color: C.ink });
  [['특성 곡선은 표 파일로 읽는다',
    '도구가 곡선을 품고 있지 않습니다. 온도 61줄 표를 읽어 씁니다. 그 발전소 표로 ' +
    '바꿔 넣으면 됩니다 — 제작사 계산식은 손대지 않았습니다.'],
   ['보정 곡선은 새로 쌓는다',
    '위례가 시험 ' + D.n + '회로 만든 것처럼, 그 발전소는 그 발전소 실적으로 ' +
    '만듭니다.'],
   ['그래서 필요한 것은 셋',
    '도구 · 그 발전소 특성 곡선표 · 그 발전소 시험 실적.']]
    .forEach(([k, v], i) => {
      const y = y2 + 56 + i * 68;
      d.text(String(i + 1), { x: 664, y: y + 2, w: 16, px: 11.5, lh: 1.2, mono: true,
                              bold: true, color: C.brass });
      d.text(k, { x: 686, y, w: 502, px: 13.5, lh: 1.25, bold: true, color: C.ink });
      d.text(v, { x: 686, y: y + 20, w: 502, px: 11.5, lh: 1.35, lines: 3, color: C.dim });
    });

  /* ── 구획 3 · 언제 무엇을 ─────────────────────────────────────── */
  const y3 = d.section(G.L, 486, G.W, 154, 3, '언제 무엇을', '');
  [['지금', '위례에 정착', '2주마다 시험하고 결과를 넣습니다. 쌓일수록 곡선이 촘촘해집니다.'],
   ['다음', '같은 구조 발전소로', '곡선표를 그 발전소 것으로 바꿔 넣고, 그 발전소 실적으로 보정 곡선을 새로 쌓습니다.'],
   ['그다음', '절차로 굳히기', '신고 숫자를 내는 순서를 사업소 표준으로 정리합니다.']]
    .forEach(([when, what, why], i) => {
      const x = 92 + i * 368;
      d.text(when, { x, y: y3, w: 90, px: 11, lh: 1.2, mono: true, bold: true,
                     color: C.brass, cs: 1.2 });
      d.text(what, { x, y: y3 + 18, w: 340, px: 15.5, lh: 1.25, bold: true, color: C.ink });
      d.text(why, { x, y: y3 + 42, w: 340, px: 11.5, lh: 1.35, lines: 3, color: C.dim });
      if (i < 2) d.vline(x + 352, y3 - 2, 100, C.rule2, 1);
    });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '한 번 만들고 끝나는 도구가 아닙니다. 쓸수록 촘촘해지고, 옮겨 심을 수 있습니다.');
};
