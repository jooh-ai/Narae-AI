/* v3-03 · ① 개요 및 추진 배경 — 기존에는 이렇게 했다.

   2026-09-16 다시 씀. 앞 판이 막힌 이유를 회신에서 이렇게 읽었다.
     · 제목이 슬로건이라 처음 보는 사람은 무슨 말인지 모른다
     · 문장마다 각을 세워 놓으니 정작 설명이 없다
     · 텍스트 덩어리가 여기저기 흩어져 눈이 한 곳에 못 머문다

   그래서 규칙을 바꿨다.
     제목은 라벨처럼 담백하게. 결론은 맨 아래 한 줄로만.
     그림 아래에 **설명 문단 하나**. 짧게 자르지 않고 끝까지 풀어 쓴다.
     그림 위에는 라벨만 얹고 문장은 쓰지 않는다.
     중점(·)과 줄표(—)를 본문에 쓰지 않는다. 그게 제일 큰 기계 냄새였다.   */
'use strict';
const A = require('./assets.js');
const STEP = [['① 값 받아오기', A.xl1], ['② 온도별 계산', A.xl2],
              ['③ 차이 더하기', A.xl2blt], ['④ 프로파일 완성', A.xl3]];
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  const { d } = T.shell(pptx, { sec: '추진 배경', idx: 1, step: 1 });
  T.title(d, '기존에는 이렇게 했습니다', null);

  const BW = 266, GAP = 24;
  STEP.forEach(([name, file], i) => {
    const x = G.L + i * (BW + GAP);
    d.text(name, { x, y: 172, w: BW, px: 15, lh: 1.3, bold: true, color: C.brass,
                   align: 'center' });
    d.zone(x, 198, BW, 250);
    d.imgFit(file, x + 10, 208, BW - 20, 230);
    if (i < STEP.length - 1) d.arrow(x + BW + 2, 312);
  });

  /* 설명은 한 덩어리로 끝까지 쓴다. 문장 길이를 일부러 고르지 않게 둔다. */
  d.text('시험은 하루에 한 번, 그날 날씨에서만 합니다. 그런데 신고는 영하 20도부터 40도까지 ' +
         '61개 온도를 다 해야 합니다.\n' +
         '해보지 않은 온도는 실제로 얼마가 나오는지 알 방법이 없었습니다. ' +
         '그래서 시험한 날에 생긴 차이를 나머지 온도에도 똑같이 더해서 신고했습니다.',
         { x: G.L, y: 476, w: 820, px: 16, lh: 1.72, lines: 4, color: C.body });

  d.rect(920, 480, 3, 96, C.rule);
  d.text('엑셀 파일 4개', { x: 942, y: 484, w: 266, px: 15, lh: 1.4, color: C.dim });
  d.text('손으로 옮기는 값 61개', { x: 942, y: 512, w: 266, px: 15, lh: 1.4, color: C.dim });
  d.text('대기압 받는 파일 별도', { x: 942, y: 540, w: 266, px: 15, lh: 1.4, color: C.dim });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '그때는 이게 최선이었습니다.');
};
