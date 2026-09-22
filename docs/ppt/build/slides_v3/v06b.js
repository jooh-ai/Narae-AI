/* v3-07 · 회귀 모델 선정.

   2026-09-18 회신이 이 장을 만들게 했다.
     "종전 개선방안에 보면 회귀모델 비교 한 차트가 있었는데, 지금은 빠졌네.
      회귀모델 비교한 부분은 중요한 내용이라 꼭 들어 갔으면 하는데."

   맞는 지적이었다. 6장을 도구 화면으로 채우면서 회귀 모델 비교를 각주 한 줄로
   밀어 놓았다. 배점표의 'AI 활용 및 분석 타당성'(20점) 근거가 바로 이 대목이고,
   "왜 그 모델입니까" 는 발표에서 반드시 나오는 질문이다.

   자리 — 목차 ④ 는 원래 "해결 방안 도출 **및 예측/보정 모델 개발**" 두 덩어리다.
   ⑥ 개선효과를 정량·정성 두 장으로 나눈 것과 같은 방식으로 ④ 를 두 장으로
   나눈다. 6장은 무엇을 바꿨나, 이 장은 그 곡선을 무엇으로 그리나.

   숫자 — 표(우리가 그린 것)와 아래 도구 화면의 숫자가 **같다**. `ui_shots.py`
   가 테스트셋 비율 0% 로 돌려 잡기 때문이다(기본 20% 로 두면 학습셋이 32건이
   되어 MAE 가 1.493 로 적히고 장표와 어긋난다). 같은 장에 표와 화면을 나란히
   두려면 이 조건이 먼저 맞아야 했다.                                      */
'use strict';
const A = require('./assets.js');
/* 후보의 성격 — 통계 용어를 풀어 한 줄로. "무엇을 겨루게 했나" 가 보이면 된다. */
const KIND = {
  'gp:rbf':      '가장 부드러운 곡선',
  'gp:rq':       '느린 물결과 급한 물결을 섞은 곡선',
  'gp:matern52': '거의 부드러운 곡선',
  'gp:matern32': '살짝 각이 지는 곡선',
  'gp:exp':      '꺾이는 곳을 따라가는 곡선',
  'curve':       '가까운 시험을 더 많이 반영한 평균',
  'bin':         '온도 구간별 평균 — 가장 단순한 방법',
};
const NAME = {
  'gp:rbf': 'GP · RBF', 'gp:rq': 'GP · RQ', 'gp:matern52': 'GP · Matérn 5/2',
  'gp:matern32': 'GP · Matérn 3/2', 'gp:exp': 'GP · 지수',
  'curve': '커널회귀', 'bin': '구간평균',
};
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  const { d } = T.shell(pptx, { name: '해결 방안', idx: 4, step: 4 });
  const M = D.methods, base = M[0];

  T.title(d, '예측 · 보정 모델 개발', null, { px: 33 });
  T.lead(d, '온도별 곡선을 어떤 회귀 모델로 그릴지 정했습니다. 후보 7가지를 같은 데이터로 시험했습니다.',
         { y: 134, lines: 1 });

  /* ── 구획 1 · 후보 7가지 성적 ─────────────────────────────────────
     막대는 MAE 절대값이 아니라 **1등과의 차이**로 그린다. 절대값으로 그으면
     1.301 ~ 1.475 라 막대 길이가 12% 밖에 안 벌어져 눈으로 구분되지 않는다. */
  const y1 = d.section(G.L, 168, G.W, 190, 1, '후보 7가지 성적',
                       '같은 데이터 · 같은 채점 · 단위 MW');
  const dmax = Math.max(...M.map(m => m.mae - base.mae)) || 1;
  const BX = 262, BW = 300;
  d.vline(BX, y1 + 2, 112, C.steel, 1);
  M.forEach((m, i) => {
    const y = y1 + 2 + i * 16, win = i === 0;
    const diff = m.mae - base.mae;
    d.text(NAME[m.key] || m.key, { x: 92, y, w: 158, px: 11, lh: 1.2, bold: win,
                                   color: win ? C.brass : C.body, align: 'right' });
    if (win) d.rect(BX, y + 2, 5, 9, C.brass);
    else d.rect(BX + 1, y + 3, Math.max(2, Math.round(BW * diff / dmax)), 7, C.steel);
    d.text(m.mae.toFixed(3), { x: BX + BW + 14, y, w: 58, px: 10.5, lh: 1.2, mono: true,
                               bold: win, color: win ? C.brass : C.dim, align: 'right' });
    d.text(win ? '기준' : '+' + diff.toFixed(3),
           { x: BX + BW + 80, y, w: 62, px: 10.5, lh: 1.2, mono: true,
             color: win ? C.dim2 : C.red, align: 'right' });
    d.text(win ? '★ 선정 · 가장 부드러운 곡선' : KIND[m.key],
           { x: BX + BW + 156, y, w: 464, px: 10.5, lh: 1.2, bold: win,
             color: win ? C.brass : C.dim });
  });
  d.text('* 막대는 1등과의 차이 · 가운데 숫자는 평균 오차 · 한 회씩 가려 맞혀 보는 방식으로 ' +
         '누적 ' + D.n + '회 가운데 ' + D.n_score + '회를 썼습니다(한 회차는 구간평균이 답을 못 내 빠집니다).',
         { x: 92, y: y1 + 118, w: 1090, px: 10, lh: 1.3, color: C.dim2 });
  d.text('* GP = 가우시안 프로세스. 선을 하나만 긋지 않습니다. 점을 지나는 선을 여러 개 그리고 ' +
         '그 평균을 답으로 냅니다. 뒤에 붙은 이름은 곡선을 얼마나 부드럽게 그을지 정하는 설정입니다.',
         { x: 92, y: y1 + 132, w: 1090, px: 10, lh: 1.3, color: C.dim2 });

  /* ── 구획 2 · 고른 모델이 그린 곡선 (도구 화면) ───────────────── */
  const y2 = d.section(G.L, 370, G.W, 270, 2, '도구 화면 · 출력곡선 비교',
                       'GP · RBF 로 그린 결과');
  d.img(A.toolWinCurve, 92, y2, 661, 232);
  [['위 칸', '이론값(점선)과 도구가 신고하는 값(빨간 선). 두 선이 벌어진 만큼이 그 온도에서 더하는 값입니다.'],
   ['아래 칸', '온도마다 더하는 값과 시험 실적 점. 연한 띠는 도구가 함께 내는 90% 범위입니다.'],
   ['점이 없는 온도', '곡선이 메웁니다. 다만 시험한 범위를 벗어나면 끝값을 그대로 씁니다.']]
    .forEach(([k, v], i) => {
      const y = y2 + i * 78;
      d.text(k, { x: 773, y, w: 409, px: 11.5, lh: 1.2, bold: true, color: C.brass });
      d.text(v, { x: 773, y: y + 18, w: 409, px: 11, lh: 1.35, lines: 3, color: C.dim });
    });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '사람이 고른 것이 아니라 성적이 골랐습니다. 그 곡선이 신고 숫자를 만듭니다.');
};
