/* 부록 x01 · 회귀 모델이 하는 일 — 따로 뽑아 끼워 넣는 한 장.

   2026-09-21 회신: "우리가 결론적으로 사용하는 회귀모델에 대한 설명을 할 수
   있는 PPT가 한장 정도만 있으면 좋겠다. 7가지를 다 설명할 필요는 없고,
   GP 가 뭔지, RBF 가 뭔지, 지수가 뭔지, 커널회귀가 뭔지. 너무 말로만 설명하면
   어려우니 그래프·차트로 각 모델의 특징이나 장·단점을 쉽게."

   곡선은 **손으로 그린 예시가 아니라 우리 실적으로 뽑은 것**이다
   (`model_curves.py` → `model_curves.json`). 같은 시험 40회에 방법만 바꿔
   그렸으므로 장표의 그림이 곧 우리 데이터의 사실이다. 그래서 "지수는 더
   구불거린다" 같은 말을 숫자로 뒷받침할 수 있다 — 거칠기는 곡선의 2차 차분
   합으로 재고, 배수도 데이터에서 계산해 적는다.

   본편 13장에 넣지 않고 따로 둔다. 발표에서 "그 모델이 뭡니까" 를 물어 왔을
   때 띄우는 장이다.                                                      */
'use strict';
const MC = require('../model_curves.json');

/* 곡선이 얼마나 구불거리는지 — 2차 차분의 합. 눈으로 보이는 것을 숫자로
   뒷받침하려고 장표에서 직접 잰다(값을 손으로 적어 두면 데이터가 바뀔 때
   장표만 옛말이 된다). */
function rough(v) {
  let s = 0;
  for (let i = 1; i < v.length - 1; i++) s += Math.abs(v[i - 1] - 2 * v[i] + v[i + 1]);
  return s;
}

