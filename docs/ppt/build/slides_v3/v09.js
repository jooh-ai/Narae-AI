/* v3-09 · 개선효과 (정성).
   배점표 평가내용의 '리스크 저감 · 품질향상 · 정성 성과' 에 대응한다.
   숫자로 못 적는 것들이다. 그래서 "무엇이 달라졌나" 를 상태로 적는다.
   전 / 후 두 칸으로 놓으면 정성 효과도 눈에 보인다.                       */
'use strict';
const A = require('./assets.js');
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  const { d } = T.shell(pptx, { name: '개선효과', idx: 6, step: 6 });
  T.title(d, '숫자로 적기 어려운 것들', null, { px: 33 });
  T.lead(d, '일하는 방식에서 달라진 것도 있습니다.', { y: 146, lines: 1 });

  /* 구획 1 — 전 / 후 세 가지 */
  d.section(G.L, 182, 700, 442, 1, '일하는 방식', '');
  [['잘못된 시험을 걸러낸다',
    '사람이 알아채야 했습니다. 지나치면 그대로 반영됐습니다.',
    '도구가 세 가지를 자동으로 걸러냅니다. 반영을 아예 막습니다.'],
   ['숫자의 근거를 말할 수 있다',
    '왜 그 값을 더했는지 관행으로만 설명했습니다.',
    '시험 ' + D.n + '회가 근거입니다. 어느 회차가 어떻게 쓰였는지 남습니다.'],
   ['담당자가 바뀌어도 같다',
    '엑셀을 다루는 손버릇에 따라 결과가 달라질 수 있었습니다.',
    '도구 폴더를 넘기면 그대로 이어집니다. 절차가 도구 안에 있습니다.']]
    .forEach(([k, before, after], i) => {
      const y = 226 + i * 132;
      d.rect(92, y + 2, 4, 26, C.brass);
      d.text(k, { x: 112, y, w: 660, px: 18, lh: 1.3, bold: true, color: C.ink });
      d.text('전', { x: 112, y: y + 38, w: 30, px: 11.5, lh: 1.2, mono: true, bold: true,
                     color: C.slateL });
      d.text(before, { x: 146, y: y + 36, w: 620, px: 13, lh: 1.4, lines: 2,
                       color: C.dim });
      d.text('후', { x: 112, y: y + 76, w: 30, px: 11.5, lh: 1.2, mono: true, bold: true,
                     color: C.brass });
      d.text(after, { x: 146, y: y + 74, w: 620, px: 13.5, lh: 1.4, lines: 2,
                      color: C.body });
      if (i < 2) d.hline(92, y + 116, 680, C.rule2, 1);
    });

  /* 구획 2 — 걸러내는 장치 (리스크 저감의 실제 내용) */
  d.section(788, 182, 420, 442, 2, '도구가 걸러내는 것', '리스크 저감');
  d.imgFit(A.toolStatus, 808, 224, 380, 150);
  [['공기를 더 넣지 않고 한 시험', '결론을 뒤집게 만든 그 시험입니다.'],
   ['시험한 범위를 벗어난 온도', '배우지 않은 구간은 늘려 쓰지 않습니다.'],
   ['일부만 골라 만든 관계', '진공도에서 세 번 걸렸던 착각입니다.']]
    .forEach(([k, why], i) => {
      const y = 396 + i * 74;
      d.rect(808, y + 2, 4, 52, C.red);
      d.text(k, { x: 828, y, w: 360, px: 13.5, lh: 1.3, lines: 2, bold: true,
                  color: C.ink });
      d.text(why, { x: 828, y: y + 34, w: 360, px: 11.5, lh: 1.3, lines: 2,
                    color: C.dim });
    });
  d.text('알린 만큼 못 낸 횟수가 ' + D.impact.blanket.short + '회에서 ' +
         D.impact.gp.short + '회로 줄었습니다.',
         { x: 808, y: 608, w: 380, px: 11.5, lh: 1.3, lines: 1, color: C.dim2 });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '사람이 놓칠 수 있는 자리를 도구가 대신 봅니다.');
};
