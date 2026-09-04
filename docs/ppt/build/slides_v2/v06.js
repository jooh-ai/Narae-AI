/* v2-06 · 데이터 분석 및 원인 규명 (1/2) — 요소 2개: 3단 좁히기 막대 / 결론.
   요지: 후보 넷이 다 원인처럼 보였지만 서로 온도에 묶여 있었다. 온도를 걷어
   내면 셋 다 사라지고, 습도만 ②에서 남는데 그것도 온도를 '곡선' 으로 빼면
   사라진다. 이 마지막 한 걸음이 다음 장(커널로 곡선을 학습)의 근거다.

   숫자는 refresh_data.causes 에서 온다. ③의 정의는 vacuum_effect_check.py ③
   과 같다 — 두 곳이 다른 정의를 쓰면 문서끼리 숫자가 어긋난다.             */
'use strict';
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  const { d } = T.shell(pptx, { sec: '원인 규명', idx: 3, step: 3 });
  const Z = D.causes, RC = Z.rcrit;
  const cit = Z.rows.find(r => r.key === 'cit');
  const cand = Z.rows.filter(r => r.key !== 'cit');
  T.title(d, '원인처럼 보이는 것이 넷이었는데,', '온도를 걷어내니 *하나만 남았습니다*');
  T.lead(d, '그럴듯한 설명 5개를 세워 하나씩 확인했고 *4개는 기각*했습니다. ' +
         '후보들이 서로 _온도에 묶여_ 있었기 때문입니다.', { lines: 1 });

  d.zone(G.L, 284, G.W, 204);
  d.plab('보정값과의 관련성  ·  상관계수 r  ·  0 에 가까우면 관계 없음', 96, 294, 620);
  d.text('임계 ±' + RC.toFixed(2) + ' — 이 선을 넘지 못하면 우연으로 봅니다 (n=' + Z.n + ')',
         { x: 760, y: 292, w: 424, px: 11.5, lh: 1.2, color: C.red, align: 'right' });

  /* 범례 = 좁혀 간 3단계 그 자체다. ③ 은 막대로 그리지 않고 오른쪽 숫자로
     말한다 — 한 줄에 막대 3개를 넣으면 값 라벨이 서로 부딪힌다. */
  [[96, C.slate, '① 그냥 봤을 때', 150], [286, C.steel, '② 온도를 직선으로 뺀 뒤', 210]]
    .forEach(([x, col, s, w]) => {
      d.rect(x, 320, 18, 8, col);
      d.text(s, { x: x + 24, y: 314, w, px: 12, lh: 1.2, color: col });
    });
  d.text('③ 온도를 곡선(모델)으로 뺀 뒤  =  오른쪽 숫자',
         { x: 760, y: 314, w: 424, px: 12, lh: 1.2, color: C.brass, align: 'right' });
  d.text('※ \'뺀다\' = 온도로 설명되는 몫을 먼저 걷어내고, 남은 것끼리 다시 재는 것',
         { x: 96, y: 496, w: 700, px: 11, lh: 1.2, color: C.dim2 });

  const BX = v => 300 + Math.abs(v) * 640;
  d.vline(300, 344, 138, C.rule, 1);
  d.vline(BX(RC), 344, 138, C.red, 1.6, 'dash');

  /* 온도 — 답이므로 굵은 막대 하나로 따로 세운다 */
  d.text('외기온도', { x: 96, y: 347, w: 190, px: 15, lh: 1.3, bold: true, color: C.brass });
  d.rect(300, 346, BX(cit.raw) - 300, 15, C.brass);
  d.text(cit.raw.toFixed(2), { x: BX(cit.raw) + 8, y: 345, w: 70, px: 15, lh: 1.2,
                               mono: true, bold: true, color: C.brass });
  d.text('★ 주된 원인', { x: 980, y: 347, w: 204, px: 13, lh: 1.2, bold: true,
                          color: C.brass, align: 'right' });
  d.hline(96, 372, 1088, C.rule, 1);

  cand.forEach((r, i) => {
    const y = 376 + i * 34;
    d.text(r.label, { x: 96, y: y + 4, w: 190, px: 14, lh: 1.3, color: C.body });
    [[r.raw, C.slate], [r.part, C.steel]].forEach(([v, col], k) => {
      const yy = y + k * 14;
      d.rect(300, yy, Math.max(BX(v) - 300, 2), 10, col);
      d.text((v >= 0 ? '+' : '−') + Math.abs(v).toFixed(2),
             { x: BX(v) + 8, y: yy - 1, w: 60, px: 11, lh: 1.2, mono: true, color: col });
    });
    const gone = Math.abs(r.model) < RC;
    d.text('③ ' + (r.model >= 0 ? '+' : '−') + Math.abs(r.model).toFixed(2) + ' → ' +
           (gone ? '사라짐' : '남음'),
           { x: 980, y: y + 4, w: 204, px: 12.5, lh: 1.2, bold: true,
             color: gone ? C.dim : C.red, align: 'right' });
  });
  /* 종전에는 label.slice(-3) 로 뒤 3글자만 잘라 '상대습도' 가 '대습도' 로 나왔다.
     짧은 이름을 따로 두고 쓴다. */
  const SHORT = { cp_meas: '진공도', press: '대기압', rh: '습도' };
  d.text('온도와의 r  ' + cand.map(r => (SHORT[r.key] || r.label) + ' ' +
         (r.vs_t >= 0 ? '+' : '−') + Math.abs(r.vs_t).toFixed(2)).join('   ·   ') +
         '  — 후보들이 서로 온도에 묶여 있다',
         { x: 96, y: 474, w: 1088, px: 11.5, lh: 1.2, mono: true, color: C.dim2 });

  /* 결론 — ②에서 습도가 남고 ③에서 사라진 것이 다음 장의 근거다 */
  d.zone(G.L, 502, G.W, 122);
  d.plab('그래서 무엇을 알았나', 96, 512, 300);
  [['진공도·대기압은 온도의 그림자였습니다',
    '① 에서 강해 보인 것은 이 둘이 온도를 따라가기 때문입니다. 온도를 빼면 사라집니다.'],
   ['습도는 ② 에서 남고 ③ 에서 사라졌습니다',
    '온도를 *직선*으로 빼면 남고, *곡선*으로 빼면 사라집니다 — 관계가 직선이 아니라는 뜻입니다.'],
   ['모델이 남긴 오차는 설명되지 않습니다',
    '평균 ' + Z.model_mae.toFixed(2) + ' MW 남은 오차를 넷 중 어느 것도 설명하지 ' +
    '못했습니다. 진공도는 세 번 의심해 세 번 다 기각했습니다.']]
    .forEach(([k, v], i) => {
      const x = 96 + i * 368, w = 344;
      d.rect(x, 534, 34, 2, C.brass);
      d.text(k, { x, y: 544, w, px: 14, lh: 1.3, bold: true, color: C.ink });
      d.text(v, { x, y: 570, w, px: 12.5, lh: 1.5, lines: 3, color: C.dim });
    });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '원인은 *온도* 하나 — 그런데 그 관계가 *직선이 아닙니다*. 그래서 곡선을 학습합니다.');
};
