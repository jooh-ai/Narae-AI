#!/usr/bin/env node
/* ══════════════════════════════════════════════════════════════════════
   장표 미리보기 — pptx 를 이미지로 못 여는 환경에서 눈으로 보는 수단.

     node docs/ppt/build/preview.js --v3            전 장
     node docs/ppt/build/preview.js --v3 --only 4,5  4·5장만
     → docs/ppt/build/preview/slideNN.html  +  .png  (headless Chromium)

   이 환경에는 LibreOffice 가 있지만 어떤 파일도 열지 못한다("source file
   could not be loaded"). 그래서 종전에는 verify.py 의 좌표 검사만으로
   장표를 판단했다 — 겹침·넘침은 잡히지만 **색·굵기·여백이 보기에 어떤지**는
   알 수 없었다. 밝은 테마로 바꾸는 작업을 눈 없이 할 수는 없어서 만들었다.

   방식 — pptxgenjs 흉내를 내는 가짜 pptx 를 하나 만들고, **테마와 슬라이드
   코드는 손대지 않고 그대로 돌린다**. addShape/addText/addImage 를 받아
   HTML 절대좌표 div 로 옮긴다. 좌표는 인치로 오므로 ×96, 글자 크기는 pt 로
   오므로 ÷0.75 해서 원래 px 로 되돌린다. 호출 순서를 z-index 로 주어
   앞뒤 관계도 pptx 와 같게 둔다.

   한계 — 맑은 고딕이 이 환경에 없어 나눔고딕으로 그린다. 자폭이 조금 달라
   줄바꿈 위치가 발표자 PC 와 한두 글자 어긋날 수 있다. 색·구조·여백을 보는
   용도이고, 넘침 최종 판정은 verify.py 가 한다.
   ══════════════════════════════════════════════════════════════════════ */
'use strict';
const fs = require('fs'), path = require('path'), { execFileSync } = require('child_process');

const DIR = __dirname;
const V3 = process.argv.includes('--v3');
const T = require(V3 ? './theme_light.js' : './theme.js');
const SLIDE_DIR = path.join(DIR, V3 ? 'slides_v3' : 'slides');
const STATE = JSON.parse(fs.readFileSync(
  path.join(DIR, V3 ? 'BUILD_STATE_V3.json' : 'BUILD_STATE.json'), 'utf8'));
const DATA = JSON.parse(fs.readFileSync(path.join(DIR, 'deck_data.json'), 'utf8'));
const OUTDIR = path.join(DIR, 'preview');
const CHROME = '/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell';

const onlyArg = process.argv.indexOf('--only');
const ONLY = onlyArg > 0 ? new Set(process.argv[onlyArg + 1].split(',').map(Number)) : null;
const SCALE = 1;

const FONT = f => (/Consolas/i.test(f)
  ? "'Consolas','DejaVu Sans Mono','Liberation Mono',monospace"
  : "'Malgun Gothic','NanumGothic','NanumBarunGothic','Noto Sans KR',sans-serif");
const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const PXI = v => (v == null ? 0 : v * 96);          // 인치 → px
const PXP = v => (v == null ? 0 : v / 0.75);        // pt   → px

