/* ══════════════════════════════════════════════════════════════════════
   위례 공급가능용량 최종 발표 — 공용 테마 · 좌표 · 그리기 도구
   디자인 v2 「계측 기록지」 (계획서 §5.0~5.3, 목업 docs/ppt/design_v2.html)

   좌표계는 목업과 같은 1280×720 px 이다. 1280 px = 13.333 in @96dpi 이므로
   px ÷ 96 = in, px × 0.75 = pt 로 1:1 이식된다. 슬라이드 코드는 전부 px 로
   쓰고 변환은 이 파일에서만 한다 — 목업과 pptx 를 눈으로 대조할 수 있다.
   ══════════════════════════════════════════════════════════════════════ */
'use strict';

const C = {
  ground : '0F1A28',  // 배경 — 검정이 아니라 '푸른' 네이비
  groove : '0A1320',  // 데이터가 앉는 홈 면
  rule   : '22354A',  // 헤어라인
  rule2  : '182838',  // 더 약한 헤어라인
  ink    : 'EAE7E0',  // 본문 강조 — 따뜻한 회백            14.2 : 1
  body   : 'CFCBC2',  // 본문 문장 — 따뜻한 밝은 회색        10.8 : 1  (← 10.4)
  dim    : 'A9A79F',  // 캡션·부가                            7.3 : 1  (←  7.0)
  dim2   : '8A8880',  // 라벨                                 4.9 : 1  (←  3.9)
  brass  : 'EFB13C',  // 개선·핵심 수치                       9.2 : 1
  brassD : '8A6620',  // 열세 후보 막대
  red    : 'FF4D63',  // 위험·미달                            5.4 : 1
  redD   : '7E2333',
  slate  : '718BA6',  // 종전 — 채워진 면(막대·박스)          5.0 : 1  (←  3.8)
  slateL : 'A8BCD1',  // 종전 — 선(점선·침)                   9.0 : 1  (←  6.7)
  steel  : '55708A',  // 중위 후보 막대
};

/* 회색이 안 보이던 이유 — 남색 바탕(#0F1A28)에 '푸른 회색' 글자를 얹으면
   명도차가 있어도 색상이 같은 계열이라 바탕에 묻힌다. 빨강·노랑·흰색이
   잘 보였던 것은 색상이 반대편이라 명도 말고 색상으로도 갈렸기 때문이다.
   그래서 중립색 계열을 전부 '따뜻한 회색'으로 돌렸다. 종전 방식(슬레이트)만
   푸른 계열로 남긴다 — 앰버(개선)와 반대편이어야 뜻이 갈리기 때문이다.
   근거: 본문은 바꾸기 전에도 이미 10.4:1 이었는데 안 보였다 — 명도 문제가
   아니라는 증거다. 다만 라벨(3.9:1)과 종전 면(3.8:1)은 AA 미달이기도 했다.
   이제 전 색이 AA(4.5:1)를 넘는다. */

/* 목차 7개 — 모든 장의 머리글이 여기서 나온다. 표현을 바꾸려면 이 줄만
   고치면 목차 장과 15개 본문 장의 머리글이 함께 바뀐다. */
const INDEX = [
  '개요 및 추진 배경',
  '현황 파악 및 문제 정의',
  '데이터 분석 및 원인 규명(가설 검증)',
  '해결 방안 도출 및 예측/보정 모델 개발',
  '향후 추이 분석(모니터링 체계 구축)',
  '개선 효과(정량적/정성적)',
  '향후 계획 및 수평 전개 방안',
];

const F = { kr: 'Malgun Gothic', mono: 'Consolas' };

/* 캡처 그림 경로 — docs/ppt/assets/. build.js 를 어디서 돌려도 같은 파일을
   가리키게 이 파일 위치를 기준으로 만든다. */
const path = require('path');
const ASSET = name => path.join(__dirname, '..', 'assets', name);

/* px → in / pt */
const IN = px => px / 96;
const PT = px => px * 0.75;

