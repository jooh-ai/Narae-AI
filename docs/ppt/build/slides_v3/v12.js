/* v3-13 · 마무리 — 감사 인사와 질의응답.

   2026-09-18 회신: "마지막 페이지에서 곡선은 지우고, 감사합니다와 Q&A
   적절히 조합해서 만들어줘."

   곡선을 걷었다. 그 그림(외기온도별 신고 출력)은 7장 「출력곡선 비교」 화면에
   도구 화면으로 이미 들어가 있어서 마지막 장에 한 번 더 두면 같은 말을 두 번
   하는 셈이었다. 마지막 장은 마지막 장 일만 한다.

   짜임새는 **표지와 짝이 되게** 잡았다. 표지가 위에 CI · 아래에 제목·작성자
   순서라면, 이 장은 위에 소속·일자 · 가운데 인사 · 아래에 CI 로 닫는다.
   같은 기준선(좌 72 · 헤어라인 150 · 꼬리글 662)을 쓰므로 첫 장과 끝 장이
   한 쌍으로 읽힌다.

   흰 자리를 굳이 채우지 않았다. 앞 열두 장이 빽빽하므로 마지막 장의 여백이
   "끝났다" 는 신호가 된다.                                               */
'use strict';
const CI = { file: 'ci_narae.png', w: 5619, h: 1056 };   // 원본 픽셀 — 비율 5.32
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  /* 우상단 소제목은 끈다 — 왼쪽 소속 줄과 '위례사업소' 를 두 번 말하게 된다. */
  const { d } = T.shell(pptx, { topRight: false });
  d.text(meta.org + '   ·   ' + meta.when,
         { x: G.L, y: G.SEC_Y, w: 700, px: 12, lh: 1.25, mono: true,
           color: C.dim2, cs: 1.8 });

  d.hline(G.L, 150, G.W, C.rule, 1);

  /* 인사 — 표지 제목과 같은 자리(빨간 짧은 바 + 큰 글씨) */
  d.rect(G.L, 226, 46, 3, C.brass);
  d.text('감사합니다', { x: G.L, y: 254, w: 900, px: 58, lh: 1.2, bold: true,
                         color: C.ink });

  /* 질의응답 — 인사 바로 아래에 붙여 한 덩어리로 읽히게 한다.
     자간은 2pt 만 준다. 8pt 로 두었더니 'Q  &  A' 로 흩어져 보였다. */
  d.text('Q & A', { x: G.L, y: 348, w: 400, px: 31, lh: 1.2, mono: true, bold: true,
                    color: C.brass, cs: 2 });
  d.text('질문 주시면 해당 장을 띄워 설명하겠습니다.',
         { x: G.L, y: 398, w: 700, px: 15, lh: 1.4, color: C.dim });

  /* CI — 표지는 위에 얹었고 이 장은 아래로 내려 닫는다 */
  const LW = 196, LH = Math.round(LW * CI.h / CI.w);      // 37
  d.img(CI.file, G.L, 556, LW, LH, { frame: false });

  d.hline(G.L, 634, G.W, C.rule, 1);
  d.text(meta.authors.join('   ·   '), { x: G.L, y: G.FOOT_Y, w: 600, px: 14, lh: 1.4,
                                          color: C.dim });
  d.text('위례열병합발전소  ·  공급가능용량 입찰 산정 Tool',
         { x: 708, y: G.FOOT_Y + 2, w: 500, px: 12, lh: 1.4, mono: true, color: C.dim2,
           cs: 1.4, align: 'right' });
};
