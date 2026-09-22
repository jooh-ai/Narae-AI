/* 부록 x03 · 커널이 결과를 바꾼다 — 개념 한 장 (프로젝트와 무관)

   x02 가 "GP 가 무엇인가" 라면 이 장은 "무엇을 정해 줘야 하는가" 다.
   커널 세 가지와, GP 가 아닌 이웃(커널회귀)을 같은 데이터에 얹어 결과가
   어떻게 달라지는지 보인다. 마지막에 길이척도 하나만 더 다룬다 —
   커널을 골라도 이 값을 잘못 잡으면 그림이 망가지기 때문이다.

   데이터는 gp_concept.py 의 교과서 예시다. 거칠기(2차 차분 합)는 장표가
   JSON 에서 직접 재서 적는다 — 손으로 적어 두면 데이터가 바뀔 때 장표만
   옛말이 된다.                                                          */
'use strict';
const D = require('../gp_concept.json');
const plot = require('./_gplot.js');

function rough(v) {
  let s = 0;
  for (let i = 1; i < v.length - 1; i++) s += Math.abs(v[i - 1] - 2 * v[i] + v[i + 1]);
  return s;
}

module.exports = (pptx, T, meta, DATA) => {
  const { C, G, LW } = T;
  const { d } = T.shell(pptx, { sec: '참고 · 회귀 모델', page: false });
  const xs = D.x;
  const K = D.kern;
  const band = (m, s, k) => ({ lo: m.map((v, i) => v - k * s[i]),
                               hi: m.map((v, i) => v + k * s[i]),
                               color: C.brassD, fill: C.brassS });
  const R = { x0: 0, x1: 10, y0: -2.2, y1: 2.2 };
  const rr = (rough(K.exp.mean) / rough(K.rbf.mean)).toFixed(1);

  T.title(d, '커널을 무엇으로 정하느냐가 곡선을 바꿉니다', null, { px: 30 });
  T.lead(d, '커널은 "두 입력이 얼마나 닮았는가" 를 정하는 함수입니다. 같은 데이터에 커널만 바꿨습니다.',
         { y: 132, lines: 1 });

  /* ── 구획 1 · 네 가지 ─────────────────────────────────────────── */
  const y1 = d.section(G.L, 166, G.W, 300, 1, '같은 점, 다른 커널',
                       '예시 데이터 · 점 ' + D.obs.length + '개 · 길이척도 ' + D.ell + ' 고정');
  const PW = 262, PH = 100, GAP = 20;
  const CARD = [
    ['GP · RBF (제곱지수)', '가장 많이 쓰는 기본',
     'k(r) = σ² exp( −r² / 2ℓ² )',
     '무한히 미분가능 — 어떤 자리에서도 매끄럽습니다.',
     '점 사이를 자연스럽게 잇습니다', '급한 꺾임은 따라가지 못합니다',
     K.rbf, C.brass],
    ['GP · Matérn 5/2', '실무 권장값',
     'k(r) = σ² (1 + a + a²/3) e⁻ᵃ,  a = √5 r/ℓ',
     '두 번 미분가능 — RBF 보다 조금 덜 매끄럽습니다.',
     '현실 데이터에 무난하게 맞습니다', 'RBF 보다 식이 복잡합니다',
     K.mat52, C.slateL],
    ['GP · 지수 (Matérn 1/2)', '',
     'k(r) = σ² exp( −r / ℓ )',
     '연속이지만 미분 불가 — 점마다 각이 집니다.',
     '급한 변화를 놓치지 않습니다', '잡음까지 따라가 ' + rr + '배 구불거립니다',
     K.exp, C.slateL],
    ['커널회귀 (Nadaraya–Watson)', 'GP 가 아닙니다',
     'y(x) = Σ wi·yi / Σ wi ,  wi = K((x−xi)/h)',
     '가까운 점에 무게를 더 준 가중평균입니다.',
     '셈이 단순하고 뜻이 바로 보입니다', '범위가 나오지 않습니다',
     null, C.slateL],
  ];
  CARD.forEach(([name, tag, eq, how, good, bad, kd, col], i) => {
    const x = 92 + i * (PW + GAP);
    d.text(name, { x, y: y1, w: PW, px: 12, lh: 1.25, bold: true, color: col });
    if (tag) d.text(tag, { x, y: y1 + 17, w: PW, px: 9.5, lh: 1.2, color: C.dim2 });
    const o = { lines: [{ v: D.truth, color: C.steel, w: 1, dash: 'dash' }],
                dots: D.obs };
    if (kd) {
      o.band = band(kd.mean, kd.sd, 1.96);
      o.lines.push({ v: kd.mean, color: col, w: 1.8 });
    } else {
      o.lines.push({ v: D.nw, color: col, w: 1.8 });
    }
    plot(d, T, x, y1 + 32, PW, PH, xs, Object.assign({}, R, o));
    d.text(eq, { x, y: y1 + 138, w: PW, px: 9.5, lh: 1.3, lines: 2,
                 mono: true, color: C.dim2 });
    d.text(how, { x, y: y1 + 166, w: PW, px: 10.5, lh: 1.35, lines: 2, color: C.dim });
    d.text('좋은 점', { x, y: y1 + 198, w: 52, px: 9.5, lh: 1.2, bold: true,
                        color: C.brass });
    d.text(good, { x: x + 54, y: y1 + 198, w: PW - 54, px: 10, lh: 1.3,
                   lines: 1, color: C.body });
    d.text('아쉬운 점', { x, y: y1 + 222, w: 56, px: 9.5, lh: 1.2, bold: true,
                          color: C.red });
    d.text(bad, { x: x + 58, y: y1 + 222, w: PW - 58, px: 10, lh: 1.3,
                  lines: 2, color: C.dim });
    if (i < 3) d.vline(x + PW + GAP / 2, y1 - 4, 250, C.rule2, 1);
  });

  /* ── 구획 2 · 길이척도 ────────────────────────────────────────── */
  const y2 = d.section(G.L, 486, G.W, 154, 2, '설정이 하나 더 있습니다 — 길이척도 ℓ',
                       '커널은 RBF 로 고정하고 ℓ 만 바꿨습니다');
  const LW2 = 300, LH2 = 74;
  [['ℓ = ' + D.ls.short.ell + ' (짧게)', D.ls.short, '가까운 점만 닮았다고 봅니다 — 잡음을 따라 출렁입니다'],
   ['ℓ = ' + D.ls.long.ell + ' (길게)', D.ls.long, '먼 점까지 닮았다고 봅니다 — 굴곡을 뭉갭니다']]
    .forEach(([head, ld, note], i) => {
      const x = 92 + i * (LW2 + 30);
      d.text(head, { x, y: y2, w: LW2, px: 11.5, lh: 1.2, bold: true, color: C.ink });
      plot(d, T, x, y2 + 18, LW2, LH2, xs, Object.assign({}, R, {
        lines: [{ v: D.truth, color: C.steel, w: 1, dash: 'dash' },
                { v: ld.mean, color: C.slateL, w: 1.6 }],
        dots: D.obs }));
      d.text(note, { x, y: y2 + LH2 + 22, w: LW2, px: 10, lh: 1.3, color: C.dim2 });
    });
  [['고르는 법', '눈으로 고르지 않습니다. 한 점을 가리고 나머지로 그 점을 맞혀 보는 ' +
    '교차검증으로 커널과 ℓ 을 함께 고릅니다.'],
   ['먼저 볼 것', '데이터가 매끄러운가 각진가 · 얼마나 떨어진 점까지 ' +
    '관련이 있는가 · 범위도 필요한가']]
    .forEach(([k, v], i) => {
      const y = y2 + 4 + i * 54;
      d.rect(748, y, 3, 42, C.brass);
      d.text(k, { x: 762, y: y - 2, w: 110, px: 11.5, lh: 1.2, bold: true, color: C.ink });
      d.text(v, { x: 762, y: y + 16, w: 426, px: 10.5, lh: 1.4, lines: 2, color: C.dim });
    });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '커널은 "데이터가 어떻게 생겼다고 보는가" 를 적어 넣는 자리입니다.');
};
