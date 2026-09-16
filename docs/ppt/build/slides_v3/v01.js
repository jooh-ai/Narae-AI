/* v2-01 · 표지 — 최종보고서 표지 형식.
   [검토 반영] 종전 표지에는 히어로 차트와 핵심 3수치가 있었는데, 그 내용은
   3장(한 장 요약)과 겹쳤다. 표지는 표지 일만 하게 비웠다 —
   CI · 문서 종류 · 제목 · 부제 · 소속/작성자/일자.

   CI 는 배경이 투명한 원본이지만 한글 글자가 검정(#231f20)이라 남색 위에
   그대로 얹으면 회사 이름이 사라진다. 그래서 흰 판에 올린다. 로고 색을
   고쳐 쓰지 않는 것이 CI 규정에 맞다.                                      */
'use strict';
const CI = { file: 'ci_narae.png', w: 5619, h: 1056 };   // 원본 픽셀 — 비율 5.32
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  const { d } = T.shell(pptx, { rule: false });

  /* CI — 흰 판 위에. 너무 크지 않게 폭 196px(슬라이드 폭의 15%) */
  const LW = 196, LH = Math.round(LW * CI.h / CI.w);      // 37
  d.rect(G.L, 56, LW + 28, LH + 26, 'FFFFFF');
  d.img(CI.file, G.L + 14, 69, LW, LH, { frame: false });
  d.text('개선과제 최종 보고', { x: 808, y: 74, w: 400, px: 12.5, lh: 1.25, mono: true,
                                 color: C.dim, cs: 2.0, align: 'right' });

  d.hline(G.L, 150, G.W, C.rule, 1);

  /* 제목 */
  d.rect(G.L, 236, 46, 3, C.brass);
  d.text('공급가능용량 산정 자동화 및', { x: G.L, y: 264, w: 1000, px: 44, lh: 1.28,
                                          bold: true, color: C.ink });
  d.text('온도별 보정 모델 개발', { x: G.L, y: 320, w: 1000, px: 44, lh: 1.28,
                                    bold: true, color: C.ink });
  d.text('온도 프로파일 생성 절차 통합과 누적 ' + D.n + '회 실적 기반 보정 곡선 적용',
         { x: G.L, y: 392, w: 1000, px: 17, lh: 1.5, color: C.body });

  d.hline(G.L, 452, G.W, C.rule, 1);

  /* 소속·작성자·일자 */
  [['소  속', meta.org], ['부  서', meta.dept],
   ['작 성 자', meta.authors.join('  ·  ')], ['작성일자', meta.when]]
    .forEach(([k, v], i) => {
      const y = 486 + i * 38;
      d.text(k, { x: G.L, y: y + 2, w: 80, px: 11.5, lh: 1.25, mono: true,
                  color: C.dim2, cs: 1.4 });
      d.vline(168, y, 20, C.rule, 1);
      d.text(v, { x: 190, y, w: 700, px: 16, lh: 1.35, color: C.ink });
    });

  d.hline(G.L, 634, G.W, C.rule, 1);
  d.text('위례열병합발전소  ·  공급가능용량 입찰 산정 Tool',
         { x: G.L, y: G.FOOT_Y, w: 800, px: 12, lh: 1.4, mono: true, color: C.dim2, cs: 1.6 });
};
