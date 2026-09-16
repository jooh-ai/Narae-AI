/* v3-05 · 차이의 원인.

   2026-09-17 회신이 이 장을 다시 짰다.
     "겪은일 '진공도를 세번 접었다' 빼고, 결론 뒤집힌건(IGV) 쉽게 설명할 것.
      1번에서 각 후보가 왜 빠졌는지 수치 또는 fact 로 설명이 더 필요하고,
      외기 온도가 왜 남았는지 이유를 좀 더 설명."

   종전 판은 후보 상자 넷에 가로줄만 그었다. "아니었습니다" 라고만 적혀 있어서
   왜 아닌지 물으면 답할 것이 없었다. 그래서 구획 1 을 **숫자가 붙은 표**로
   바꿨다. 같은 방법(GP·RBF)에 입력만 바꿔 채점한 결과이므로 행끼리 바로
   견줄 수 있다 — 근거는 `docs/ppt/build/varsel.py`, 값은 deck_data.varsel.

   진공도 구획은 뺐다. 세 번 접은 이야기는 결론이 "아니었다" 뿐이라 장표에서
   자리만 차지했다. 표의 한 행(+복수기 진공도)으로 충분하다.                */
'use strict';
module.exports = (pptx, T, meta, D) => {
  const { C, G } = T;
  const { d } = T.shell(pptx, { name: '원인', idx: 3, step: 3 });
  const V = D.varsel, CZ = D.causes;
  const cp = CZ.rows.find(r => r.key === 'cp_meas');
  const near = V.near;

  T.title(d, '차이의 원인', null, { px: 33 });
  T.lead(d, '출력에 영향을 줄 수 있는 값 네 개를 후보로 놓고, 하나씩 넣어 보며 확인했습니다.',
         { y: 134, lines: 1 });

  /* ── 구획 1 · 후보 4개 → 1개. 같은 방법에 입력만 바꿔 채점했다 ──── */
  const y1 = d.section(G.L, 174, G.W, 236, 1, '넣어 본 것과 남은 것',
                       '같은 방법 · 입력만 바꿔 채점');
  const NAME = { cit: '외기 온도만', rh: '＋ 상대습도', press: '＋ 대기압',
                 cp_meas: '＋ 복수기 진공도' };
  const WHY = {
    cit: '차이의 *85%* 를 이것만으로 설명합니다',
    rh: '0.01 나아졌지만 흔들림 ±' + near.vs_base.se.toFixed(2) + ' 보다 작습니다',
    press: '제작사 계산식이 이미 쓰고 있습니다 (두 번 반영)',
    cp_meas: '온도와 같이 움직입니다 (겹침 ' + cp.vs_t.toFixed(2) + ')',
    all: '넣을수록 나빠졌습니다',
  };
  const key = r => (r.keys.length > 2 ? 'all' : r.keys[r.keys.length - 1]);
  const label = r => (r.keys.length > 2 ? '＋ 네 개 전부' : NAME[key(r)]);
  /* 종전 판에는 오차 크기 막대가 있었다. 값이 1.30~1.44 라 막대 길이가 10%
     밖에 안 벌어져 눈으로 구분되지 않았다(미리보기로 확인). 막대를 걷고
     **기준과의 차이**를 숫자로 적는다 — 그게 이 표에서 볼 값이다. */
  const COL = [{ label: '넣은 값', w: 176 },
               { label: '평균 오차', w: 88, align: 'right', mono: true },
               { label: '기준과 차이', w: 110, align: 'right', mono: true },
               { label: '판정', w: 78 },
               { label: '까닭', w: 638 }];
  const diff = r => {
    if (!r.vs_base) return { t: '기준', px: 11, color: C.dim2 };
    const v = r.vs_base.d_mae;
    return { t: (v > 0 ? '+' : '−') + Math.abs(v).toFixed(2), px: 11, bold: true,
             color: v > 0 ? C.red : C.slateL };
  };
  const tb = d.table(92, y1, COL,
    V.rows.map((r, i) => [
      { t: label(r), bold: i === 0, color: i === 0 ? C.ink : C.body },
      { t: r.mae.toFixed(2), bold: i === 0, color: i === 0 ? C.brass : C.dim },
      diff(r), { t: i === 0 ? '★ 선정' : '제외', px: 11.5, bold: i === 0,
                 color: i === 0 ? C.brass : C.dim2 },
      { t: WHY[key(r)], px: 11.5 }]),
    { rh: 24, hh: 26, hi: 0 });
  d.text('단위 MW · 작을수록 잘 맞힌 것입니다. 회차마다 흔들리는 폭이 ±' +
         near.vs_base.se.toFixed(2) + ' 이므로 그보다 작은 차이는 차이로 볼 수 ' +
         '없습니다. 한 회를 가리고 나머지로 그 회를 맞혀 보는 방식으로 채점했습니다.',
         { x: 92, y: y1 + tb.h + 10, w: 1090, px: 10.5, lh: 1.3, color: C.dim2 });

  /* ── 구획 2 · 외기 온도가 남은 이유 ──────────────────────────── */
  const y2 = d.section(G.L, 422, 556, 218, 2, '외기 온도가 남은 이유', '');
  [['혼자서 대부분을 설명한다',
    '차이의 85% 가 온도로 설명됩니다. 추우면 커지고 더우면 작아집니다.'],
   ['방향이 분명하다',
    '온도와 차이가 반대로 움직입니다 (겹침 ' + Math.abs(CZ.rows[0].raw).toFixed(2) +
    '). 네 후보 가운데 가장 뚜렷합니다.'],
   ['미리 알 수 있는 값이다',
    '신고는 영하 20도부터 40도까지 온도마다 내야 합니다. 입력이 온도여야 표를 만들 수 있습니다.']]
    .forEach(([k, v], i) => {
      const y = y2 + i * 60;
      d.rect(92, y + 2, 4, 44, C.brass);
      d.text(String(i + 1), { x: 108, y, w: 18, px: 12, lh: 1.2, mono: true, bold: true,
                              color: C.brass });
      d.text(k, { x: 130, y: y - 2, w: 478, px: 15, lh: 1.25, bold: true, color: C.ink });
      d.text(v, { x: 130, y: y + 20, w: 478, px: 11.5, lh: 1.4, lines: 2, color: C.dim });
    });

  /* ── 구획 3 · 어려웠던 점 · 결론을 뒤집었다 (IGV) ───────────────
     쉽게 쓰라는 회신에 따라 'IGV turn-up' 은 괄호로만 남기고, 본문은
     "출력을 끝까지 올려야 하는데 그 조작을 안 했다" 로 풀었다.          */
  const y3 = d.section(644, 422, 564, 218, 3, '어려웠던 점 · 결론을 뒤집었다', '');
  d.text('봄 시험 몇 회가 유별나게 낮았습니다. 설비가 늙었다고 보고 문서까지 썼습니다.',
         { x: 664, y: y3, w: 524, px: 13, lh: 1.45, lines: 2, color: C.dim });
  d.rect(664, y3 + 46, 4, 96, C.red);
  d.text('설비 문제가 아니었습니다.',
         { x: 684, y: y3 + 44, w: 504, px: 15.5, lh: 1.3, bold: true, color: C.ink });
  d.text('이 시험은 *출력을 끝까지 올린 상태*에서 해야 합니다. 가스터빈 입구 날개를 ' +
         '더 여는 조작입니다(IGV turn-up). 그 조작을 하지 않고 측정한 날이었습니다. ' +
         '덜 올린 채로 쟀으니 낮게 나온 것입니다.',
         { x: 684, y: y3 + 68, w: 504, px: 12, lh: 1.45, lines: 4, color: C.body });
  d.text('보고 결론을 거뒀습니다. 지금은 그런 날의 시험을 도구가 걸러냅니다.',
         { x: 664, y: y3 + 150, w: 524, px: 12, lh: 1.35, lines: 2, color: C.dim2 });

  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '후보를 하나씩 접고 나니 외기 온도만 남았습니다.');
};
