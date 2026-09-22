/* 부록 x04 · 회귀 방식 개념 한 장 (x02·x03 을 한 장으로 줄인 판)

   2026-09-22 3차 회신.
     "한장으로 요약하자. 두번째 장의 길이 척도 같은 개념은 사실 필요 없어.
      내가 원하는건 우리가 gp 커널회귀 지수 등의 여러 방식을 비교 사용하고
      이 여러방식의 개념이 어떤건지 간략하고 아주 쉽게 한장 정도로 설명하고
      넘어 가는게 주 목적이야."

   그래서 셋을 버렸다 — 길이척도, Matérn 5/2, GP 의 사전·사후 3단계 그림.
   대신 **단순한 것부터 정교한 것으로** 네 방식을 늘어놓는다. 순서가 곧
   설명이 되게 했다: 구간평균 → 커널회귀 → GP·지수 → GP·RBF.

   아래 구획은 "띠가 있는 둘이 GP 다" 한 마디로 GP 를 설명한다. 정의를
   따로 적는 대신 그림에서 이미 보이는 것(띠)을 가리키는 쪽이 빠르다.

   데이터는 gp_concept.py 의 교과서 예시다(프로젝트 실적이 아니다).    */
'use strict';
const D = require('../gp_concept.json');
const plot = require('./_gplot.js');

module.exports = (pptx, T, meta, DATA) => {
  const { C, G } = T;
  const { d } = T.shell(pptx, { sec: '참고 · 회귀 모델', page: false });
  const xs = D.x;
  const K = D.kern;
  const band = (m, s) => ({ lo: m.map((v, i) => v - s[i]),
                            hi: m.map((v, i) => v + s[i]),
                            color: C.brassD, fill: C.brassS });
  const R = { x0: 0, x1: 10, y0: -2.2, y1: 2.2 };

  T.title(d, '흩어진 점 사이로 선을 긋는 네 가지 방법', null, { px: 33 });
  T.lead(d, '같은 데이터를 놓고 방법만 바꿔 그렸습니다. 왼쪽이 가장 단순하고, 오른쪽으로 갈수록 정교해집니다.',
         { y: 134, lines: 1 });

  /* ── 구획 1 · 네 방식 ─────────────────────────────────────────── */
  const y1 = d.section(G.L, 168, G.W, 302, 1, '단순한 것부터 정교한 것까지',
                       '예시 데이터 · 점선은 실제 값 · 검은 점은 측정값 · 연한 띠는 예측 범위');
  const PW = 262, PH = 104, GAP = 20;
  const CARD = [
    ['구간평균', '가장 단순',
     { lines: [{ v: D.bin, color: C.slateL, w: 1.8 }] },
     '구간을 나누고, 그 안의 점을 평균 냅니다.',
     '계산이 단순해서 설명하기 쉽습니다',
     '구간이 바뀌면 값이 뚝 끊깁니다 · 점이 없으면 값도 없습니다',
     C.slateL],
    ['커널회귀', '가까운 점 위주',
     { lines: [{ v: D.nw, color: C.slateL, w: 1.8 }] },
     '가까운 점은 많이, 먼 점은 적게 반영합니다.',
     '선이 끊기지 않고 이어집니다',
     '값 하나만 나옵니다 · 그 값이 얼마나 맞는지는 알 수 없습니다',
     C.slateL],
    ['GP · 지수', '여기서부터 GP',
     { band: band(K.exp.mean, K.exp.sd),
       lines: [{ v: K.exp.mean, color: C.body, w: 1.8 }] },
     '바로 옆 점하고만 값이 비슷하다고 봅니다.',
     '값이 갑자기 변해도 따라갑니다',
     '튀는 값까지 따라가 선이 출렁입니다',
     C.body],
    ['GP · RBF', '우리가 고른 것',
     { band: band(K.rbf.mean, K.rbf.sd),
       lines: [{ v: K.rbf.mean, color: C.brass, w: 2 }] },
     '조금 떨어진 점까지 값이 비슷하다고 봅니다.',
     '점이 없는 구간도 무리 없이 이어 줍니다',
     '값이 갑자기 꺾이는 곳은 놓칩니다',
     C.brass],
  ];
  CARD.forEach(([name, tag, art, how, good, bad, col], i) => {
    const x = 92 + i * (PW + GAP);
    d.text(name, { x, y: y1, w: 150, px: 15, lh: 1.25, bold: true, color: col });
    d.text(tag, { x: x + 150, y: y1 + 4, w: PW - 150, px: 10, lh: 1.2,
                  color: C.dim2, align: 'right' });
    const o = Object.assign({ dots: D.obs }, art);
    o.lines = [{ v: D.truth, color: C.steel, w: 1, dash: 'dash' }].concat(o.lines);
    plot(d, T, x, y1 + 26, PW, PH, xs, Object.assign({}, R, o));
    d.text(how, { x, y: y1 + 140, w: PW, px: 11, lh: 1.4, lines: 2, color: C.dim });
    d.text('좋은 점', { x, y: y1 + 186, w: 52, px: 10, lh: 1.2, bold: true,
                        color: C.brass });
    d.text(good, { x: x + 58, y: y1 + 186, w: PW - 58, px: 10.5, lh: 1.3,
                   lines: 2, color: C.body });
    d.text('아쉬운 점', { x, y: y1 + 224, w: 56, px: 10, lh: 1.2, bold: true,
                          color: C.red });
    d.text(bad, { x: x + 60, y: y1 + 224, w: PW - 60, px: 10.5, lh: 1.3,
                  lines: 3, color: C.dim });
    if (i < 3) d.vline(x + PW + GAP / 2, y1 - 4, 254, C.rule2, 1);
  });
  /* ── 구획 2 · GP 는 무엇이 다른가 ─────────────────────────────── */
  const y2 = d.section(G.L, 498, G.W, 98, 2, '연한 띠가 있는 둘이 GP 입니다',
                       '가우시안 프로세스 · 앞의 두 방법과 갈라지는 지점');
  [['선을 하나만 긋지 않습니다',
    '점을 지나는 선을 여러 개 그리고, 그 평균을 답으로 냅니다.'],
   ['그래서 범위가 같이 나옵니다',
    '선이 여러 개니 위아래로 범위가 생깁니다. 그것이 연한 띠입니다.'],
   ['커널이 선의 성격을 정합니다',
    '얼마나 떨어진 점까지 비슷하게 볼지를 정하는 것이 커널입니다.']]
    .forEach(([k, v], i) => {
      const x = 92 + i * 372;
      d.rect(x, y2 + 2, 3, 38, C.brass);
      d.text(k, { x: x + 14, y: y2, w: 330, px: 12.5, lh: 1.25, bold: true,
                  color: C.ink });
      d.text(v, { x: x + 14, y: y2 + 22, w: 330, px: 10.8, lh: 1.42, lines: 3,
                  color: C.dim });
    });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '우리는 이 넷을 포함한 일곱 가지를 같은 데이터로 시험해 보고 골랐습니다.');
};
