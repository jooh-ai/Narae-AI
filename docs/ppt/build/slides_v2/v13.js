/* v2-13 · Tool 기능과 사용 — 요소 2개: 캡처 2장 / 탭 6개 + 사용 순서.
   [검토 반영] 기능 장과 시연 장 두 장을 한 장으로 합쳤다. '시연해 보겠습니다'
   같은 진행 멘트도 뺐다 — 화면에 적을 말이 아니라 발표자가 할 말이다.

   그림은 실제 캡처다(docs/ppt/assets/, tool/scripts/ui_shot.py 로 생성).
   두 장을 고른 기준: 왼쪽은 '무엇을 넣고 무엇이 나오나'(입력 4칸 → 61행 표),
   오른쪽은 '무엇을 보고 판단하나'(이론값 vs 모델 곡선 + 실측점).
   크기는 원본 비율 그대로 — 늘리면 글자가 뭉개져 도구가 지저분해 보인다.   */
'use strict';
const SHOT = {
  win:   { file: 'tool_window.png', w: 1280, h: 860 },
  curve: { file: 'tool_curve.png',  w: 1262, h: 654 },
};
const TABS = '공급가능용량 산정 · 온도 구간별 보정값 현황 · Test 결과 List-up · ' +
             '출력 시뮬레이션 · 출력곡선 비교 · 모델 선정';
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  const { d } = T.shell(pptx, { sec: 'Tool' });
  T.title(d, '엑셀 4개가 하던 일이,', '*이 한 화면*에 들어왔습니다');
  T.lead(d, '탭 6개입니다. 날짜·시각을 넣고 실행하면 _−20 ~ 40℃ 61행 신고값 표_ 가 ' +
         '그대로 나옵니다.', { lines: 1 });

  const H = 300;
  const wW = Math.round(H * SHOT.win.w / SHOT.win.h);      // 447
  const wC = Math.round(H * SHOT.curve.w / SHOT.curve.h);  // 579
  const x0 = G.L + Math.round((G.W - (wW + wC + 40)) / 2);
  const x1 = x0 + wW + 40;
  d.plab('① 산정 화면  ·  입력 4칸 → 61행 신고값 표', x0, 246, wW, C.brass);
  d.plab('② 출력곡선 비교  ·  이론값 vs 모델 + 실측 ' + D.n + '회', x1, 246, wC, C.brass);
  d.img(SHOT.win.file, x0, 262, wW, H);
  d.img(SHOT.curve.file, x1, 262, wC, H);

  d.zone(G.L, 574, G.W, 50);
  d.text('탭 6개', { x: 96, y: 584, w: 74, px: G.LAB_PX, lh: 1.25, mono: true, bold: true,
                     color: C.dim2, cs: 1.5 });
  d.text(TABS, { x: 176, y: 582, w: 1008, px: 12, lh: 1.3, color: C.body });
  d.text('사용 순서', { x: 96, y: 604, w: 74, px: G.LAB_PX, lh: 1.25, mono: true,
                        bold: true, color: C.brass, cs: 1.5 });
  d.text('① 날짜·시각 입력 → ② 실행 → ③ 곡선·표 확인 → ④ 엑셀로 저장',
         { x: 176, y: 602, w: 1008, px: 12, lh: 1.3, bold: true, color: C.ink });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '목업이 아니라 *실제 화면*입니다 — 사람이 손으로 옮겨 적는 칸은 없습니다.');
};
