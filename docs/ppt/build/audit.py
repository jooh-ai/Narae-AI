#!/usr/bin/env python3
"""장표 전면 감사 — verify.py 가 못 잡는 것을 잡는다.

    python3 docs/ppt/build/audit.py docs/ppt/위례_공급가능용량_최종발표_v3.pptx

`verify.py` 는 경계·여백·넘침·겹침 네 가지를 본다. 그것으로 통과해도 남는
결함이 있다. 2026-09-18 전면 검토에서 실제로 나온 것들이다.

  ① 구획 밖으로 삐져나온 글자
      구획(테두리 상자) 안에서 시작했는데 아래로 빠져나온 글자. 겹치지도
      넘치지도 않으므로 verify 는 통과시킨다. 화면에서는 글자가 상자 선을
      타고 앉은 것으로 보인다 — 일곱 군데 나왔다.
  ② 왼쪽 정렬이 1~6px 만 어긋난 짝
      완전히 어긋나면 눈에 보여서 고치는데, 2px 는 "뭔가 안 맞는다" 는
      느낌만 남긴다. 다른 계층(구획 라벨 vs 본문)끼리는 어긋나도 되므로
      사람이 판단할 목록으로만 뽑는다.
  ③ 부호 문자 혼용
      −(U+2212) 과 ASCII 하이픈을 섞어 쓰면 숫자 열의 마이너스가 들쭉날쭉
      해진다. 장표에서는 −(U+2212) 로 통일한다.
  ④ 두 장 이상에 똑같이 나오는 구절
      표지·마무리 상용구는 정상이고, 본문에 같은 문장이 두 번 나오면 한
      쪽을 줄여야 한다.
  ⑤ 한 장에 39 와 40 이 함께 나오는지
      채점 회차(39)와 누적 회차(40)다. 근거 문장 없이 둘이 같이 있으면
      반드시 질문받는다.

verify.py 는 '틀린 것', audit.py 는 '설명이 필요한 것' 을 뽑는다.
"""
import sys, zipfile, re, collections
import xml.etree.ElementTree as ET

A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
P = '{http://schemas.openxmlformats.org/presentationml/2006/main}'
EMU = 9525.0


def load(path):
    z = zipfile.ZipFile(path)
    names = sorted((n for n in z.namelist()
                    if re.match(r'ppt/slides/slide\d+\.xml$', n)),
                   key=lambda n: int(re.search(r'(\d+)', n.split('/')[-1]).group(1)))
    out = {}
    for i, n in enumerate(names, 1):
        root = ET.fromstring(z.read(n))
        sh = []
        for sp in root.iter():
            if sp.tag not in (P + 'sp', P + 'pic'):
                continue
            off, ext = sp.find('.//' + A + 'off'), sp.find('.//' + A + 'ext')
            if off is None or ext is None:
                continue
            txt = ''.join(t.text or '' for t in sp.iter(A + 't'))
            prst = sp.find('.//' + A + 'prstGeom')
            pPr = sp.find('.//' + A + 'pPr')
            sh.append(dict(x=round(float(off.get('x')) / EMU, 1),
                           y=round(float(off.get('y')) / EMU, 1),
                           w=round(float(ext.get('cx')) / EMU, 1),
                           h=round(float(ext.get('cy')) / EMU, 1),
                           txt=txt.strip(),
                           pic=(sp.tag == P + 'pic'),
                           geom=(prst.get('prst') if prst is not None else ''),
                           algn=(pPr.get('algn') if pPr is not None else None)))
        out[i] = sh
    return out


def main(path):
    S = load(path)
    bad = 0

    print('① 구획 밖으로 삐져나온 글자')
    n = 0
    for i, sh in S.items():
        boxes = [s for s in sh if not s['pic'] and not s['txt']
                 and s['geom'] == 'rect' and s['w'] > 300 and s['h'] > 60]
        items = [s for s in sh if s['txt'] or s['pic']]
        for bx in boxes:
            for t in items:
                if not (bx['x'] - 2 <= t['x'] and t['x'] + t['w'] <= bx['x'] + bx['w'] + 2):
                    continue
                if not (bx['y'] - 2 <= t['y'] <= bx['y'] + bx['h']):
                    continue
                over = t['y'] + t['h'] - (bx['y'] + bx['h'])
                if over > 1.5:
                    n += 1
                    print('   %2d  %-28s  %.1fpx' % (i, (t['txt'][:26] or '(그림)'), over))
    print('   ' + ('없음' if not n else '%d건' % n)); bad += n

    print('\n② 부호 문자 혼용 (− U+2212 로 통일)')
    n = 0
    for i, sh in S.items():
        for s in sh:
            if re.search(r'(?<![\w])-\s?\d', s['txt']):
                n += 1; print('   %2d  %r' % (i, s['txt'][:60]))
    print('   ' + ('없음' if not n else '%d건' % n)); bad += n

    print('\n③ 두 장 이상에 똑같이 나오는 구절 (표지·마무리 상용구는 정상)')
    seg = collections.defaultdict(set)
    for i, sh in S.items():
        for s in sh:
            for t in re.split(r'[.·—]\s*', s['txt']):
                t = t.strip()
                if len(t) >= 12:
                    seg[t].add(i)
    for t, pages in sorted(seg.items(), key=lambda kv: -len(kv[1])):
        if len(pages) > 1:
            print('   %-58s %s' % (t[:58], sorted(pages)))

    print('\n④ 한 장에 39·40 이 함께 (근거 문장이 있어야 한다)')
    for i, sh in S.items():
        j = ' '.join(s['txt'] for s in sh)
        if '39' in j and '40' in j:
            ok = any(k in j for k in ('빠집니다', '못 냅니다', '까닭', '뺐습니다'))
            print('   %2d  근거 %s' % (i, '있음' if ok else '없음  ← 확인'))
            if not ok: bad += 1

    print('\n⑤ 왼쪽 정렬이 1~6px 만 어긋난 짝 (사람이 판단할 목록)')
    for i, sh in S.items():
        xs = collections.defaultdict(list)
        for s in sh:
            if s['txt'] and s['algn'] not in ('r', 'ctr'):
                xs[s['x']].append(s['txt'][:18])
        k = sorted(xs)
        for a, b in zip(k, k[1:]):
            if 0.5 < b - a <= 6:
                print('   %2d  %g ↔ %g (%.0fpx)  %s | %s' % (i, a, b, b - a, xs[a][0], xs[b][0]))

    print('\n──── 고칠 것 %d건 ────' % bad)
    return 1 if bad else 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1
                          else 'docs/ppt/위례_공급가능용량_최종발표_v3.pptx'))