/* 여백·기준선 (계획서 §5.3) */
const G = {
  L: 72, R: 1208, W: 1136,          // 좌우 외곽여백과 본문 폭
  SEC_Y: 44,                        // 섹션명 / 진행 눈금 — 선언 여백과 같은 줄에 둔다
  RULE1: 72,                        // 헤더 헤어라인
  TITLE_Y: 96, TITLE_PX: 37, TITLE_LH: 1.26,
  LEAD_Y: 210, LEAD_PX: 18, LEAD_LH: 1.66,
  BODY_Y: 284,                      // 본문 영역 시작
  RULE2: 636,                       // 하단 헤어라인
  FOOT_Y: 654,
  SUB_PX: 21, SUB_LH: 1.42,
  TXT_PX: 15, TXT_LH: 1.68,
  LAB_PX: 10.5,
};

/* ── 인라인 강조 마크업 ───────────────────────────────────────────────
   *앰버볼드*  _회백볼드_  ~슬레이트~  `숫자는 Consolas`
   슬라이드 문장을 한 줄로 쓰고 색·서체는 여기서 붙인다.            */
/* 자막폭 추정 — verify.py 와 같은 모델을 쓴다.
   한글·기호 1.0em / 영숫자 0.55em(Consolas 자폭) + 10% 안전 여유.
   숫자 박스를 이 폭으로 잡아야 박스가 겹치지도, 검증에서 넘치지도 않는다. */
function textW(str, px_) {
  let w = 0;
  for (const ch of str) w += px_ * (ch.codePointAt(0) > 0x2000 ? 1.0 : 0.55);
  return w * 1.10;
}

