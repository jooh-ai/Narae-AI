/* v3-09 · 시험이 쌓이면 스스로 갱신.
   구획 둘. 갱신 순환(도구 화면 포함) / 잘못된 회차를 걸러내는 장치.
   앞 장에서 "막힌 자리마다 검사를 심었다" 고 닫았으니, 그 검사들이 여기 모인다. */
'use strict';
const A = require('./assets.js');
const STEP = ['시험을 한다', '날짜와 시각을 넣는다', '곡선이 다시 배운다',
              '다음 숫자에 쓰인다'];
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  const { d } = T.shell(pptx, { name: '유지 관리', idx: 7, step: 7 });
  T.title(d, '시험이 쌓이면 스스로 갱신', null, { px: 33 });
  T.lead(d, '사람이 다시 계산하지 않습니다. 시험 결과를 넣으면 도구가 스스로 다시 배웁니다.',
         { y: 146, lines: 1 });

  /* 구획 1 — 순환 */
  d.section(G.L, 186, G.W, 108, 1, '한 회차가 도는 순서', '날짜와 시각만 입력');
  STEP.forEach((s, i) => {
    const x = 96 + i * 282;
    d.text(String(i + 1), { x, y: 232, w: 24, px: 15, lh: 1.2, mono: true, bold: true,
                            color: C.brass });
    d.text(s, { x: x + 28, y: 230, w: 206, px: 14.5, lh: 1.3, color: C.ink });
    if (i < 3) d.arrow(x + 240, 230);
  });

  /* 구획 2 — 도구 화면 */
  d.section(G.L, 306, 700, 318, 2, '도구 화면', '시험 ' + D.n + '회가 쌓인 상태');
  d.imgFit(A.toolWin, 92, 344, 660, 232);
  d.text('날짜와 시각을 넣고 실행하면 61개 온도의 숫자가 한 번에 나옵니다.',
         { x: 92, y: 586, w: 660, px: 12, lh: 1.3, color: C.dim2 });

  /* 구획 3 — 걸러내는 장치 */
  d.section(788, 306, 420, 318, 3, '잘못된 회차를 걸러냅니다', '');
  [['공기를 더 넣지 않고 한 시험', '아예 쓰지 않습니다',
    '결론을 뒤집게 만든 그 시험입니다.'],
   ['시험한 범위를 벗어난 온도', '끝값을 그대로 씁니다',
    '배우지 않은 구간은 늘려 쓰지 않습니다.'],
   ['일부 회차만 골라 만든 관계', '검사가 걸러냅니다',
    '진공도에서 세 번 걸렸던 착각입니다.']]
    .forEach(([k, v, why], i) => {
      const y = 348 + i * 88;
      d.rect(808, y + 2, 4, 62, C.red);
      d.text(k, { x: 828, y, w: 360, px: 13, lh: 1.3, lines: 1, color: C.dim });
      d.text(v, { x: 828, y: y + 22, w: 360, px: 15, lh: 1.3, bold: true, color: C.brass });
      d.text(why, { x: 828, y: y + 46, w: 360, px: 11.5, lh: 1.35, lines: 2, color: C.dim2 });
    });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '사람이 놓칠 수 있는 자리를 도구가 대신 봅니다.');
};
