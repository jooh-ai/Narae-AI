/* v3-04 · 문제점.

   4차. 회신 두 가지를 반영했다.
     "BLT 사진이 너무 허접한데, 차라리 표로 하는게 낫지 않나?"
     "텍스트가 너무 다 구어체야. 단순한 단어가 필요한 곳은 단어로."

   ① 엑셀 캡처를 걷어내고 **표**로 바꿨다. 다만 숫자만 늘어놓으면 읽어야 하므로
      각 행에 막대를 붙였다. 놋빛 막대(실제 차이)는 들쭉날쭉하고 회색 막대
      (적용한 값)는 늘 짧고 비슷하다. 읽지 않아도 어긋난 것이 보인다.
      숫자는 legacy_log.json — 담당자 시트에서 옮겨 적은 기록이다.

   ② 말의 층을 나눴다. 제목과 라벨은 **단어**, 설명은 문장, 결론은 맨 아래 한 줄.
      앞 판은 전부 "~했습니다" 라서 어디가 중요한지 구분이 안 됐다.            */
'use strict';
const LOG = require('../legacy_log.json');
module.exports = (pptx, T, meta, D) => {
  const { C, G, LW } = T;
  const { d } = T.shell(pptx, { sec: '문제점', idx: 2, step: 2 });
  T.title(d, '문제점', null);
  T.lead(d, '시험 결과는 회차마다 달랐지만, 더해 주는 보정값은 거의 하나로 고정돼 있었습니다.',
         { y: 168, lines: 1 });

  /* 왼쪽 — 표. 행마다 막대 두 개. */
  d.zone(G.L, 226, 548, 402);
  d.plab('기존 실적 시트 기록', 92, 238, 240);
  d.text('MW', { x: 470, y: 237, w: 130, px: 10.5, lh: 1.2, mono: true, color: C.dim2,
                 align: 'right' });
  const Z = 232, K = 18.6;                        // 0 위치와 MW 당 픽셀
  const BX = v => Z + v * K;
  d.vline(Z, 258, 330, C.rule, 1);
  LOG.rows.forEach((r, i) => {
    const y = 266 + i * 25;
    d.text(r.date, { x: 92, y: y + 2, w: 58, px: 12, lh: 1.2, mono: true, color: C.dim,
                     align: 'right' });
    const g = BX(r.gap);
    d.rect(Math.min(Z, g), y, Math.max(Math.abs(g - Z), 2), 9, r.gap < 0 ? C.red : C.brass);
    d.rect(Z, y + 11, Math.max(BX(r.applied) - Z, 2), 5, C.slate);
    d.text(r.gap.toFixed(1), { x: 452, y: y + 1, w: 48, px: 12, lh: 1.2, mono: true,
                               bold: true, color: r.gap < 0 ? C.red : C.brass,
                               align: 'right' });
    d.text(String(r.applied), { x: 512, y: y + 1, w: 48, px: 12, lh: 1.2, mono: true,
                                color: C.slateL, align: 'right' });
  });
  d.rect(92, 600, 16, 8, C.brass);
  d.text('실제 차이', { x: 114, y: 597, w: 120, px: 11.5, lh: 1.2, color: C.dim });
  d.rect(240, 601, 16, 6, C.slate);
  d.text('적용한 보정값', { x: 262, y: 597, w: 140, px: 11.5, lh: 1.2, color: C.dim });

  /* 오른쪽 — 40회 전부 */
  d.zone(636, 226, 572, 402);
  d.plab('시험 ' + D.n + '회 전체', 656, 238, 240);
  d.text('가로 외기온도 ℃ / 세로 차이 MW', { x: 948, y: 237, w: 240, px: 10.5, lh: 1.2,
                                              color: C.dim2, align: 'right' });
  const X = t => 700 + (t + 3) * 11.3, Y = c => 288 + (14 - c) * 12.4;
  [12, 8, 4, -4].forEach(v => d.hline(X(-3), Y(v), 470, C.rule2, 1));
  d.hline(X(-3), Y(0), 470, C.rule, 1);
  [12, 8, 4, 0, -4].forEach(v => d.text((v > 0 ? '+' : '') + v,
    { x: 656, y: Y(v) - 7, w: 34, px: 10, lh: 1.2, mono: true, color: C.dim2,
      align: 'right' }));
  [0, 10, 20, 30].forEach(t => { d.vline(X(t), Y(-6), 5, C.dim2, 1);
    d.text(t === 0 ? '0℃' : String(t), { x: X(t) - 22, y: Y(-6) + 8, w: 44, px: 10,
      lh: 1.2, mono: true, color: C.dim2, align: 'center' }); });
  d.hline(X(-3), Y(D.blanket.flat), 470, C.slateL, LW.ref, 'dash');
  d.text('적용한 보정값', { x: X(22), y: Y(D.blanket.flat) - 20, w: 180, px: 11.5,
                            lh: 1.2, bold: true, color: C.slateL, align: 'right' });
  D.scatter.forEach(([t, c]) => d.dot(X(t), Y(c), 3.2, C.body));
  d.text('추울 때는 더 나오고 더울 때는 덜 나옵니다. 그 폭이 온도마다 달랐습니다.',
         { x: 656, y: 570, w: 540, px: 14, lh: 1.6, lines: 2, color: C.body });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '온도마다 다른 것을 하나로 맞추려니 맞을 수가 없었습니다.');
};
