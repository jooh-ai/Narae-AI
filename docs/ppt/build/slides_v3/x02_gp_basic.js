/* 부록 x02 · 가우시안 프로세스란 — 개념 한 장 (프로젝트와 무관)

   2026-09-22 회신이 이 장을 만들게 했다.
     "나는 이 프로젝트와 상관 없이 모델에 정의 및 어떤 경우에 사용하면
      좋은지, 이 모델은 어떨때 좋고 어떨때 단점이 있다 등등의 개념 정리가
      필요한데, 너가 작성한건 이 프로젝트와 연관해서 설명 하다 보니
      내가 이해 및 설명하기가 쉽지 않더라고. 회귀 모델을 처음 배우는
      사람이 자료를 찾아서 공부 하듯이"

   그래서 첫 판(x01_model.js)과 달리 위례 실적을 쓰지 않는다. 데이터는
   gp_concept.py 가 만든 교과서 예시다 — sin 곡선에 잡음을 얹고 가운데를
   비워 두었다. 우리 실적으로는 커널을 바꿔도 곡선이 거의 같아서 개념
   차이가 그림에 드러나지 않았다(그것이 첫 판이 어려웠던 까닭이다).

   이 장은 GP 가 무엇인가만 말한다. 커널 이야기는 다음 장(x03)이다.   */
'use strict';
const D = require('../gp_concept.json');
const plot = require('./_gplot.js');

module.exports = (pptx, T, meta, DATA) => {
  const { C, G, LW } = T;
  const { d } = T.shell(pptx, { sec: '참고 · 회귀 모델', page: false });
  const xs = D.x;
  const band = (m, s, k) => ({ lo: m.map((v, i) => v - k * s[i]),
                               hi: m.map((v, i) => v + k * s[i]) });
  const R = { x0: 0, x1: 10, y0: -2.6, y1: 2.6 };

  T.title(d, '가우시안 프로세스 (GP) 란', null, { px: 33 });
  T.lead(d, '곡선 하나를 고르는 대신, 가능한 곡선 전체를 다루는 회귀 방법입니다.',
         { y: 134, lines: 1 });

  /* ── 구획 1 · 세 걸음 그림 ─────────────────────────────────────── */
  const y1 = d.section(G.L, 168, G.W, 300, 1, '곡선 하나가 아니라 곡선의 무리',
                       '예시 데이터 · 점 ' + D.obs.length + '개');
  const PW = 352, PH = 176, GAP = 26;
  const STEP = [
    ['① 관측 전', '커널만 정하면 이런 곡선들이 후보가 됩니다',
     g => ({ lines: D.prior.map(v => ({ v, color: C.slate, w: 1 })) })],
    ['② 관측 뒤', '점을 지나는 곡선만 남습니다',
     g => ({ lines: D.post_draws.map(v => ({ v, color: C.slateL, w: 1 })),
             dots: D.obs })],
    ['③ 답', '남은 곡선의 평균과 95% 범위를 냅니다',
     g => ({ band: Object.assign(band(D.post_mean, D.post_sd, 1.96),
                                 { color: C.brassD, fill: C.brassS }),
             lines: [{ v: D.truth, color: C.slateL, w: 1, dash: 'dash' },
                     { v: D.post_mean, color: C.brass, w: LW.main }],
             dots: D.obs })],
  ];
  STEP.forEach(([head, note, mk], i) => {
    const x = 92 + i * (PW + GAP);
    d.text(head, { x, y: y1, w: PW, px: 13.5, lh: 1.25, bold: true, color: C.ink });
    plot(d, T, x, y1 + 22, PW, PH, xs, Object.assign({}, R, mk(), { zero: true }));
    d.text(note, { x, y: y1 + PH + 26, w: PW, px: 11, lh: 1.35, lines: 2,
                   color: C.dim });
  });
  d.text('*가운데가 비어 있는 것을 보십시오* — 점이 없는 구간에서는 곡선들이 흩어져 ' +
         '범위가 넓어집니다. 모르는 곳을 모른다고 말하는 것이 GP 의 성질입니다.',
         { x: 92, y: y1 + PH + 62, w: 1096, px: 11.5, lh: 1.4, color: C.body });

  /* ── 구획 2 · 정의와 특징 ──────────────────────────────────────── */
  const y2 = d.section(G.L, 478, 556, 162, 2, '정의와 특징', '');
  [['정의',
    '어떤 입력들을 골라도 그 함수값들이 정규분포를 이루는 확률 과정입니다. ' +
    '평균 함수와 커널 둘로 정해집니다.'],
   ['특징',
    '식의 모양을 미리 정하지 않습니다(비모수). 데이터가 늘면 모델도 같이 자라고, ' +
    '예측이 값이 아니라 분포로 나옵니다.']]
    .forEach(([k, v], i) => {
      const y = y2 + i * 60;
      d.rect(92, y + 2, 3, 44, C.brass);
      d.text(k, { x: 106, y, w: 80, px: 12.5, lh: 1.25, bold: true, color: C.ink });
      d.text(v, { x: 106, y: y + 20, w: 508, px: 11, lh: 1.42, lines: 2, color: C.dim });
    });

  /* ── 구획 3 · 장점 · 단점 · 언제 ──────────────────────────────── */
  const y3 = d.section(644, 478, 564, 162, 3, '장점 · 단점 · 언제 쓰나', '');
  [['좋은 점', C.brass,
    '데이터가 적어도 씁니다 · 불확실성을 숫자로 냅니다 · 커널로 사전 지식을 넣습니다'],
   ['아쉬운 점', C.red,
    '계산이 데이터 수의 세제곱으로 늘어 수천 건이 넘으면 무겁습니다 · ' +
    '커널을 잘못 고르면 결과가 달라집니다 · 입력 변수가 많으면 약합니다'],
   ['쓰기 좋은 곳', C.slateL,
    '데이터가 수십~수천 건이고 입력이 한두 개일 때 · 값과 함께 신뢰 범위가 ' +
    '필요할 때 · 다음 실험을 어디서 할지 고를 때']]
    .forEach(([k, col, v], i) => {
      const y = y3 + i * 42;
      d.text(k, { x: 664, y, w: 76, px: 11.5, lh: 1.25, bold: true, color: col });
      d.text(v, { x: 748, y, w: 440, px: 10.8, lh: 1.4, lines: 2, color: C.dim });
    });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '값 하나가 아니라 "이 범위 안에 있을 것" 까지 내놓는 것이 GP 의 핵심입니다.');
};