function rt(str, base) {
  const b = Object.assign({ fontFace: F.kr }, base || {});
  const re = /(\*[^*]+\*|_[^_]+_|~[^~]+~|`[^`]+`)/g;
  const out = []; let i = 0, m;
  while ((m = re.exec(str)) !== null) {
    if (m.index > i) out.push({ text: str.slice(i, m.index), options: Object.assign({}, b) });
    const tok = m[0], body = tok.slice(1, -1), o = Object.assign({}, b);
    if (tok[0] === '*') { o.color = C.brass; o.bold = true; }
    else if (tok[0] === '_') { o.color = C.ink; o.bold = true; }
    else if (tok[0] === '~') { o.color = C.slate; }
    else { o.fontFace = F.mono; }
    out.push({ text: body, options: o });
    i = m.index + tok.length;
  }
  if (i < str.length) out.push({ text: str.slice(i), options: Object.assign({}, b) });
  return out.length ? out : [{ text: str, options: b }];
}

/* ── 그리기 도구 — 한 슬라이드에 묶어서 준다 ───────────────────────── */
function draw(pptx, s) {
  const R = pptx.ShapeType.rect, LN = pptx.ShapeType.line, EL = pptx.ShapeType.ellipse;

  const api = {
    /* 채운 사각형 (막대·홈 면·룰) */
    rect(x, y, w, h, color, opt) {
      s.addShape(R, Object.assign({
        x: IN(x), y: IN(y), w: IN(w), h: IN(h),
        fill: { color }, line: { type: 'none' },
      }, opt || {}));
      return api;
    },
    /* 테두리만 있는 사각형 (홈 면 테두리·자리표시자 프레임) */
    box(x, y, w, h, fillColor, lineColor, lineW, dash) {
      s.addShape(R, {
        x: IN(x), y: IN(y), w: IN(w), h: IN(h),
        fill: fillColor ? { color: fillColor } : { type: 'none' },
        line: { color: lineColor || C.rule, width: lineW || 1, dashType: dash || 'solid' },
      });
      return api;
    },
    /* 임의 두 점 사이의 선. pptx line 은 bbox 대각선이라 방향은 flip 으로 준다 */
    seg(x1, y1, x2, y2, color, width, dash) {
      const x = Math.min(x1, x2), y = Math.min(y1, y2);
      const w = Math.abs(x2 - x1), h = Math.abs(y2 - y1);
      const flipV = (x2 - x1) * (y2 - y1) < 0;
      s.addShape(LN, {
        x: IN(x), y: IN(y), w: IN(w), h: IN(h), flipV,
        line: { color, width: width || 1, dashType: dash || 'solid' },
      });
      return api;
    },
    hline(x, y, w, color, width, dash) { return api.seg(x, y, x + w, y, color, width, dash); },
    vline(x, y, h, color, width, dash) { return api.seg(x, y, x, y + h, color, width, dash); },
    dot(cx, cy, r, color) {
      s.addShape(EL, { x: IN(cx - r), y: IN(cy - r), w: IN(r * 2), h: IN(r * 2),
                       fill: { color }, line: { type: 'none' } });
      return api;
    },
    /* 텍스트 — px 좌표, px 폰트크기, 줄간격 배수 */
    text(str, o) {
      const px = o.px || G.TXT_PX, lh = o.lh || 1.4, lines = o.lines || 1;
      const h = o.h != null ? o.h : px * lh * lines;
      s.addText(typeof str === 'string' ? rt(str, {
        fontSize: PT(px), color: o.color || C.body, bold: !!o.bold,
        fontFace: o.mono ? F.mono : F.kr,
      }) : str, {
        x: IN(o.x), y: IN(o.y), w: IN(o.w), h: IN(h),
        align: o.align || 'left', valign: o.valign || 'top',
        lineSpacing: PT(px * lh), charSpacing: o.cs || 0,
        margin: 0, isTextBox: true, wrap: true, shrinkText: false,
        fontSize: PT(px), color: o.color || C.body, bold: !!o.bold,
        fontFace: o.mono ? F.mono : F.kr,
      });
      return api;
    },
    /* T4 라벨 — Consolas · 자간 넓게 */
    plab(str, x, y, w, color) {
      return api.text(str, { x, y, w, px: G.LAB_PX, lh: 1.25, mono: true, bold: true,
                             color: color || C.dim2, cs: 1.5 });
    },
    /* T2 주장 */
    sub(str, x, y, w, lines, color) {
      return api.text(str, { x, y, w, px: G.SUB_PX, lh: G.SUB_LH, bold: true,
                             lines: lines || 1, color: color || C.ink });
    },
    /* T3 본문 */
    txt(str, x, y, w, lines) {
      return api.text(str, { x, y, w, px: G.TXT_PX, lh: G.TXT_LH, lines: lines || 1 });
    },
    /* T1 데이터 — Consolas 볼드 */
    big(str, x, y, w, px, color, align) {
      return api.text(str, { x, y, w, px, lh: 1.05, mono: true, bold: true,
                             color: color || C.brass, align: align || 'left' });
    },
    /* 데이터가 앉는 홈 면 */
    zone(x, y, w, h) { return api.box(x, y, w, h, C.groove, C.rule2, 1); },
    /* 개방 패널 상단 룰 */
    panel(x, y, w, kind) {
      const col = kind === 'on' ? C.brass : kind === 'bad' ? C.redD : C.rule;
      return api.rect(x, y, w, 2, col);
    },
    /* T1 데이터 + 단위 — 숫자 박스를 글자 폭에 맞춰 좁게 잡는다.
       박스를 넓게 두면 뒤에 붙는 단위·비교값과 박스가 겹쳐 검증에 걸린다.
       Consolas 는 자폭이 0.55em 로 일정하므로 폭을 정확히 계산할 수 있다. */
    bigUnit(v, unit, x, y, px_, color, unitPx) {
      const vw = textW(v, px_) + 2;
      api.big(v, x, y, vw, px_, color);
      /* 단위 칸도 글자 폭으로 잡는다 — '%' 같은 한 글자만 오는 게 아니라
         '번에 1번' 처럼 길어질 수 있다. 고정 42px 이면 그때 넘친다. */
      if (unit) api.text(unit, { x: x + vw + 6, y: y + px_ * 0.5,
                                 w: Math.max(42, textW(unit, unitPx || 13) + 4),
                                 px: unitPx || 13, lh: 1.2, color: C.dim });
      return vw;
    },
    /* 태그 칩 */
    chip(str, x, y, w, on) {
      api.box(x, y, w, 30, null, on ? '6B5220' : C.rule, 1);
      return api.text(str, { x: x + 10, y: y + 7, w: w - 20, px: 13, lh: 1.2,
                             color: on ? C.brass : C.dim });
    },
    arrow(x, y) { return api.text('→', { x, y, w: 20, px: 13, lh: 1.2, color: C.dim2, align: 'center' }); },
    /* 그림 — Tool 화면 캡처. 테두리를 한 줄 둘러 '창' 이라는 것을 보이게 한다.
       캡처는 docs/ppt/assets/ 에 있고 파일명만 준다(ASSET 이 경로를 만든다).
       w·h 는 원본 비율대로 넣는다 — 늘리면 글자가 뭉개져서 캡처가 지저분해진다. */
    img(name, x, y, w, h, opt) {
      s.addImage(Object.assign({
        path: ASSET(name), x: IN(x), y: IN(y), w: IN(w), h: IN(h),
      }, opt || {}));
      if (!opt || opt.frame !== false) api.box(x - 1, y - 1, w + 2, h + 2, null, C.rule, 1);
      return api;
    },
  };
  return api;
}

/* ── 슬라이드 뼈대: 배경 · 섹션명 · 진행 눈금 · 헤어라인 ───────────── */
function shell(pptx, opt) {
  const s = pptx.addSlide();
  s.background = { color: C.ground };
  const d = draw(pptx, s);
  if (opt && (opt.sec || opt.idx)) {
    const runs = [];
    if (opt.idx) {
      runs.push({ text: String(opt.idx).padStart(2, '0') + '   ',
                  options: { fontFace: F.mono, bold: true, color: C.brass, fontSize: PT(15) } });
      runs.push({ text: INDEX[opt.idx - 1],
                  options: { fontFace: F.kr, bold: true, color: C.ink, fontSize: PT(15) } });
      if (opt.sec) runs.push({ text: '   ·   ' + opt.sec,
                  options: { fontFace: F.kr, color: C.dim, fontSize: PT(13) } });
    } else {
      runs.push({ text: opt.sec,
                  options: { fontFace: F.kr, bold: true, color: C.ink, fontSize: PT(15) } });
    }
    d.text(runs, { x: G.L, y: G.SEC_Y, w: 800, px: 15, lh: 1.28, cs: 0.6 });
  }
  if (opt && opt.step) {           // 우상단 7눈금 계기 (목차 7개)
    /* 지난 눈금이 안 보였다 — rule(#22354A)은 헤어라인용이라 배경과 거의
       같다. 남은 눈금을 dim2(따뜻한 중립 회색, 4.9:1)로 올리고 폭도 4px 로
       키운다. 앰버(현재)와 색상·길이·굵기 세 가지로 갈린다. */
    for (let i = 0; i < 7; i++) {
      const x = 1120 + i * 14, on = (i + 1) === opt.step;
      d.rect(x, on ? 44 : 51, on ? 4 : 4, on ? 15 : 8, on ? C.brass : C.dim2);
    }
  }
  if (!opt || opt.rule !== false) d.hline(G.L, G.RULE1, G.W, C.rule, 1);
  return { s, d };
}

/* 제목 2행 — 핵심 어절만 인라인 강조 (*…*) */
function title(d, l1, l2, o) {
  o = o || {};
  const px = o.px || G.TITLE_PX, y = o.y != null ? o.y : G.TITLE_Y, w = o.w || 1080;
  const runs = [];
  rt(l1, { fontSize: PT(px), bold: true, color: C.ink }).forEach(r => runs.push(r));
  if (l2) {
    runs[runs.length - 1].options.breakLine = true;
    rt(l2, { fontSize: PT(px), bold: true, color: C.ink }).forEach(r => runs.push(r));
  }
  return d.text(runs, { x: G.L, y, w, px, lh: G.TITLE_LH, lines: l2 ? 2 : 1, bold: true, color: C.ink });
}

function lead(d, str, o) {
  o = o || {};
  return d.text(str, { x: G.L, y: o.y != null ? o.y : G.LEAD_Y, w: o.w || 1080,
                       px: G.LEAD_PX, lh: G.LEAD_LH, lines: o.lines || 2 });
}

/* 하단 결론 스트립 — 앞에 mono '결론' */
function foot(d, str) {
  d.text('결론', { x: G.L, y: G.FOOT_Y + 4, w: 50, px: G.LAB_PX, lh: 1.2,
                   mono: true, bold: true, color: C.brass, cs: 1.8 });
  return d.text(str, { x: G.L + 56, y: G.FOOT_Y, w: G.W - 56, px: 16.5, lh: 1.4 });
}

module.exports = { C, F, IN, PT, G, INDEX, ASSET, rt, textW, draw, shell, title, lead, foot };