/* ── 가짜 pptx ──────────────────────────────────────────────────── */
function fakeSlide() {
  const parts = [];
  let z = 0;
  const self = {
    background: { color: 'FFFFFF' },
    notes: '',
    addNotes(s) { self.notes = s; },
    addShape(kind, o) {
      z += 1;
      const x = PXI(o.x), y = PXI(o.y), w = PXI(o.w), h = PXI(o.h);
      const st = [`left:${x}px`, `top:${y}px`, `width:${w}px`, `height:${h}px`,
                  `z-index:${z}`, 'position:absolute'];
      if (kind === 'line') {
        /* 가로·세로선은 bbox 두께가 0 이다. svg 를 0 높이로 두면 선이 절반만
           그려져 거의 안 보인다. 선굵기만큼 패딩을 두고 그 안에서 그린다
           (미리보기용 1px 어긋남은 색·굵기를 보는 데 지장이 없다). */
        const ln = o.line || {};
        const lw = ln.width || 1, p = Math.ceil(lw) + 1;
        const d = o.flipV ? `M${p},${h + p} L${w + p},${p}`
                          : `M${p},${p} L${w + p},${h + p}`;
        const dash = ln.dashType === 'dash' ? ` stroke-dasharray="${lw * 4},${lw * 3}"` : '';
        const st2 = [`left:${x - p}px`, `top:${y - p}px`, `width:${w + p * 2}px`,
                     `height:${h + p * 2}px`, `z-index:${z}`, 'position:absolute'];
        parts.push(`<svg style="${st2.join(';')};overflow:visible" `
          + `width="${w + p * 2}" height="${h + p * 2}"><path d="${d}" `
          + `stroke="#${ln.color || '000'}" stroke-width="${lw}" fill="none"${dash}/></svg>`);
        return self;
      }
      if (o.fill && o.fill.color) st.push(`background:#${o.fill.color}`);
      if (o.line && o.line.type !== 'none' && o.line.color) {
        st.push(`border:${o.line.width || 1}px ${o.line.dashType === 'dash' ? 'dashed' : 'solid'} #${o.line.color}`);
        st.push('box-sizing:border-box');
      }
      if (kind === 'ellipse') st.push('border-radius:50%');
      else if (o.shape === 'roundRect') st.push(`border-radius:${(o.rectRadius || 0.1) * Math.min(w, h) * 2}px`);
      parts.push(`<div style="${st.join(';')}"></div>`);
      return self;
    },
    addText(body, o) {
      z += 1;
      const px = PXP(o.fontSize), lh = PXP(o.lineSpacing) || px * 1.4;
      const st = [`left:${PXI(o.x)}px`, `top:${PXI(o.y)}px`, `width:${PXI(o.w)}px`,
                  `height:${PXI(o.h)}px`, `z-index:${z}`, 'position:absolute',
                  `font-size:${px}px`, `line-height:${lh}px`,
                  `color:#${o.color || '000000'}`, `font-family:${FONT(o.fontFace || '')}`,
                  `text-align:${o.align || 'left'}`, 'display:flex', 'flex-direction:column',
                  `justify-content:${o.valign === 'middle' ? 'center' : o.valign === 'bottom' ? 'flex-end' : 'flex-start'}`,
                  'overflow:visible', 'white-space:pre-wrap', 'word-break:break-word'];
      if (o.bold) st.push('font-weight:700');
      if (o.charSpacing) st.push(`letter-spacing:${PXP(o.charSpacing)}px`);
      let html;
      if (typeof body === 'string') html = esc(body);
      else html = body.map(r => {
        const b = r.options || {}, s2 = [];
        if (b.color) s2.push(`color:#${b.color}`);
        if (b.bold) s2.push('font-weight:700');
        if (b.fontFace) s2.push(`font-family:${FONT(b.fontFace)}`);
        if (b.fontSize) s2.push(`font-size:${PXP(b.fontSize)}px`);
        return `<span style="${s2.join(';')}">${esc(r.text)}</span>`
             + (b.breakLine ? '<br/>' : '');
      }).join('');
      /* 런(run)은 pptx 에서 한 줄 안에 이어 흐른다. flex 컨테이너의 자식으로
         두면 런마다 줄이 갈리므로 안쪽 div 하나에 담아 흐르게 한다. */
      parts.push(`<div style="${st.join(';')}"><div style="width:100%">`
        + `${html.replace(/\n/g, '<br/>')}</div></div>`);
      return self;
    },
    addImage(o) {
      z += 1;
      parts.push(`<img src="file://${o.path}" style="left:${PXI(o.x)}px;top:${PXI(o.y)}px;`
        + `width:${PXI(o.w)}px;height:${PXI(o.h)}px;z-index:${z};position:absolute"/>`);
      return self;
    },
  };
  self._parts = parts;
  return self;
}

function fakePptx() {
  const slides = [];
  return {
    slides,
    ShapeType: { rect: 'rect', line: 'line', ellipse: 'ellipse' },
    defineLayout() {}, set layout(_v) {},
    addSlide() { const s = fakeSlide(); slides.push(s); return s; },
  };
}

/* ── 그리기 ─────────────────────────────────────────────────────── */
fs.mkdirSync(OUTDIR, { recursive: true });
const pptx = fakePptx();
if (T.resetPage) T.resetPage();
const made = [];
/* 부록 한 장만 미리보기 — node preview.js --v3 --one x01_model */
const oneIdx = process.argv.indexOf('--one');
const PREFIX = oneIdx > 0 ? 'one' : 'slide';   // 부록은 본편 파일을 덮지 않는다
if (oneIdx > 0) {
  const names = String(process.argv[oneIdx + 1]).split(',')
    .map(s => s.trim()).filter(Boolean);
  for (const nm of names) {
    const before = pptx.slides.length;
    require(path.join(SLIDE_DIR, nm + '.js'))(pptx, T, STATE.meta, DATA);
    for (let i = before; i < pptx.slides.length; i++)
      made.push([made.length, pptx.slides[i]]);   // 부록도 장마다 다른 파일로
  }
  STATE.slides = [];
}
for (const it of STATE.slides) {
  const f = path.join(SLIDE_DIR, it.file);
  if (!fs.existsSync(f)) continue;
  const before = pptx.slides.length;
  require(f)(pptx, T, STATE.meta, DATA);
  for (let i = before; i < pptx.slides.length; i++) made.push([it.no, pptx.slides[i]]);
}

const shots = [];
for (const [no, s] of made) {
  if (ONLY && !ONLY.has(no)) continue;
  const html = `<!doctype html><meta charset="utf-8"><style>
html,body{margin:0;padding:0}
#slide{position:relative;width:1280px;height:720px;overflow:hidden;
       background:#${s.background.color}}
#slide div,#slide img,#slide svg{box-sizing:content-box}
</style><div id="slide">${s._parts.join('\n')}</div>`;
  const hp = path.join(OUTDIR, `${PREFIX}${String(no).padStart(2, '0')}.html`);
  fs.writeFileSync(hp, html, 'utf8');
  shots.push([no, hp, path.join(OUTDIR, `${PREFIX}${String(no).padStart(2, '0')}.png`)]);
}

for (const [no, hp, pp] of shots) {
  execFileSync(CHROME, ['--headless', '--disable-gpu', '--no-sandbox',
    '--allow-file-access-from-files', '--hide-scrollbars',
    `--force-device-scale-factor=${SCALE}`, '--window-size=1280,720',
    `--screenshot=${pp}`, `--virtual-time-budget=2500`, `file://${hp}`],
    { stdio: 'ignore' });
  console.log(`  ${String(no).padStart(2, '0')}  ${path.relative(process.cwd(), pp)}`
    + `  (${(fs.statSync(pp).size / 1024).toFixed(0)} KB)`);
}
