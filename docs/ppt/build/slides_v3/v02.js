/* v3-02 · 목차 — 여덟 항목. 이름은 쉬운 단어로 바꿨고, 원래 보고 항목 번호를
   오른쪽에 작게 병기한다. 순서를 바꾼 것(모니터링과 효과)이 보이게 하려는 것이다.
   본사 양식을 안 지킨 것이 아니라 읽는 순서만 손댔다는 뜻이다.             */
'use strict';
const ITEM = [
  ['기존 방식',   '기존 공급가능용량 산정 방식',   '03', '① 개요 및 추진 배경'],
  ['문제점',      '절차 · 일괄 보정 · 예측 오차',   '04', '② 현황 파악 및 문제 정의'],
  ['원인',        '무엇 때문에 어긋났나',           '05', '③ 데이터 분석 및 원인 규명'],
  ['개선 방안',   '온도별로 배우는 보정 모델',      '06', '④ 해결 방안 및 모델 개발'],
  ['개선 효과',   '신고 정확도와 업무 시간',        '07', '⑥ 개선 효과'],
  ['넘어온 과정', '막혔던 것과 푼 방법',            '08', '별도'],
  ['유지 관리',   '시험이 쌓이면 스스로 갱신',      '09', '⑤ 모니터링 체계 구축'],
  ['향후 계획',   '정착과 수평 전개',               '10', '⑦ 향후 계획 및 수평 전개'],
];
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  const { d } = T.shell(pptx, {});
  T.title(d, '목차', null, { y: 96, px: 36 });
  T.lead(d, '앞의 세 항목이 왜 했는지, 뒤의 다섯 항목이 무엇을 어떻게 바꿨는지입니다.',
         { y: 152, lines: 1 });

  ITEM.forEach(([name, desc, page, orig], i) => {
    const y = 210 + i * 51;
    d.text(String(i + 1).padStart(2, '0'), { x: G.L, y: y + 6, w: 44, px: 17, lh: 1.2,
                                             mono: true, bold: true, color: C.brass });
    d.text(name, { x: 132, y: y + 2, w: 220, px: 21, lh: 1.3, bold: true, color: C.ink });
    d.text(desc, { x: 372, y: y + 7, w: 460, px: 14, lh: 1.3, color: C.dim });
    d.text(orig, { x: 856, y: y + 8, w: 280, px: 11.5, lh: 1.3, color: C.dim2,
                   align: 'right' });
    d.text(page, { x: 1152, y: y + 6, w: 56, px: 15, lh: 1.3, mono: true, color: C.slateL,
                   align: 'right' });
    if (i < ITEM.length - 1) d.hline(G.L, y + 44, G.W, C.rule2, 1);
  });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  d.text('오른쪽 작은 글씨는 본사 보고 항목입니다. 읽는 순서만 바꿨습니다.',
         { x: G.L, y: G.FOOT_Y + 2, w: 700, px: 12.5, lh: 1.3, color: C.dim2 });
};
