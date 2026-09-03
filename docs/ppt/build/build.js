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
const T = require('./theme.js');

const DIR = __dirname;
/* --v2 : 컴팩트판(13장). 기존 18장 판은 인자 없이 그대로 만든다. */
const V2 = process.argv.includes('--v2');
const SLIDE_DIR = path.join(DIR, V2 ? 'slides_v2' : 'slides');
const STATE_PATH = path.join(DIR, V2 ? 'BUILD_STATE_V2.json' : 'BUILD_STATE.json');
const OUT = path.join(DIR, '..', V2 ? '위례_공급가능용량_최종발표_v2.pptx'
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

function main() {
  const listOnly = process.argv.includes('--list');
  const pptx = new pptxgen();
  pptx.defineLayout({ name: 'W169', width: 13.333, height: 7.5 });
  pptx.layout = 'W169';
  pptx.title = '공급가능용량 산정 Tool — 최종 발표';
  pptx.subject = '위례열병합발전소 공급가능용량 산정 체계 개선';
  pptx.company = '나래에너지서비스';
  pptx.author = state.meta.authors.join(', ');

  let done = 0, todo = [];
  for (const it of state.slides) {
    const f = path.join(SLIDE_DIR, it.file);
    const exists = fs.existsSync(f);
    it.status = exists ? 'done' : 'todo';
    if (exists) { done++; } else { todo.push(it.no); }
    if (!listOnly) {
      if (exists) require(f)(pptx, T, state.meta, DATA);
      else placeholder(pptx, it);
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
    console.log('출력  ' + path.relative(process.cwd(), OUT) + '  (' + kb + ' KB)');
  });
}
main();
