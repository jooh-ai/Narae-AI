/* index.html 의 규칙 엔진에서 사용 가능한 근무 조합을 전부 뽑아 JSON 으로 출력한다.
   엑셀 드롭다운 목록의 원천이며, 이렇게 해야 엑셀과 HTML 이 같은 규칙을 쓴다.
       node worktime/gen_combos.js > worktime/data/combos.json          */
const fs = require('fs'), path = require('path');
const html = fs.readFileSync(path.join(__dirname, 'index.html'), 'utf8');
const body = html.split('\n<script>\n')[1].split('\n</script>\n')[0];
const upto = body.indexOf('/* 휴가 블록 표기');
const engine = body.slice(0, upto)
  + 'function coversRange(segs,a,b){const l=segs.slice().sort((x,y)=>x[0]-y[0]);'
  + 'let c=a;for(const[s,e]of l){if(s>c)return false;if(e>c)c=e;if(c>=b)return true;}return c>=b;}'
  + '\nmodule.exports={evalDay,TYPES,toMin,toStr,fmtH,DEFAULTS,dinnerWin};';
const m = { exports: {} };
new Function('module', 'exports', engine)(m, m.exports);
const { evalDay, toMin, toStr, DEFAULTS: C } = m.exports;

const grid = [];
for (let t = 6 * 60; t <= 22 * 60; t += C.unit) grid.push(toStr(t));

const hm = h => (Math.round(h * 100) / 100);
const tag = t => t.replace(':', '');
const out = [];

/* 시각이 필요 없는 유형 */
[['ANNUAL', '연차'], ['TRIP', '출장'], ['EDU', '교육'], ['OTHER', '기타'],
 ['ONLEAVE', '휴직']].forEach(([type, code]) => {
  const ev = evalDay({ type }, C, { isWorkday: true });
  out.push({ code, type, label: code, start: '', end: '',
             work: hm(ev.work), leave: hm(ev.leave), meets8: ev.counts8h ? 1 : 0,
             block: '', group: '휴가·사외' });
});

/* 시각이 필요한 유형 — 격자 전체를 돌려 규칙을 통과하는 조합만 */
const KIND = [
  ['WORK',    '근무',     '근무'],
  ['HALF_AM', '오전반',   '반차'],
  ['HALF_PM', '오후반',   '반차'],
  ['Q_AM',    '오전반반', '반반차'],
  ['Q_PM',    '오후반반', '반반차'],
  ['CHECKUP', '검진',     '건강검진'],
];
for (const [type, prefix, group] of KIND) {
  for (const a of grid) for (const b of grid) {
    if (toMin(b) <= toMin(a)) continue;
    const ev = evalDay({ type, start: a, end: b }, C, { isWorkday: true });
    if (ev.viol.length) continue;
    out.push({
      code: `${prefix} ${tag(a)}-${tag(b)}`, type, label: prefix, start: a, end: b,
      work: hm(ev.work), leave: hm(ev.leave), meets8: ev.counts8h ? 1 : 0,
      block: ev.block ? `${toStr(ev.block[0])}~${toStr(ev.block[1])}` : '',
      group,
    });
  }
}

/* 실사용 빈도 순 — 정확히 8시간인 근무를 맨 앞에, 선택근로 나머지를 맨 뒤에 */
const rank = r => {
  if (r.type === 'WORK' && r.work === C.fullDay) return 0;
  if (r.group === '휴가·사외') return r.code === '휴직' ? 9 : 1;
  if (r.group === '반차') return 2;
  if (r.group === '반반차') return 3;
  if (r.group === '건강검진') return 4;
  return 5;
};
out.sort((x, y) => rank(x) - rank(y) || x.start.localeCompare(y.start)
                   || x.end.localeCompare(y.end));
process.stdout.write(JSON.stringify(out, null, 1));
