/* 슬라이드 11 · 모니터링 — 스스로 갱신하는 체계
   신호등 판정 기준은 구간 건수: 5건 이상 충분(앰버) / 3~4 보통(슬레이트) /
   2건 이하 부족(레드). 새 색을 만들지 않고 기존 3색 뜻을 그대로 쓴다.      */
'use strict';
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  const { d } = T.shell(pptx, { sec: '모니터링', idx: 5, step: 5 });

  T.title(d, '회차가 쌓이면,', '*스스로 다시 고릅니다*');
  T.lead(d, '매주 받은 값이 검증을 통과하면 누적에 들어가고, 누적이 늘면 _다시 채점해 방식을 다시 고릅니다_. 사람이 손대는 지점이 없습니다.');

  /* 좌 — 순환 */
  d.panel(G.L, 288, 596, 'on');
  d.plab('갱신 순환', G.L, 302, 596);
  d.zone(G.L, 322, 596, 108);
  [[88, 100, '자동 취득'], [224, 105, '검증 가드'], [365, 105, '누적 반영'], [506, 140, '재학습·재선정']]
    .forEach(([x, w, s], i) => d.chip(s, x, 340, w, i === 3));
  [196, 337, 478].forEach(x => d.arrow(x, 347));
  d.seg(576, 378, 576, 400, C.brass, 1.4);
  d.seg(138, 400, 576, 400, C.brass, 1.4);
  d.seg(138, 378, 138, 400, C.brass, 1.4);
  d.text('▲', { x: 132, y: 370, w: 14, px: 9, lh: 1.1, color: C.brass });
  d.text('회차가 쌓일 때마다', { x: 300, y: 404, w: 200, px: 11.5, lh: 1.3, mono: true, color: C.dim2 });

  [['자동 취득', '설비에서 6가지 값을 직접 받습니다. 옮겨 적는 단계가 없습니다.'],
   ['검증 가드', 'IGV 미실시·습도계 이탈이면 그 회차는 누적에 넣지 않습니다.'],
   ['누적 반영', '통과한 회차만 학습 데이터가 됩니다. 이력은 그대로 남습니다.'],
   ['재학습·재선정', '누적이 늘면 7가지를 다시 채점해 1위를 다시 고릅니다.']]
    .forEach(([k, v], i) => {
      const y = 450 + i * 40;
      d.text(k, { x: G.L, y, w: 130, px: 13.5, lh: 1.35, bold: true, color: C.brass });
      d.text(v, { x: 210, y, w: 458, px: 13.5, lh: 1.35, color: C.body });
      if (i < 3) d.hline(G.L, y + 30, 596, C.rule2, 1);
    });

  /* 우 — 온도 구간 신호등 */
  d.panel(692, 288, 516, null);
  d.plab('온도 구간별 데이터 현황  ·  누적 ' + D.n + '회차', 692, 302, 516);
  d.zone(692, 322, 516, 238);
  const SC = 132 / Math.max(...D.bins.map(b => b.n));       // 최대 막대 132 px
  D.bins.map(b => [b.label, b.n])
    .forEach(([l, n], i) => {
      const y = 340 + i * 32;
      const st = n >= 5 ? ['충분', C.brass] : n >= 3 ? ['보통', C.slateL] : ['부족', C.red];
      d.rect(708, y + 4, 10, 10, st[1]);
      d.text(l, { x: 730, y: y + 1, w: 96, px: 12.5, lh: 1.3, mono: true, color: C.body });
      d.rect(840, y + 4, n * SC, 10, st[1] === C.brass ? C.brassD : st[1] === C.red ? C.redD : C.rule);
      d.text(String(n) + '건', { x: 990, y: y + 1, w: 50, px: 12.5, lh: 1.3, mono: true, color: C.dim });
      d.text(st[0], { x: 1120, y: y + 1, w: 72, px: 12.5, lh: 1.3, bold: true, color: st[1], align: 'right' });
    });
  d.txt('_부족한 구간은 화면에 그대로 뜹니다_ — 그 구간의 값은 아직 믿지 말라는 표시입니다.',
        692, 576, 516, 2);

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '한 번 만들고 끝나는 모델이 아닙니다 — *회차가 쌓일수록 좋아집니다*.');
};
