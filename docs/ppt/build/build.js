#!/usr/bin/env node
/* ══════════════════════════════════════════════════════════════════════
   위례 공급가능용량 최종 발표 — 조립기

     node docs/ppt/build/build.js            존재하는 장만 붙여 .pptx 생성
     node docs/ppt/build/build.js --list     진행 상태만 출력

   장별로 slides/sNN.js 한 파일씩 작성한다. 이 스크립트는 BUILD_STATE.json
   순서대로 파일이 있으면 붙이고, 없으면 '작성 예정' 자리표시자를 넣는다.
   그래서 **작업이 중간에 끊겨도 항상 열리는 pptx** 가 나오고, 다음 세션은
   BUILD_STATE.json 의 todo 첫 항목부터 이어서 쓰면 된다. (RESUME.md 참조)
   ══════════════════════════════════════════════════════════════════════ */
'use strict';
const fs = require('fs'), path = require('path');
const pptxgen = require('pptxgenjs');
/* v3 는 밝은 테마(사내 양식 참고)를 쓴다. 어두운 테마는 18장판·v2 가 그대로 쓴다. */
const T = require(process.argv.includes('--v3') ? './theme_light.js' : './theme.js');

const DIR = __dirname;
/* 판(版) 세 가지. 인자 없으면 18장판, --v2 컴팩트판, --v3 스토리판(STORY.md).
   앞의 두 판은 그대로 둔다 — 되돌릴 자리가 있어야 한다. */
const V3 = process.argv.includes('--v3');
const V2 = !V3 && process.argv.includes('--v2');
const TAG = V3 ? 'v3' : V2 ? 'v2' : '';
const SLIDE_DIR = path.join(DIR, V3 ? 'slides_v3' : V2 ? 'slides_v2' : 'slides');
const STATE_PATH = path.join(DIR, V3 ? 'BUILD_STATE_V3.json'
                                : V2 ? 'BUILD_STATE_V2.json' : 'BUILD_STATE.json');
const OUT = path.join(DIR, '..', TAG ? `위례_공급가능용량_최종발표_${TAG}.pptx`
                                     : '위례_공급가능용량_최종발표.pptx');

const state = JSON.parse(fs.readFileSync(STATE_PATH, 'utf8'));
/* 장표 수치는 전부 여기서 온다. 데이터가 갱신되면 refresh_data.py 를 먼저 돌린다.
   슬라이드 코드에 숫자를 직접 적지 않는다 — 그래야 화면 값과 어긋나지 않는다. */
const DATA = JSON.parse(fs.readFileSync(path.join(DIR, 'deck_data.json'), 'utf8'));

function placeholder(pptx, it) {
  const { d } = T.shell(pptx, { sec: it.sec, idx: it.section, step: it.step });
  T.title(d, it.title, null, { px: 30 });
  d.box(T.G.L, 300, T.G.W, 220, T.C.groove, T.C.rule, 1.5, 'dash');
  d.text('작성 예정 — 이 장은 아직 만들지 않았습니다.', {
    x: T.G.L, y: 388, w: T.G.W, px: 17, lh: 1.4, color: T.C.dim2, align: 'center' });
  d.plab('SLIDE ' + String(it.no).padStart(2, '0') + '  ·  TODO', T.G.L, 424, T.G.W, T.C.redD);
  d.hline(T.G.L, T.G.RULE2, T.G.W, T.C.rule, 1);
}

/* 한 장만 뽑기 — 본편에 끼워 넣을 부록 장을 따로 만든다.
     node docs/ppt/build/build.js --v3 --one x01_model
   본편 13장은 건드리지 않는다. 쪽번호는 슬라이드 쪽에서 끈다(끼워 넣는
   자리에 따라 번호가 달라지므로 넣는 사람이 정한다).                     */
function buildOne(name) {
  const names = String(name).split(',').map(s => s.trim()).filter(Boolean);
  const pptx = new pptxgen();
  pptx.defineLayout({ name: 'W169', width: 13.333, height: 7.5 });
  pptx.layout = 'W169';
  pptx.title = names.join(' · ');
  pptx.company = '나래에너지서비스';
  pptx.author = state.meta.authors.join(', ');
  if (T.resetPage) T.resetPage();
  for (const nm of names)
    require(path.join(SLIDE_DIR, nm + '.js'))(pptx, T, state.meta, DATA);
  const out = path.join(DIR, '..', `부록_${names.join('_')}.pptx`);
  return pptx.writeFile({ fileName: out }).then(() => {
    const kb = (fs.statSync(out).size / 1024).toFixed(0);
    console.log('출력  ' + path.relative(process.cwd(), out) +
                '  (' + kb + ' KB)  ' + names.length + ' 장');
  });
}

function main() {
  const oneIdx = process.argv.indexOf('--one');
  if (oneIdx > 0) return buildOne(process.argv[oneIdx + 1]);
  const listOnly = process.argv.includes('--list');
  const pptx = new pptxgen();
  pptx.defineLayout({ name: 'W169', width: 13.333, height: 7.5 });
  pptx.layout = 'W169';
  pptx.title = '공급가능용량 산정 Tool — 최종 발표';
  pptx.subject = '위례열병합발전소 공급가능용량 산정 체계 개선';
  pptx.company = '나래에너지서비스';
  pptx.author = state.meta.authors.join(', ');

  let done = 0, todo = [];
  /* 발표자 노트 — 슬라이드 모듈은 슬라이드 객체를 돌려주지 않으므로, 각 장을
     만든 직후 pptx 가 방금 붙인 마지막 장에 노트를 단다. 노트 본문은 수치를
     deck_data 에서 받아 만든다(notes.js) — 슬라이드와 노트가 어긋나면
     발표 중에 들킨다. 노트 파일이 없는 판(18장판)은 조용히 건너뛴다. */
  let NOTES = null;
  try {
    NOTES = require(path.join(SLIDE_DIR, 'notes.js'))(DATA, state.meta);
  } catch (e) {
    if (e.code !== 'MODULE_NOT_FOUND') throw e;
  }
  let noted = 0;

  for (const it of state.slides) {
    const f = path.join(SLIDE_DIR, it.file);
    const exists = fs.existsSync(f);
    it.status = exists ? 'done' : 'todo';
    if (exists) { done++; } else { todo.push(it.no); }
    if (!listOnly) {
      if (exists) require(f)(pptx, T, state.meta, DATA);
      else placeholder(pptx, it);
      const note = NOTES && NOTES[it.no];
      if (note && pptx.slides.length) {
        pptx.slides[pptx.slides.length - 1].addNotes(note);
        noted++;
      }
    }
  }

  state.meta.updated = new Date().toISOString().slice(0, 16).replace('T', ' ');
  state.meta.done = done;
  state.meta.next = todo.length ? todo[0] : null;
  fs.writeFileSync(STATE_PATH, JSON.stringify(state, null, 2) + '\n', 'utf8');

  const bar = state.slides.map(i => (i.status === 'done' ? '■' : '□')).join('');
  console.log('진행  ' + bar + '   ' + done + ' / ' + state.slides.length + ' 장');
  if (todo.length) console.log('남음  ' + todo.join(', ') + '   → 다음: 슬라이드 ' + todo[0]);
  else console.log('전 장 완료');
  if (listOnly) return;

  return pptx.writeFile({ fileName: OUT }).then(() => {
    const kb = (fs.statSync(OUT).size / 1024).toFixed(0);
    console.log('출력  ' + path.relative(process.cwd(), OUT) + '  (' + kb + ' KB)'
                + (noted ? '   발표자 노트 ' + noted + '장' : ''));
  });
}
main();
