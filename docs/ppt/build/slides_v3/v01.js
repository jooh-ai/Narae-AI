/* v2-01 · 표지 — 최종보고서 표지 형식.
   표지는 표지 일만 한다 — 문서 종류 · 제목 · 부제 · 소속/작성자/일자.

   2026-09-18 회신 "회사 CI 둘다 지우고" 로 CI 를 걷었다(표지·마무리 양쪽).
   빈 왼쪽 머리 자리에는 소속을 글자로 적는다 — 마무리 장과 같은 모양이라
   첫 장과 끝 장이 한 쌍으로 읽히고, 오른쪽 문서 종류와 좌우 균형이 맞는다. */
'use strict';
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  /* 표지에는 머리글·쪽번호를 두지 않는다. 우상단 소제목은 아래 '개선과제
     최종 보고' 와 두 줄로 붙어 실수처럼 보였다. */
  const { d } = T.shell(pptx, { topRight: false, page: false });

  d.text(meta.org, { x: G.L, y: 78, w: 600, px: 12, lh: 1.25, mono: true,
                     color: C.dim2, cs: 1.8 });
  d.text('개선과제 최종 보고', { x: 808, y: 74, w: 400, px: 12.5, lh: 1.25, mono: true,
                                 color: C.dim, cs: 2.0, align: 'right' });

  d.hline(G.L, 150, G.W, C.rule, 1);

  /* 제목 */
  d.rect(G.L, 236, 46, 3, C.brass);
  d.text('공급가능용량 산정 자동화 및', { x: G.L, y: 264, w: 1000, px: 44, lh: 1.28,
                                          bold: true, color: C.ink });
  d.text('온도별 보정 모델 개발', { x: G.L, y: 320, w: 1000, px: 44, lh: 1.28,
                                    bold: true, color: C.ink });
  d.text('산정 절차를 하나로 합치고, 누적 ' + D.n + '회 실적으로 온도별 보정 곡선을 만들었습니다',
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
