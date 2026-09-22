/* 슬라이드 13 · 정량 효과
   종전 RMSE 4.488 은 36건 LOOCV flat 로 직접 계산한 값이다(MAE 3.833 과 같은 방식).
   설명력은 종전 방식에 대응값이 없어 빈칸으로 두고 각주로 밝힌다 — 만들지 않는다.
   시운전 4회차 실측은 계획서 §6 그대로.                                     */
'use strict';
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  const { d } = T.shell(pptx, { sec: '정량 효과', idx: 6, step: 6 });

  T.title(d, '한 지표만 좋아진 게 아닙니다 —', '*세 지표가 동시에* 좋아졌습니다');
  const I = D.impact, K = I.cut, CM = D.commission;
  const pct = (a, b) => Math.round((1 - a / b) * 100) + '% ↓';
  T.lead(d, '같은 ' + D.n + '회차를 _같은 방식으로 채점_ 해 종전과 나란히 놓았습니다. 그리고 시운전 ' +
         CM.n + '회차에서 다시 확인했습니다.');

  /* 좌 — 대조표 */
  d.panel(G.L, 288, 700, 'on');
  d.plab('종전 대비  ·  누적 ' + D.n + '회차를 한 건씩 가려 채점', G.L, 302, 700);
  d.zone(G.L, 322, 700, 240);
  ['지표', '종전', '개선', '나아진 폭'].forEach((h, i) => {
    const x = [88, 300, 440, 590][i], w = [200, 110, 110, 150][i];
    d.plab(h, x, 338, w, C.dim2);
  });
  d.hline(88, 358, 668, C.rule, 1);
  [['평균 오차', I.blanket.mae.toFixed(2), I.gp.mae.toFixed(2), K.mae + '% ↓'],
   ['큰 오차 가중', D.blanket.rmse.toFixed(2), D.best.rmse.toFixed(2), pct(D.best.rmse, D.blanket.rmse)],
   ['설명력', '—', (D.best.r2 >= 0 ? '+' : '') + D.best.r2.toFixed(2), '1에 가까울수록 좋음'],
   ['기준 미달 회차', String(I.blanket.short), String(I.gp.short), K.short + '% ↓'],
   ['과대 신고 누계', I.blanket.over.toFixed(1), I.gp.over.toFixed(1), K.over + '% ↓']]
    .forEach(([k, a, b, r], i) => {
      const y = 372 + i * 38;
      d.text(k, { x: 88, y, w: 200, px: 14, lh: 1.35, color: C.ink });
      d.text(a, { x: 300, y, w: 110, px: 15, lh: 1.3, mono: true, color: C.slateL, align: 'right' });
      d.text('→', { x: 418, y, w: 20, px: 12, lh: 1.4, color: C.dim2 });
      d.text(b, { x: 440, y: y - 1, w: 110, px: 17, lh: 1.25, mono: true, bold: true, color: C.brass, align: 'right' });
      d.text(r, { x: 590, y, w: 150, px: 13.5, lh: 1.35, mono: r.indexOf('%') > 0,
                  color: r.indexOf('%') > 0 ? C.brass : C.dim, align: 'right' });
      if (i < 4) d.hline(88, y + 30, 668, C.rule2, 1);
    });
  d.txt('오차는 MW, 미달은 회차, 과대 신고는 누계 MW 입니다. 설명력은 종전 방식에 대응하는 값이 없어 _비워 두었습니다_.',
        G.L, 578, 700, 2);

  /* 우 — 시운전 실측 */
  d.panel(812, 288, 396, null);
  d.plab('시운전 실측  ·  ' + CM.n + '회차  ·  ' + CM.from.slice(2) + ' ~ ' + CM.to.slice(2),
         812, 302, 396);
  d.zone(812, 322, 396, 152);
  [['치우침', (CM.me >= 0 ? '+' : '−') + Math.abs(CM.me).toFixed(2), 'MW'],
   ['평균 오차', CM.mae.toFixed(2), 'MW'],
   ['큰 오차 가중', CM.rmse.toFixed(2), 'MW'],
   ['종전 대비 개선율', (CM.skill * 100).toFixed(1), '%']]
    .forEach(([l, v, u], i) => {
      const x = 828 + (i % 2) * 192, y = 338 + Math.floor(i / 2) * 70;
      d.plab(l, x, y, 180);
      d.bigUnit(v, u, x, y + 20, 24);
    });
  d.sub('학습에 쓰지 않은 회차에서도 *같은 수준*', 812, 494, 396, 2);
  d.txt('시운전 ' + CM.n + '회차는 학습에 넣지 않고 예측만 했습니다. 누적 ' + D.n +
        '회차 채점과 비슷하게 나왔습니다.', 812, 562, 396, 3);

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '한 지표를 좋게 만들려고 다른 지표를 희생하지 않았습니다 — *전부 같은 방향*으로 움직였습니다.');
};