module.exports = (pptx, T, meta, D) => {
  const { C, G, LW } = T;
  const { d } = T.shell(pptx, { sec: '참고', page: false });
  const t = MC.t;
  /* 자(축) 둘.
     FULL  전 구간 −4 ~ 40℃ — GP 를 설명하는 큰 그림.
     ZOOM  20 ~ 40℃ 를 확대 — 세 방법의 차이가 가장 크게 벌어지는 자리다
           (벌어짐 1.9 MW · 거칠기 차 5.2). 전 구간으로 그리면 세로 19 MW 를
           54px 에 담게 되어 0.7 MW 차이가 2px 로 뭉개진다. 미리보기로 세 그림이
           똑같아 보이는 것을 확인하고 창을 좁혔다. 확대했다는 것은 구획 이름
           옆에 밝힌다.                                                      */
  const FULL = { t0: t[0], t1: t[t.length - 1], c0: -5.5, c1: 13.5 };
  const ZOOM = { t0: 20, t1: 40, c0: -5.2, c1: 4.2 };

  T.title(d, '회귀 모델이 하는 일', null, { px: 33 });
  T.lead(d, '시험 결과 점들을 지나는 곡선을 찾는 일입니다. 그 곡선을 어떻게 긋느냐가 방법의 차이입니다.',
         { y: 134, lines: 1 });

  /* 그림 하나를 그리는 함수 — 큰 그림과 작은 그림 셋이 같은 자를 쓴다.
     band 를 주면 90% 띠를 점선 두 줄로 두른다(면을 칠하면 작은 그림에서
     점이 묻힌다).                                                        */
  const plot = (x, y, w, h, key, R, opt) => {
    opt = opt || {};
    const X = tt => x + 10 + (tt - R.t0) / (R.t1 - R.t0) * (w - 20);
    const Y = c => y + h - 12 - (c - R.c0) / (R.c1 - R.c0) * (h - 22);
    const clip = c => Math.max(R.c0, Math.min(R.c1, c));
    const inT = tt => tt >= R.t0 && tt <= R.t1;
    d.box(x, y, w, h, null, C.rule2, 1);
    d.hline(X(R.t0), Y(0), X(R.t1) - X(R.t0), C.rule, 1);          // 0 선
    if (opt.band) {
      const B = MC.band;
      for (const side of ['lo', 'hi'])
        for (let i = 0; i < t.length - 1; i++) {
          if (B[side][i] == null || B[side][i + 1] == null) continue;
          if (!inT(t[i]) || !inT(t[i + 1])) continue;
          d.seg(X(t[i]), Y(B[side][i]), X(t[i + 1]), Y(B[side][i + 1]),
                C.brassD, 1, 'dash');
        }
    }
    MC.scatter.forEach(([tt, c]) => {
      if (!inT(tt)) return;
      d.dot(X(tt), Y(clip(c)), opt.big ? 2.6 : 1.8, C.body);
    });
    const v = MC[key];
    for (let i = 0; i < t.length - 1; i++)
      if (v[i] != null && v[i + 1] != null && inT(t[i]) && inT(t[i + 1]))
        d.seg(X(t[i]), Y(v[i]), X(t[i + 1]), Y(v[i + 1]),
              opt.dim ? C.slateL : C.brass, opt.big ? LW.main : 1.8);
    (opt.xt || []).forEach(tt => d.text(String(tt) + '℃',
      { x: X(tt) - 20, y: y + h - 12, w: 40, px: 9.5, lh: 1.2, mono: true,
        color: C.dim2, align: 'center' }));
    (opt.yt || []).forEach(c => d.text((c > 0 ? '+' : '') + c,
      { x: x - 26, y: Y(c) - 6, w: 24, px: 9.5, lh: 1.2, mono: true,
        color: C.dim2, align: 'right' }));
  };

  /* ── 구획 1 · GP 가 무엇인가 ──────────────────────────────────── */
  const y1 = d.section(G.L, 168, G.W, 218, 1, 'GP (가우시안 프로세스)',
                       '우리가 쓰는 방법 · 점 ' + MC.n + '개는 실제 시험');
  plot(118, y1, 494, 162, 'rbf', FULL, { big: true, band: true,
                                         xt: [0, 20, 40], yt: [0, 5] });
  d.text('가로 외기온도 ℃ · 세로 더하는 값 MW · 빨간 선이 도구가 쓰는 곡선',
         { x: 118, y: y1 + 168, w: 494, px: 10, lh: 1.2, color: C.dim2 });
  [['곡선을 하나만 고르지 않습니다',
    '점들을 지날 수 있는 곡선을 모두 놓고, 그 한가운데를 답으로 냅니다.'],
   ['그래서 범위가 같이 나옵니다',
    '연한 점선 두 줄이 90% 범위입니다. 값 하나만 내놓는 방법에는 없는 것입니다.'],
   ['커널은 곡선의 성격입니다',
    '얼마나 부드럽게 그을지 정하는 설정입니다. 아래 셋이 그 차이입니다.']]
    .forEach(([k, v], i) => {
      const y = y1 + i * 58;
      d.rect(648, y + 2, 4, 40, C.brass);
      d.text(k, { x: 666, y, w: 516, px: 14, lh: 1.25, bold: true, color: C.ink });
      d.text(v, { x: 666, y: y + 20, w: 516, px: 11, lh: 1.4, lines: 2, color: C.dim });
    });

  /* ── 구획 2 · 커널을 바꾸면 ───────────────────────────────────── */
  const y2 = d.section(G.L, 398, G.W, 242, 2, '긋는 방법 셋 · 곡선의 성격이 이렇게 다릅니다',
                       '같은 시험 ' + MC.n + '회 · 차이가 가장 큰 20~40℃ 를 확대');
  const rr = (rough(MC.exp) / rough(MC.rbf)).toFixed(1);
  const gap = Math.max(...MC.rbf.map((a, i) => Math.abs(a - MC.curve[i]))).toFixed(1);
  const CARD = [
    ['rbf', 'GP · RBF (제곱지수)', '우리가 쓰는 것',
     '가까운 온도끼리는 아주 비슷하다고 봅니다. 그래서 가장 매끄럽게 이어집니다.',
     '시험이 없는 온도도 자연스럽게 메웁니다',
     '갑작스러운 꺾임은 따라가지 못합니다', false],
    ['exp', 'GP · 지수 (Matérn 1/2)', '',
     '바로 옆 점만 보고 따라갑니다. 그래서 각지고 구불거립니다.',
     '급한 변화도 놓치지 않습니다',
     '잡음까지 따라가 ' + rr + '배 더 구불거립니다', true],
    ['curve', '커널회귀', 'GP 가 아닌 것',
     '그 온도 가까이에 있는 시험들의 평균입니다. 가까울수록 무게를 더 줍니다.',
     '셈이 단순하고 뜻이 바로 보입니다',
     '범위가 나오지 않습니다 · RBF 와 최대 ' + gap + ' MW 차이', true],
  ];
  CARD.forEach(([key, name, tag, how, good, bad, dim], i) => {
    const x = 92 + i * 368;
    d.text(name, { x, y: y2, w: 250, px: 14, lh: 1.25, bold: true,
                   color: dim ? C.body : C.brass });
    if (tag) d.text(tag, { x: x + 254, y: y2 + 3, w: 94, px: 10, lh: 1.2,
                           color: C.dim2, align: 'right' });
    plot(x, y2 + 22, 348, 96, key, ZOOM, { dim, xt: [20, 40] });
    d.text(how, { x, y: y2 + 124, w: 348, px: 10.5, lh: 1.35, lines: 2, color: C.dim });
    d.text('좋은 점', { x, y: y2 + 158, w: 52, px: 10, lh: 1.2, bold: true,
                        color: C.brass });
    d.text(good, { x: x + 56, y: y2 + 158, w: 292, px: 10.5, lh: 1.3, color: C.body });
    d.text('아쉬운 점', { x, y: y2 + 178, w: 52, px: 10, lh: 1.2, bold: true,
                          color: C.red });
    d.text(bad, { x: x + 56, y: y2 + 178, w: 292, px: 10.5, lh: 1.3, lines: 2,
                  color: C.dim });
    if (i < 2) d.vline(x + 356, y2 - 2, 204, C.rule2, 1);
  });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  /* 세 곡선이 비슷한 것은 우리 데이터의 사실이고, 그게 곧 7장 채점표가 있는
     까닭이다. 눈으로 고를 수 없으니 성적으로 골랐다 — 여기서 닫는다. */
  T.foot(d, '우리 실적에서는 세 곡선이 크게 다르지 않았습니다. 그래서 눈이 아니라 성적으로 골랐습니다.');
};
