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
  'gp:rq':       '여러 굵기의 파동을 섞은 곡선',
  'gp:matern52': '조금 덜 부드러운 곡선',
  'gp:matern32': '더 덜 부드러운 곡선',
  'gp:exp':      '꺾임을 허용하는 곡선',
  'curve':       '가까운 시험에 무게를 더 주는 평균',
  'bin':         '온도 구간을 나눠 그 안의 평균을 씀 — 가장 단순',
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

  T.title(d, '회귀 모델 선정', null, { px: 33 });
  T.lead(d, '어떤 회귀 모델을 써야 하는지 우리가 정할 수 없었습니다. 후보 7가지를 같은 데이터로 겨루게 했습니다.',
         { y: 134, lines: 1 });

  /* ── 구획 1 · 후보 7가지 성적 ─────────────────────────────────────
     막대는 MAE 절대값이 아니라 **1등과의 차이**로 그린다. 절대값으로 그으면
     1.301 ~ 1.475 라 막대 길이가 12% 밖에 안 벌어져 눈으로 구분되지 않는다
     (종전 6장의 막대가 그랬다). 차이로 그리면 0 ~ 0.174 라 그대로 보인다. */
  const y1 = d.section(G.L, 168, G.W, 200, 1, '후보 7가지 성적',
                       '같은 데이터 · 같은 채점 · 단위 MW');
  const dmax = Math.max(...M.map(m => m.mae - base.mae)) || 1;
  const BX = 262, BW = 300;
  d.vline(BX, y1 + 2, 128, C.steel, 1);
  M.forEach((m, i) => {
    const y = y1 + 4 + i * 18, win = i === 0;
    const diff = m.mae - base.mae;
    d.text(NAME[m.key] || m.key, { x: 92, y, w: 158, px: 11.5, lh: 1.2, bold: win,
                                   color: win ? C.brass : C.body, align: 'right' });
    if (win) d.rect(BX, y + 3, 5, 9, C.brass);
    else d.rect(BX + 1, y + 4, Math.max(2, Math.round(BW * diff / dmax)), 7, C.steel);
    d.text(m.mae.toFixed(3), { x: BX + BW + 14, y, w: 58, px: 11, lh: 1.2, mono: true,
                               bold: win, color: win ? C.brass : C.dim, align: 'right' });
    d.text(win ? '기준' : '+' + diff.toFixed(3),
           { x: BX + BW + 80, y, w: 62, px: 11, lh: 1.2, mono: true,
             color: win ? C.dim2 : C.red, align: 'right' });
    d.text(win ? '★ 선정' : KIND[m.key],
           { x: BX + BW + 158, y, w: 420, px: 11, lh: 1.2, bold: win,
             color: win ? C.brass : C.dim });
  });
  d.text('세로 이름 · 막대는 1등과의 차이(오른쪽으로 갈수록 더 틀린 것) · 가운데 숫자가 ' +
         '평균 오차 · 채점은 시험 ' + D.n_score + '회를 한 회씩 가려 맞혀 보는 방식',
         { x: 92, y: y1 + 134, w: 1090, px: 10, lh: 1.3, color: C.dim2 });
  d.text('* GP = 가우시안 프로세스. 값 하나를 내는 것이 아니라 곡선 전체를 후보로 두고 ' +
         '실적에 가장 잘 맞는 곡선을 고릅니다. 뒤에 붙은 이름(RBF · Matérn …)은 곡선이 ' +
         '얼마나 부드러운지를 정하는 설정입니다.',
         { x: 92, y: y1 + 152, w: 1090, px: 10, lh: 1.3, lines: 1, color: C.dim2 });

  /* ── 구획 2 · 도구 안에서 고릅니다 ────────────────────────────── */
  const y2 = d.section(G.L, 380, G.W, 260, 2, '도구 안에서 고릅니다',
                       '모델 선정 화면 · 위 표와 같은 숫자입니다');
  d.img(A.toolWinSel, 92, y2, 778, 226);
  [['왜 도구에 넣었나', '시험이 ' + D.n + '회뿐입니다. 실적이 늘면 성적이 바뀔 수 있어 ' +
    '그때마다 다시 채점해야 합니다.'],
   ['어떻게 채점하나', '한 회를 가리고 나머지로 그 회를 맞혀 봅니다. 전 회차를 돌아가며 ' +
    '반복해 평균을 냅니다.'],
   ['앞서면 바꾼다', '다른 모델이 앞서면 그때 바꿉니다. 지금은 GP·RBF 가 앞섭니다.']]
    .forEach(([k, v], i) => {
      const y = y2 + i * 76;
      d.text(k, { x: 900, y, w: 282, px: 11.5, lh: 1.2, bold: true, color: C.brass });
      d.text(v, { x: 900, y: y + 18, w: 282, px: 11, lh: 1.35, lines: 4, color: C.dim });
    });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '사람이 고른 것이 아니라 성적이 골랐습니다. 그 채점이 도구 안에 들어 있습니다.');
};
