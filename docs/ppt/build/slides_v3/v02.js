/* v3-02 · 목차 — 심사 배점표 순서 그대로. 가이드 6번의 7단계를 지킨다.
   마지막 「넘어온 과정」은 7단계 밖이라 번호를 주지 않고 들여 붙인다.     */
'use strict';
const ITEM = [
  ['추진 배경',   '이 과제를 시작한 이유',          '03', '① 개요 및 추진 배경'],
  ['문제점',      '기존 방식의 문제점',            '04', '② 현황 파악 및 문제정의'],
  ['원인',        '차이의 원인',                  '05', '③ 데이터 분석 및 원인 규명'],
  ['해결 방안',   '개선 방안',                    '06', '④ 해결방안 및 모델 개발'],
  ['모니터링',    '넉 달 병행 운전',               '07', '⑤ 향후 추이 분석' ],
  ['개선효과',    '정량 — 시간 · 정확도 · 요금',    '08', '⑥ 개선효과 (정량)'],
  ['개선효과',    '정성 — 일하는 방식',            '09', '⑥ 개선효과 (정성)'],
  ['향후 계획',   '정확도 향상과 수평 전개',        '10', '⑦ 향후계획 및 수평전개'],
];
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  const { d } = T.shell(pptx, {});
  T.title(d, '목차', null, { y: 96, px: 36 });
  T.lead(d, '문제에서 시작해 개선효과와 확산까지 하나로 잇습니다.', { y: 152, lines: 1 });

  ITEM.forEach(([name, desc, page, orig], i) => {
    const y = 206 + i * 47;
    d.text(String(i + 1).padStart(2, '0'), { x: G.L, y: y + 5, w: 44, px: 16, lh: 1.2,
                                             mono: true, bold: true, color: C.brass });
    d.text(name, { x: 132, y: y + 1, w: 210, px: 20, lh: 1.3, bold: true, color: C.ink });
    d.text(desc, { x: 362, y: y + 6, w: 440, px: 13.5, lh: 1.3, color: C.dim });
    d.text(orig, { x: 846, y: y + 7, w: 290, px: 11, lh: 1.3, color: C.dim2,
                   align: 'right' });
    d.text(page, { x: 1152, y: y + 5, w: 56, px: 14, lh: 1.3, mono: true, color: C.slateL,
                   align: 'right' });
    d.hline(G.L, y + 40, G.W, C.rule2, 1);
  });

  d.text('참고', { x: G.L, y: 590, w: 60, px: 11.5, lh: 1.2, mono: true, bold: true,
                    color: C.dim2 });
  d.text('어려웠던 점', { x: 132, y: 586, w: 210, px: 17, lh: 1.3, color: C.dim });
  d.text('시작한 계기 · 막혔던 곳 · 역할 분담', { x: 362, y: 591, w: 440, px: 13,
                                                   lh: 1.3, color: C.dim2 });
  d.text('11', { x: 1152, y: 590, w: 56, px: 14, lh: 1.3, mono: true, color: C.dim2,
                 align: 'right' });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  d.text('오른쪽 작은 글씨는 권장 발표 구성 항목입니다.',
         { x: G.L, y: G.FOOT_Y + 2, w: 700, px: 12.5, lh: 1.3, color: C.dim2 });
};
