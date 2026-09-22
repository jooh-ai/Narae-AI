/* 회귀 개념 장표용 그림 도우미 — 부록 두 장이 같이 쓴다.

   교과서 그림 하나를 그리는 데 필요한 것만 담았다. 축·격자·띠·곡선·점.
   장표 본편의 차트들과 달리 단위가 없는 예시이므로 눈금 숫자도 없다 —
   x 와 y 라고만 적고 모양에 집중하게 한다.                              */
'use strict';

/* o = {
     x0,x1,y0,y1   자(축) 범위
     band          {lo:[], hi:[], color}        평균±2σ 같은 띠
     lines         [{v:[], color, w, dash}]     곡선들
     dots          [[x,y], ...]                 관측점
     zero          true 면 y=0 에 실선
     label         왼쪽 위에 붙는 작은 말
   }                                                                    */
module.exports = function plot(d, T, X, Y, W, H, xs, o) {
  const { C, LW } = T;
  const px = t => X + 8 + (t - o.x0) / (o.x1 - o.x0) * (W - 16);
  const py = v => Y + H - 10 - (v - o.y0) / (o.y1 - o.y0) * (H - 20);
  const clip = v => Math.max(o.y0, Math.min(o.y1, v));
  d.box(X, Y, W, H, C.groove, C.rule2, 1);
  if (o.zero !== false) d.hline(px(o.x0), py(0), px(o.x1) - px(o.x0), C.rule2, 1);

  if (o.band) {
    for (const side of ['lo', 'hi'])
      for (let i = 0; i < xs.length - 1; i++)
        d.seg(px(xs[i]), py(clip(o.band[side][i])),
              px(xs[i + 1]), py(clip(o.band[side][i + 1])),
              o.band.color || C.brassD, 1, 'dash');
    /* 면은 얇은 가로선을 촘촘히 그어 채운다 — 도형 채우기를 쓰면 점이 묻힌다 */
    for (let i = 0; i < xs.length - 1; i += 1) {
      const a = py(clip(o.band.hi[i])), b = py(clip(o.band.lo[i]));
      if (b - a > 0.5) d.rect(px(xs[i]), a, px(xs[i + 1]) - px(xs[i]) + 0.6,
                              b - a, o.band.fill || C.brassS);
    }
  }
  (o.lines || []).forEach(L => {
    for (let i = 0; i < xs.length - 1; i++) {
      if (L.v[i] == null || L.v[i + 1] == null) continue;
      d.seg(px(xs[i]), py(clip(L.v[i])), px(xs[i + 1]), py(clip(L.v[i + 1])),
            L.color, L.w || 1, L.dash);
    }
  });
  (o.dots || []).forEach(([a, b]) => d.dot(px(a), py(clip(b)), 2.4, C.ink));
  if (o.label) d.text(o.label, { x: X + 8, y: Y + 5, w: W - 16, px: 10,
                                 lh: 1.2, color: C.dim2 });
  return { px, py };
};
