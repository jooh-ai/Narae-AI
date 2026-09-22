#!/usr/bin/env python3
"""생성된 pptx 의 기하 검증 — 이 환경에서는 pptx 를 이미지로 렌더할 수 없으므로
눈으로 보는 대신 좌표로 확인한다 (계획서 §8 ⑤).

  python3 docs/ppt/build/verify.py

검사 4종
  ① 경계 이탈   모든 도형의 x+w, y+h 가 1280×720 안인가
  ② 여백 침범   글자·도형이 외곽여백(좌우 72 / 상 44 / 하 686) 안인가
  ③ 글자 넘침   한글 자막폭을 넉넉하게(보수적으로) 추정해 필요 높이 vs 박스 높이
  ④ 상호 겹침   글자 박스끼리 겹치는가 (배경 도형은 의도된 것이라 제외)

③ 은 한글 1.0em · 영문 0.55em + 8% 안전 여유로 잡는다. 넉넉하게 추정하므로
통과하면 실제 맑은 고딕에서는 여유가 남는다. 최종 확인은 발표자 PC 에서 한 번.
"""
import sys, zipfile, math, re
import xml.etree.ElementTree as ET

A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
P = '{http://schemas.openxmlformats.org/presentationml/2006/main}'
EMU = 9525.0                      # 1 px @96dpi
W, H = 1280, 720
MARGIN = (72, 44, 1208, 686)      # left, top, right, bottom
SAFE = 1.08                       # 자막폭 안전 여유

def px(v): return float(v) / EMU

def text_width(s, size_px):
    w = 0.0
    for ch in s:
        w += size_px * (1.0 if ord(ch) > 0x2000 else 0.55)
    return w * SAFE

def shapes(slide_xml):
    root = ET.fromstring(slide_xml)
    out = []
    for sp in root.iter():
        if sp.tag not in (P + 'sp', P + 'pic'):
            continue
        off = sp.find('.//' + A + 'off'); ext = sp.find('.//' + A + 'ext')
        if off is None or ext is None:
            continue
        x, y = px(off.get('x')), px(off.get('y'))
        w, h = px(ext.get('cx')), px(ext.get('cy'))
        paras = []
        for p in sp.iter(A + 'p'):
            sz = None; ls = None
            for rpr in p.iter(A + 'rPr'):
                if rpr.get('sz'): sz = int(rpr.get('sz')) / 100.0; break
            sp_pts = p.find('.//' + A + 'lnSpc/' + A + 'spcPts')
            if sp_pts is not None: ls = int(sp_pts.get('val')) / 100.0
            # <a:br/> 는 강제 줄바꿈이다 — 한 문단이어도 줄을 갈라 센다
            seg = ['']
            for ch in list(p):
                if ch.tag == A + 'br':
                    seg.append('')
                elif ch.tag == A + 'r':
                    seg[-1] += ''.join(t.text or '' for t in ch.iter(A + 't'))
            for t in seg:
                if t.strip(): paras.append((t, sz, ls))
        out.append(dict(x=x, y=y, w=w, h=h, paras=paras,
                        txt=' '.join(p[0] for p in paras)))
    return out

def check(path):
    z = zipfile.ZipFile(path)
    names = sorted((n for n in z.namelist()
                    if re.match(r'ppt/slides/slide\d+\.xml$', n)),
                   key=lambda n: int(re.search(r'(\d+)', n.split('/')[-1]).group(1)))
    fails = []
    for i, n in enumerate(names, 1):
        sh = shapes(z.read(n))
        for s in sh:
            r, b = s['x'] + s['w'], s['y'] + s['h']
            tag = (s['txt'][:26] or '(도형)')
            if s['x'] < -0.5 or s['y'] < -0.5 or r > W + 0.5 or b > H + 0.5:
                fails.append(('①경계', i, tag,
                              'x %.0f y %.0f → %.0f, %.0f' % (s['x'], s['y'], r, b)))
            if s['paras']:
                if s['x'] < MARGIN[0] - 0.5 or s['y'] < MARGIN[1] - 0.5 \
                   or r > MARGIN[2] + 0.5 or b > MARGIN[3] + 0.5:
                    fails.append(('②여백', i, tag,
                                  'x %.0f y %.0f → %.0f, %.0f' % (s['x'], s['y'], r, b)))
                need = 0.0
                for t, sz, ls in s['paras']:
                    sz_px = (sz or 11) / 0.75
                    lh = (ls / 0.75) if ls else sz_px * 1.4
                    lines = max(1, math.ceil(text_width(t, sz_px) / max(s['w'], 1)))
                    need += lines * lh
                if need > s['h'] + 1.5:
                    fails.append(('③넘침', i, tag,
                                  '필요 %.0f > 박스 %.0f px' % (need, s['h'])))
        tb = [s for s in sh if s['paras']]
        for a in range(len(tb)):
            for b2 in range(a + 1, len(tb)):
                p, q = tb[a], tb[b2]
                ox = min(p['x'] + p['w'], q['x'] + q['w']) - max(p['x'], q['x'])
                oy = min(p['y'] + p['h'], q['y'] + q['h']) - max(p['y'], q['y'])
                if ox > 1.5 and oy > 1.5:
                    fails.append(('④겹침', i, p['txt'][:18] + ' ↔ ' + q['txt'][:18],
                                  '%.0f × %.0f px' % (ox, oy)))
    return len(names), fails

if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else 'docs/ppt/위례_공급가능용량_최종발표.pptx'
    n, fails = check(path)
    print('검증  %d 장' % n)
    if not fails:
        print('통과  경계 이탈 0 · 여백 침범 0 · 글자 넘침 0 · 상호 겹침 0')
        sys.exit(0)
    by = {}
    for k, s, t, d in fails: by.setdefault(k, []).append((s, t, d))
    for k in sorted(by):
        print('\n%s  %d건' % (k, len(by[k])))
        for s, t, d in by[k][:40]:
            print('  슬라이드 %-2d  %-30s  %s' % (s, t, d))
        if len(by[k]) > 40: print('  … 외 %d건' % (len(by[k]) - 40))
    sys.exit(1)
