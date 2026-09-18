/* v3 밝은 테마 — 사내 발표자료(SK) 양식을 참고했다.
   2026-09-17 회신: "PPT 색이 어두운데 다시 밝은 색으로 컨셉을 바꿔보자.
   ppt 컨셉 색상과 Tool 색상이 같다보니 Tool 캡쳐 이미지가 잘 보이지 않음."

   어두운 테마에서 도구 캡처(다크)를 얹으면 서로 묻혔다. 흰 바탕으로 바꾸면
   캡처가 도리어 또렷해진다. 색 역할도 사내 양식에 맞춰 다시 정했다.

     레드    강조 · 현재 · 좋아진 것      (제목 바 · 구획 라벨 · 큰 숫자)
     주황    주의 · 위험
     회색    종전 · 참조
     남색    표 머리
   어두운 테마(theme.js)는 그대로 둔다 — 18장판과 v2 가 쓴다.            */
const C = {
  ground : 'FFFFFF',  // 배경 — 흰색
  groove : 'FFFFFF',  // 데이터가 앉는 면. 흰 바탕에서는 테두리로 구획한다
  head   : 'F2F5F9',  // 구획 머리 띠 — 아주 연한 회청
  rule   : 'C9D0D8',  // 헤어라인
  rule2  : 'DEE3E9',  // 더 약한 헤어라인
  ink    : '1A1A1A',  // 제목·강조 본문
  body   : '333333',  // 본문 문장
  dim    : '5A5A5A',  // 캡션·부가
  dim2   : '8C8C8C',  // 라벨
  brass  : 'EA002C',  // 강조 · 현재 · 좋아진 것 (사내 양식의 주 강조색)
  brassD : 'F5A3B0',  // 열세 후보 막대 — 연한 레드
  brassS : 'FDEBEE',  // 강조 배경 (표 강조 행)
  red    : 'FF6F0F',  // 주의 · 위험 — 주황
  redD   : 'FFD9B8',
  slate  : '9AA3AC',  // 종전 — 채워진 면
  slateL : '6E7780',  // 종전 — 선·글씨 (밝은 바탕이라 어둡게)
  steel  : 'C4CAD1',  // 중위 후보 막대
  navy   : '1B3C6E',  // 표 머리
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

/* 선 굵기 — 차트 선은 여기서만 정한다. 굵은 선은 데이터를 가리고 화면을
   무겁게 만든다. 얇게 두고 색으로 구분한다.
     main 모델·개선 주 곡선 / ref 종전·이론 점선 / aux 보조 곡선(후보 커널)
     mark 임계선·브래킷 / grid 눈금선·축선                                  */
const LW = { main: 1.8, ref: 1.4, aux: 1.0, mark: 1.2, grid: 1 };

/* 캡처 그림 경로 — docs/ppt/assets/. build.js 를 어디서 돌려도 같은 파일을
   가리키게 이 파일 위치를 기준으로 만든다. */
const path = require('path');
const ASSET = name => path.join(__dirname, '..', 'assets', name);

/* PNG 원본 픽셀 크기 (IHDR). 비율을 지켜 배치하려면 알아야 한다. 같은 파일을
   여러 장에서 쓰므로 한 번 읽고 기억한다. */
const _pngCache = new Map();
function pngSize(file) {
  if (_pngCache.has(file)) return _pngCache.get(file);
  const fd = require('fs').openSync(file, 'r');
  const buf = Buffer.alloc(24);
  require('fs').readSync(fd, buf, 0, 24, 0);
  require('fs').closeSync(fd);
  if (buf.slice(0, 8).toString('hex') !== '89504e470d0a1a0a')
    throw new Error('PNG 이 아닙니다: ' + file);
  const wh = [buf.readUInt32BE(16), buf.readUInt32BE(20)];
  _pngCache.set(file, wh);
  return wh;
}

/* px → in / pt */
const IN = px => px / 96;
const PT = px => px * 0.75;

/* 여백·기준선 (계획서 §5.3) */
const G = {
  L: 72, R: 1208, W: 1136,          // 좌우 외곽여백과 본문 폭
  SEC_Y: 36,                        // 섹션명 / 진행 눈금 — 선언 여백과 같은 줄에 둔다
  RULE1: 66,                        // 헤더 헤어라인
  TITLE_Y: 84, TITLE_PX: 33, TITLE_LH: 1.26,
  LEAD_Y: 134, LEAD_PX: 17, LEAD_LH: 1.55,
  BODY_Y: 284,                      // 본문 영역 시작
  RULE2: 646,                       // 하단 헤어라인
  FOOT_Y: 662,
  SUB_PX: 21, SUB_LH: 1.42,
  TXT_PX: 15, TXT_LH: 1.68,
  LAB_PX: 10.5,
};

/* ── 인라인 강조 마크업 ───────────────────────────────────────────────
   *레드볼드*  _먹색볼드_  ~~슬레이트~~  `숫자는 Consolas`
   슬라이드 문장을 한 줄로 쓰고 색·서체는 여기서 붙인다.

   슬레이트만 물결 **두 개**다. 하나였을 때 `20~25℃ 는 1회, 15~20℃ 는 3회`
   같은 문장에서 두 물결 사이가 마크업으로 먹혀 `2025℃ 는 1회, 1520℃` 로
   나왔다(미리보기로 발견). 온도 구간을 적을 일이 많은 장표라 물결은 글자로
   쓰는 편이 자연스럽고, 강조 쪽을 두 개로 미루는 것이 맞다.
   어두운 테마(theme.js)는 그대로 하나다 — 18장판이 `~이론 출력~` 처럼
   이미 쓰고 있어서 규칙을 바꾸면 그 판이 깨진다.                      */
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
  const re = /(\*[^*]+\*|_[^_]+_|~~[^~]+~~|`[^`]+`)/g;
  const out = []; let i = 0, m;
  while ((m = re.exec(str)) !== null) {
    if (m.index > i) out.push({ text: str.slice(i, m.index), options: Object.assign({}, b) });
    const tok = m[0], body = tok.slice(1, -1), o = Object.assign({}, b);
    if (tok[0] === '*') { o.color = C.brass; o.bold = true; }
    else if (tok[0] === '_') { o.color = C.ink; o.bold = true; }
    else if (tok[0] === '~') { o.color = C.slate; }
    else { o.fontFace = F.mono; }
    out.push({ text: tok[0] === '~' ? tok.slice(2, -2) : body, options: o });
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
    zone(x, y, w, h) { return api.box(x, y, w, h, C.groove, C.rule, 1); },
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
    /* 구획 — 번호 붙은 머리 띠와 테두리. 회신 "구획을 더 또렷하게" 반영.
       종전 zone() 은 홈 면에 헤어라인 하나여서 네이비 배경에서 거의 안 보였다.
       층을 셋으로 갈라 세운다.
         몸통  groove (가장 어둡다)
         머리  head   (가장 밝다) + 왼쪽 놋빛 바 + 번호
         테두리 rule 1.2 (헤어라인 한 단 위)
       돌려주는 값은 **내용이 시작되는 y** 다. 장마다 좌표를 다시 세지 않는다. */
    section(x, y, w, h, no, label, right) {
      /* 사내 양식은 색 라벨(pill)을 상자 왼쪽 위에 얹는다. 흰 바탕에서는
         띠를 깔기보다 이 쪽이 또렷하다. 돌려주는 값은 내용 시작 y. */
      const PH = 26, PW = Math.ceil(textW(label, 13.5)) + (no != null ? 54 : 30);
      api.box(x, y + 13, w, h - 13, C.groove, C.rule, 1);
      api.rect(x, y, PW, PH, C.brass, { rectRadius: 0.12, shape: 'roundRect' });
      let tx = x + 14;
      if (no != null) {
        api.text(String(no), { x: tx, y: y + 6, w: 16, px: 12.5, lh: 1.2, mono: true,
                               bold: true, color: 'FFFFFF' });
        tx += 20;
      }
      api.text(label, { x: tx, y: y + 6, w: PW - (tx - x) - 12, px: 13.5, lh: 1.2,
                        bold: true, color: 'FFFFFF' });
      if (right) {
        const RW = Math.ceil(textW(right, 11)) + 10;
        api.text(right, { x: x + w - RW - 12, y: y + 20, w: RW, px: 11, lh: 1.2,
                          color: C.dim2, align: 'right' });
      }
      return y + PH + 12;
    },
    /* 표 — 헤더 음영과 줄 구분선까지 그린다. '잘 만든 보고서' 느낌은 표에서
       많이 온다. 숫자를 그냥 늘어놓는 것과 표로 앉히는 것은 다르게 읽힌다.
         cols: [{ label, w, align, mono }]
         rows: [[셀, 셀, ...], ...]   셀은 문자열이거나 { t, color, bold, px }
         o.foot: 맨 아래 요약 행(같은 형식). 위에 굵은 선을 둔다.            */
    table(x, y, cols, rows, o) {
      o = o || {};
      const rh = o.rh || 23, hh = o.hh || 26;
      const W = cols.reduce((a, c) => a + c.w, 0);
      const cell = (v, c, cy, def, mono) => {
        const t = (v && typeof v === 'object') ? v : { t: v };
        api.text(String(t.t == null ? '' : t.t),
          { x: cx + 9, y: cy, w: c.w - 18, px: t.px || 12.5, lh: 1.2,
            mono: mono == null ? c.mono : mono,
            bold: t.bold, color: t.color || def, align: c.align || 'left' });
      };
      let cx = x;
      api.rect(x, y, W, hh, C.navy);
      /* 머리글은 숫자 열이라도 한글 서체로 둔다. Consolas 로 두면 한글이
         대체 서체로 떨어져 '평균  오차' 처럼 자간이 벌어져 보인다. */
      cols.forEach(c => { cell(c.label, c, y + 8, 'FFFFFF', false); cx += c.w; });
      rows.forEach((r, i) => {
        const ry = y + hh + i * rh;
        if (o.hi === i) api.rect(x, ry, W, rh, C.brassS);
        else if (i % 2 === 1) api.rect(x, ry, W, rh, C.head);
        api.hline(x, ry + rh, W, C.rule2, 1);
        cx = x;
        cols.forEach((c, j) => { cell(r[j], c, ry + (rh - 15) / 2, C.body); cx += c.w; });
      });
      let h = hh + rows.length * rh;
      if (o.foot) {
        const fy = y + h;
        api.hline(x, fy, W, C.rule, 1.2);
        cx = x;
        cols.forEach((c, j) => { cell(o.foot[j], c, fy + (rh - 15) / 2 + 2, C.dim); cx += c.w; });
        h += rh + 2;
      }
      return { w: W, h };
    },
    /* 원본 비율을 지켜 상자 안에 맞춘다. 캡처는 가로세로비가 제각각이라
       (엑셀 실적 3.1:1, 온도별 표 1.2:1) 상자에 억지로 늘리면 글자가 뭉개진다.
       상자 안에서 가운데 정렬하고, 남는 자리는 비운다. */
    imgFit(name, bx, by, bw, bh, opt) {
      const [iw, ih] = pngSize(ASSET(name));
      const k = Math.min(bw / iw, bh / ih);
      const w = iw * k, h = ih * k;
      return api.img(name, bx + (bw - w) / 2, by + (bh - h) / 2, w, h, opt);
    },
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
let _page = 0;                      // 쪽번호 — shell 을 부른 순서대로 센다

function shell(pptx, opt) {
  const s = pptx.addSlide();
  s.background = { color: C.ground };
  const d = draw(pptx, s);
  opt = opt || {};

  /* 사내 양식 — 제목 왼쪽에 굵은 빨간 바, 우상단에 작은 회색 소제목 */
  if (opt.bar === true || (opt.bar !== false && (opt.sec || opt.idx)))
    d.rect(G.L - 22, 34, 8, 44, C.brass);
  if (opt.sec || opt.idx) {
    const runs = [];
    if (opt.idx) {
      runs.push({ text: String(opt.idx).padStart(2, '0') + '  ',
                  options: { fontFace: F.mono, bold: true, color: C.brass, fontSize: PT(13) } });
      runs.push({ text: opt.name || INDEX[opt.idx - 1],
                  options: { fontFace: F.kr, bold: true, color: C.dim, fontSize: PT(13) } });
    } else {
      runs.push({ text: opt.sec,
                  options: { fontFace: F.kr, bold: true, color: C.dim, fontSize: PT(13) } });
    }
    d.text(runs, { x: G.L, y: 36, w: 700, px: 13, lh: 1.25, cs: 0.6 });
  }
  if (opt.topRight !== false)
    d.text('AI FRONTIER  ·  위례사업소', { x: 808, y: 38, w: 400, px: 10, lh: 1.2,
                                            mono: true, color: C.dim2, cs: 1.6,
                                            align: 'right' });

  if (opt.step) {                    // 진행 눈금 7개 — 흰 바탕용 색으로
    for (let i = 0; i < 7; i++) {
      const x = 1120 + i * 14, on = (i + 1) === opt.step;
      d.rect(x, on ? 60 : 65, 4, on ? 13 : 7, on ? C.brass : C.rule);
    }
  }

  _page += 1;
  if (opt.page !== false) d.text(String(_page), { x: 1150, y: 688, w: 58, px: 11,
    lh: 1.2, mono: true, color: C.dim2, align: 'right' });
  return { s, d };
}

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
  d.rect(G.L, G.FOOT_Y - 1, 46, 20, C.brass, { rectRadius: 0.2, shape: 'roundRect' });
  d.text('결론', { x: G.L, y: G.FOOT_Y + 2, w: 46, px: 11, lh: 1.2, bold: true,
                   color: 'FFFFFF', align: 'center' });
  return d.text(str, { x: G.L + 58, y: G.FOOT_Y, w: G.W - 58 - 70, px: 15.5, lh: 1.4,
                       bold: true, color: C.ink });
}

module.exports = { C, F, LW, IN, PT, G, INDEX, ASSET, pngSize, rt, textW, draw,
                   shell, title, lead, foot, resetPage: () => { _page = 0; } };
