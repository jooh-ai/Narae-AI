/* v3-03 · 이 과제를 시작한 이유.
   구획 셋. 신고하는 숫자(무엇을 하는 일인가) / 과제 선정 이유 / 기존 절차.

   2026-09-17 2차 회신이 이 장을 고쳤다.
     "1 신고하는 숫자에 그래프만 있다보니 어떤 그래프인지 분간이 어려움.
      주석 넣을 것. 많이 입찰하고 출력을 못 내면 패널티, 적게 입찰하면
      차이만큼 CP 용량 요금 손실. 2 과제 선정 이유는 'AI를 통해 새로운
      분야를 경험하고 study해서 해결하는 성취감을 위해' 라는 방향으로 수정."

   축도 눈금도 없는 곡선 하나를 놓고 "이런 그래프입니다" 라고 말하고 있었다.
   가로·세로가 무엇인지, 무슨 값을 그린 것인지 적었다.

   선정 이유는 순서를 바꿨다. 종전 판은 '눈에 보였다 / 수익' 둘이었는데,
   그것은 대상을 고른 이유이고 **시작한 이유는 따로 있었다**. 그 이유를
   맨 앞에 세운다.                                                        */
'use strict';
const A = require('./assets.js');
module.exports = (pptx, T, meta, D) => {
  const { C, G, LW } = T;
  const { d } = T.shell(pptx, { name: '추진 배경', idx: 1, step: 1 });
  T.title(d, '이 과제를 시작한 이유', null, { px: 33 });
  T.lead(d, '발전소는 전기를 팔기 전에 얼마나 낼 수 있는지 미리 신고해야 합니다. 이 과제는 그 신고 숫자를 만드는 일입니다.',
         { y: 134, lines: 1 });

  /* ── 구획 1 · 신고하는 숫자 ───────────────────────────────────── */
  const y1 = d.section(G.L, 176, G.W, 154, 1, '신고하는 숫자',
                       '발전운영팀 업무 · 우리는 정비기술팀');
  /* 그래프 — 제작사 계산값(이론값) 곡선. 축·눈금·이름을 붙인다. */
  const R = D.profile.rows.filter(r => r.t >= -10 && r.t <= 40);
  const vs = R.map(r => r.theory), lo = Math.min(...vs), hi = Math.max(...vs);
  const X = t => 128 + (t + 10) * 6.2, Y = v => y1 + 92 - (v - lo) / (hi - lo) * 66;
  /* 구획 안의 캡션은 다른 장과 같이 내용 왼쪽 축(92)에 맞춘다. 종전에는 74 라
     머리글(72)과 2px 어긋나 보였다 — 2026-09-18 정렬 감사에서 잡았다. */
  d.text('세로 신고 출력(MW) · 가로 외기온도(℃) · 추우면 많이, 더우면 적게',
         { x: 92, y: y1, w: 400, px: 10, lh: 1.2, color: C.dim2 });
  d.hline(122, y1 + 96, 328, C.rule, 1);
  d.vline(122, y1 + 18, 78, C.rule, 1);
  for (let i = 0; i < R.length - 1; i++)
    d.seg(X(R[i].t), Y(R[i].theory), X(R[i + 1].t), Y(R[i + 1].theory), C.brass, LW.main);
  d.text(Math.round(hi) + ' MW', { x: 74, y: Y(hi) - 6, w: 44, px: 9.5, lh: 1.2, mono: true,
                                    color: C.dim2, align: 'right' });
  d.text(Math.round(lo) + ' MW', { x: 74, y: Y(lo) - 6, w: 44, px: 9.5, lh: 1.2, mono: true,
                                    color: C.dim2, align: 'right' });
  [[-10, '−10℃'], [0, '0'], [20, '20'], [40, '40℃']].forEach(([t, lb]) =>
    d.text(lb, { x: X(t) - 22, y: y1 + 100, w: 44, px: 9.5, lh: 1.2, mono: true,
                 color: C.dim2, align: 'center' }));
  d.text('제작사 계산값 곡선', { x: 226, y: y1 + 16, w: 150, px: 10.5, lh: 1.2,
                                 bold: true, color: C.brass });
  d.vline(482, y1 - 2, 108, C.rule2, 1);
  d.text('추울 때와 더울 때 낼 수 있는 양이 다릅니다.',
         { x: 510, y: y1, w: 330, px: 14, lh: 1.45, lines: 2, color: C.body });
  d.text('영하 20도 ~ 40도까지 온도 61개 숫자를 따로 신고합니다.',
         { x: 510, y: y1 + 44, w: 330, px: 12.5, lh: 1.4, lines: 2, color: C.dim });

  d.vline(872, y1 - 2, 108, C.rule2, 1);
  d.text('신고한 숫자가 어긋나면', { x: 898, y: y1, w: 290, px: 11, lh: 1.2, color: C.dim2 });
  [['많이 신고하고 출력을 못 내면', '패널티', C.red],
   ['적게 신고하면', '차이만큼 CP 용량요금 손실', C.slateL]]
    .forEach(([k, v, col], i) => {
      const y = y1 + 24 + i * 46;
      d.text(k, { x: 898, y, w: 290, px: 12, lh: 1.25, color: C.body });
      d.text(v, { x: 898, y: y + 18, w: 290, px: 13.5, lh: 1.25, bold: true, color: col });
    });

  /* ── 구획 2 · 과제 선정 이유 ──────────────────────────────────── */
  const y2 = d.section(G.L, 342, 556, 282, 2, '과제 선정 이유', '정비기술팀 두 사람');
  d.text('해 본 적 없는 분야를 공부해서 직접 풀어 보고 싶었습니다.',
         { x: 92, y: y2, w: 516, px: 15, lh: 1.25, bold: true, color: C.ink });
  d.text('남의 팀 업무인데도 과제로 잡은 이유가 셋 있습니다.',
         { x: 92, y: y2 + 24, w: 516, px: 12, lh: 1.35, color: C.dim });
  [['AI 로 새 분야를 경험하고 싶었다',
    '예측·보정 모델은 해 본 적이 없었습니다. AI 의 도움을 받아 직접 공부하고 ' +
    '풀어내는 성취감을 느껴 보고 싶었습니다.'],
   ['비효율이 눈에 먼저 보였다',
    '공급가능용량 테스트는 발전운영팀 업무입니다. 곁에서 보니 엑셀 파일 네 개를 ' +
    '오가는 일이 번거로워 보였습니다.'],
   ['수익으로 이어진다',
    '신고 숫자가 정확해지면 CP 용량요금 손실이 그만큼 줄어듭니다.']]
    .forEach(([k, v], i) => {
      const y = y2 + 62 + i * 60;
      d.rect(92, y + 2, 4, 46, C.brass);
      d.text(String(i + 1), { x: 108, y, w: 18, px: 12, lh: 1.2, mono: true, bold: true,
                              color: C.brass });
      d.text(k, { x: 130, y: y - 2, w: 478, px: 14.5, lh: 1.25, bold: true, color: C.ink });
      d.text(v, { x: 130, y: y + 20, w: 478, px: 11.5, lh: 1.35, lines: 2, color: C.dim });
    });

  /* ── 구획 3 · 기존 절차 ───────────────────────────────────────── */
  const y3 = d.section(644, 342, 564, 282, 3, '기존 절차', '엑셀 파일 4개 · 한 회에 1시간');
  const STEP = [['① 계측값 받아오기', A.xl1], ['② 온도별로 계산', A.xl2],
                ['③ 차이를 더하기', A.xl2blt], ['④ 표 완성', A.xl3]];
  STEP.forEach(([name, file], i) => {
    const x = 664 + (i % 2) * 272, y = y3 + Math.floor(i / 2) * 114;
    d.text(name, { x, y, w: 250, px: 12.5, lh: 1.25, bold: true, color: C.brass });
    d.box(x, y + 20, 250, 72, null, C.rule2, 1);
    d.imgFit(file, x + 5, y + 24, 240, 64);
  });
  d.text('값은 사람이 손으로 옮겼습니다. 한 회에 61개였습니다.',
         { x: 664, y: y3 + 226, w: 524, px: 11.5, lh: 1.3, color: C.dim2 });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '공부해 보고 싶은 분야였고, 줄일 수 있는 일도 눈에 보였습니다.');
};
