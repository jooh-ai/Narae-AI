/* v2-14 · Tool 기능 — 화면 그대로 · 요소 2개: 캡처 2장 / 탭 6개 띠.
   도구를 만든 보고인데 도구 화면이 한 장도 없으면 이상하다. 그림은 실제
   캡처다(docs/ppt/assets/, tool/scripts/ui_shot.py 로 뽑았다) — 목업이 아니다.

   두 장을 고른 기준: 왼쪽은 '무엇을 넣고 무엇이 나오는가'(입력 4칸 → 61행
   프로파일 표), 오른쪽은 '무엇을 보고 판단하는가'(이론값 vs 모델 곡선).
   나머지 탭은 아래 띠에 이름만 둔다 — 실물은 다음 장에서 띄운다.

   그림 크기는 원본 비율 그대로다. 캡처를 늘리면 글자가 뭉개져서 화면이
   지저분해 보이고, 그러면 도구가 지저분해 보인다.                          */
'use strict';
/* 원본 픽셀 — 비율을 여기서 한 번만 계산한다 */
const SHOT = {
  win:   { file: 'tool_window.png', w: 1280, h: 860 },
  curve: { file: 'tool_curve.png',  w: 1262, h: 654 },
};
const TABS = ['공급가능용량 산정', '온도 구간별 보정값 현황', 'Test 결과 List-up',
              '출력 시뮬레이션', '출력곡선 비교', '모델 선정'];
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  const { d } = T.shell(pptx, { sec: 'Tool 기능' });
  T.title(d, '엑셀 4개가 하던 일이,', '*이 한 화면*에 들어왔습니다');
  T.lead(d, '탭 6개입니다. 날짜·시각을 넣고 실행하면 _−20 ~ 40℃ 61행 신고값 표_ 가 ' +
         '그대로 나옵니다.', { lines: 1 });

  /* 두 장을 같은 높이로 맞춰 나란히 — 높이를 맞춰야 한 쌍으로 읽힌다 */
  const H = 320, GAP = 40;
  const wW = Math.round(H * SHOT.win.w / SHOT.win.h);      // 476
  const wC = Math.round(H * SHOT.curve.w / SHOT.curve.h);  // 617
  const x0 = G.L, x1 = G.L + wW + GAP;
  d.img(SHOT.win.file, x0, 246, wW, H);
  d.img(SHOT.curve.file, x1, 246, wC, H);

  d.plab('무엇을 넣고 무엇이 나오나', x0, 576, wW, C.brass);
  d.text('입력은 *날짜·시각* 4칸 → 아래에 61행 신고값 표',
         { x: x0, y: 592, w: wW, px: 13, lh: 1.35 });
  d.plab('무엇을 보고 판단하나', x1, 576, wC, C.brass);
  d.text('~이론값~ 곡선과 *모델* 곡선, 그리고 실측점 ' + D.n + '회를 겹쳐 봅니다',
         { x: x1, y: 592, w: wC, px: 13, lh: 1.35 });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '목업이 아니라 *실제 화면*입니다 — 다음 장에서 직접 띄우겠습니다.');
};
