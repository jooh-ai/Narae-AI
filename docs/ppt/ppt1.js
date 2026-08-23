// PPT-1 : 공급가능용량 자동산정 Tool 개발 보고 (4장)
// SK 브랜드 — 레드 EA002C / 오렌지 F47725
//
// 3장의 산점도는 누적 DB 씨앗을 직접 읽는다 — 시험이 쌓여 씨앗이 갱신되면
// 이 스크립트를 다시 돌리기만 하면 그림도 따라 바뀐다.
// 3장의 비교 수치는 tool/scripts/method_compare.py 출력이다.
const pptx = require("pptxgenjs");
const SEED = require("../../tool/wirye_capacity/data/measurements_seed.json");
const p = new pptx();
p.layout = "LAYOUT_WIDE";              // 13.3 x 7.5 in
p.author = "발전운영팀";
p.title = "공급가능용량 자동산정 Tool";

const RED = "EA002C", ORG = "F47725", INK = "1F1A18", GRAY = "6B625E";
const LINE = "E8E0DC", BG = "FFFFFF", TINT = "FFF4EE", HINT = "9A908C";
const F = "맑은 고딕";
const DIR = __dirname + "/";   // 이 스크립트와 같은 폴더의 s_*.png / 출력 pptx

// ── 머리글 : 번호 + 제목(좌) + 소속·담당자(우) ──
function head(s, no, title) {
  s.addShape(p.ShapeType.rect, { x: 0, y: 0, w: 13.33, h: 1.0, fill: { color: INK } });
  s.addText(String(no).padStart(2, "0"), {
    x: 0.45, y: 0.2, w: 0.7, h: 0.6, fontFace: F, fontSize: 26, bold: true,
    color: ORG, margin: 0, valign: "middle",
  });
  s.addText(title, {
    x: 1.15, y: 0.2, w: 7.4, h: 0.6, fontFace: F, fontSize: 23, bold: true,
    color: "FFFFFF", margin: 0, valign: "middle",
  });
  s.addText("소속 : 발전운영팀", {
    x: 8.7, y: 0.17, w: 4.2, h: 0.32, fontFace: F, fontSize: 12,
    color: "C9BFBB", align: "right", margin: 0, valign: "middle",
  });
  s.addText("담당자 : ○○○  ·  2026. 8월", {
    x: 8.7, y: 0.5, w: 4.2, h: 0.32, fontFace: F, fontSize: 12, bold: true,
    color: "FFFFFF", align: "right", margin: 0, valign: "middle",
  });
}
function card(s, x, y, w, h, fill) {
  s.addShape(p.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.06, fill: { color: fill || "FFFFFF" },
    line: { color: LINE, width: 1 },
    shadow: { type: "outer", angle: 90, blur: 8, offset: 1, color: "D8CFCA", opacity: 0.5 },
  });
}
function secTitle(s, x, y, text, color, hint) {
  s.addShape(p.ShapeType.ellipse, { x, y: y + 0.05, w: 0.26, h: 0.26, fill: { color: color || RED } });
  s.addText(text, {
    x: x + 0.4, y, w: 5.0, h: 0.34, fontFace: F, fontSize: 13.5, bold: true,
    color: INK, margin: 0, valign: "middle",
  });
  if (hint) s.addText(hint, {
    x: x + 5.5, y, w: 6.7, h: 0.34, fontFace: F, fontSize: 10,
    color: HINT, align: "right", margin: 0, valign: "middle",
  });
}
// 큰 숫자 + 라벨 (수치 강조)
function stat(s, x, y, w, value, unit, label, color) {
  s.addText([
    { text: value, options: { fontSize: 21, bold: true, color: color || INK } },
    { text: unit ? " " + unit : "", options: { fontSize: 11.5, bold: true, color: color || INK } },
  ], { x, y, w, h: 0.38, fontFace: F, margin: 0, valign: "bottom" });
  s.addText(label, {
    x, y: y + 0.38, w, h: 0.44, fontFace: F, fontSize: 9.5, color: GRAY,
    margin: 0, lineSpacing: 12,
  });
}

/* ══════════════ 1장 : 왜 만들었나 ══════════════ */
{
  const s = p.addSlide();
  s.background = { color: BG };
  head(s, 1, "왜 만들었나");

  // 상황 3단계
  const steps = [
    ["매일 신고합니다", "내일 우리 발전소가 낼 수 있는\n전기량을 전력거래소에 신고", RED],
    ["온도가 변수입니다", "같은 발전소라도 기온에 따라\n출력이 376~472 MW 로 변동", ORG],
    ["정확도가 곧 돈입니다", "허용범위 ±0.5% (약 ±2 MW)\n적게 신고 → 손해 / 못 지키면 → 페널티", "8A7F7A"],
  ];
  steps.forEach(([t, d, c], i) => {
    const x = 0.55 + i * 4.24;
    card(s, x, 1.28, 3.9, 1.66);
    s.addShape(p.ShapeType.ellipse, { x: x + 0.28, y: 1.52, w: 0.4, h: 0.4, fill: { color: c } });
    s.addText(String(i + 1), {
      x: x + 0.28, y: 1.52, w: 0.4, h: 0.4, fontFace: F, fontSize: 14, bold: true,
      color: "FFFFFF", align: "center", valign: "middle", margin: 0,
    });
    s.addText(t, {
      x: x + 0.82, y: 1.49, w: 2.85, h: 0.4, fontFace: F, fontSize: 14.5, bold: true,
      color: INK, margin: 0, valign: "middle",
    });
    s.addText(d, {
      x: x + 0.28, y: 2.0, w: 3.4, h: 0.8, fontFace: F, fontSize: 11,
      color: GRAY, margin: 0, lineSpacing: 15,
    });
  });

  // Before / After
  s.addText("지금까지는 이렇게 했습니다", {
    x: 0.55, y: 3.14, w: 5.9, h: 0.32, fontFace: F, fontSize: 13.5, bold: true,
    color: GRAY, margin: 0,
  });
  card(s, 0.55, 3.52, 5.9, 2.3, "F7F4F2");
  s.addText([
    { text: "엑셀 4개를 오가며 담당자가 직접 계산", options: { bullet: true, breakLine: true } },
    { text: "시험 결과를 손으로 옮겨 적고 평균 산출", options: { bullet: true, breakLine: true } },
    { text: "온도 61개 구간 값을 매번 수작업 입력", options: { bullet: true, breakLine: true } },
    { text: "사람이 하는 일이라 실수 가능성 존재", options: { bullet: true } },
  ], {
    x: 0.9, y: 3.78, w: 5.25, h: 1.5, fontFace: F, fontSize: 12.5, color: INK,
    paraSpaceAfter: 7, margin: 0,
  });
  s.addText("＂엑셀 4개 · 수작업 · 반복＂", {
    x: 0.9, y: 5.36, w: 5.25, h: 0.34, fontFace: F, fontSize: 12.5, italic: true,
    color: GRAY, margin: 0,
  });

  s.addText("그래서 이렇게 바꿨습니다", {
    x: 6.88, y: 3.14, w: 5.9, h: 0.32, fontFace: F, fontSize: 13.5, bold: true,
    color: RED, margin: 0,
  });
  card(s, 6.88, 3.52, 5.9, 2.3, TINT);
  s.addText([
    { text: "날짜만 입력하면 발전소 데이터 자동 취득", options: { bullet: true, breakLine: true } },
    { text: "계산·보정·검증을 프로그램이 일괄 처리", options: { bullet: true, breakLine: true } },
    { text: "온도 61개 구간 신고파일까지 자동 생성", options: { bullet: true, breakLine: true } },
    { text: "기존 엑셀과 동일 계산 확인 (오차 0.19 MW)", options: { bullet: true } },
  ], {
    x: 7.23, y: 3.78, w: 5.25, h: 1.5, fontFace: F, fontSize: 12.5, color: INK,
    paraSpaceAfter: 7, margin: 0,
  });
  s.addText("＂날짜 입력 → 클릭 한 번＂", {
    x: 7.23, y: 5.36, w: 5.25, h: 0.34, fontFace: F, fontSize: 12.5, italic: true, bold: true,
    color: RED, margin: 0,
  });

  // 하단 수치 5칸
  card(s, 0.55, 6.06, 12.23, 1.18);
  const kpi = [
    ["31", "건", "축적된 시험 결과\n(−1.9 ~ 36.1°C)", RED],
    ["0.19", "MW", "기존 엑셀 대비\n최대 계산 오차", INK],
    ["1.33", "MW", "예측 오차\n(일괄 3.63 → 2.7배 개선)", RED],
    ["61", "개", "자동 산출 온도 구간\n(−20 ~ 40°C)", INK],
    ["±0.5", "%", "입찰 허용범위\n(약 ±2 MW)", "8A7F7A"],
  ];
  kpi.forEach(([v, u, l, c], i) => stat(s, 0.95 + i * 2.4, 6.24, 2.25, v, u, l, c));

  s.addNotes("전력 판매를 위해 매일 '내일 낼 수 있는 전기량'을 신고합니다. 기온에 따라 출력이 376~472MW로 "
    + "크게 달라지고, 허용범위가 ±0.5%(약 ±2MW)라 정확도가 중요합니다. 기존에는 엑셀 4개를 오가며 "
    + "손으로 계산했는데 이를 자동화했고, 기존 엑셀과 계산이 동일함을 오차 0.19MW로 확인했습니다.");
}

/* ══════════════ 2장 : 무엇을 만들었나 (화면 5개 정사각형) ══════════════ */
{
  const s = p.addSlide();
  s.background = { color: BG };
  head(s, 2, "무엇을 만들었나");

  secTitle(s, 0.55, 1.12, "화면 5개짜리 Windows 프로그램", RED,
    "날짜 입력 → 자동 취득 → 보정 계산 → 신고파일 생성");

  // 5개 화면 — 정사각형 카드 가로 배치
  const shots = [
    ["s_run.png", "공급가능용량 산정", "날짜만 입력하면\n신고파일까지 자동 생성", RED],
    ["s_status.png", "온도별 보정값 현황", "구간별 시험 건수를\n신호등으로 표시", RED],
    ["s_list.png", "시험 결과 목록", "누적 31건 관리\n(날짜·온도·측정값)", RED],
    ["s_sim.png", "출력 시뮬레이션", "조건 입력 → 예상 출력\n시험 후 즉시 대조", ORG],
    ["s_chart.png", "출력곡선 비교", "이론값 vs 보정 후\n그래프로 확인", ORG],
  ];
  const W = 2.27, GAP = 0.22, X0 = 0.55, CY = 1.56, IMG = 2.03;
  shots.forEach(([f, t, d, c], i) => {
    const x = X0 + i * (W + GAP);
    card(s, x, CY, W, 2.52, "FBF9F8");
    s.addShape(p.ShapeType.roundRect, {          // 정사각형 이미지 영역
      x: x + 0.12, y: CY + 0.12, w: IMG, h: IMG, rectRadius: 0.03,
      fill: { color: "FFFFFF" }, line: { color: LINE, width: 1 },
    });
    s.addImage({                                  // 비율 유지하며 정사각형 안에 맞춤
      path: DIR + f, x: x + 0.12, y: CY + 0.12, w: IMG, h: IMG,
      sizing: { type: "contain", w: IMG, h: IMG },
    });
    s.addShape(p.ShapeType.ellipse, {
      x: x + 0.12, y: CY + 2.2, w: 0.24, h: 0.24, fill: { color: c },
    });
    s.addText(String(i + 1), {
      x: x + 0.12, y: CY + 2.2, w: 0.24, h: 0.24, fontFace: F, fontSize: 10, bold: true,
      color: "FFFFFF", align: "center", valign: "middle", margin: 0,
    });
    s.addText(t, {
      x: x + 0.42, y: CY + 2.18, w: 1.78, h: 0.28, fontFace: F, fontSize: 11, bold: true,
      color: INK, margin: 0, valign: "middle",
    });
    s.addText(d, {
      x, y: CY + 2.6, w: W, h: 0.56, fontFace: F, fontSize: 9.5, color: GRAY,
      align: "center", margin: 0, lineSpacing: 12,
    });
  });

  // 계산 방식 (좌) + 검증 체계 (우)
  secTitle(s, 0.55, 4.82, "계산 방식 — 2단 구조", ORG);
  card(s, 0.55, 5.24, 5.9, 2.0, TINT);
  s.addText([
    { text: "1단  이론값", options: { fontSize: 12, bold: true, color: RED, breakLine: true } },
    { text: "설계 성능곡선으로 계산 (기존 엑셀과 동일)", options: { fontSize: 11, color: GRAY, breakLine: true } },
    { text: "", options: { fontSize: 5, breakLine: true } },
    { text: "2단  보정값", options: { fontSize: 12, bold: true, color: RED, breakLine: true } },
    { text: "실제 시험 31건에서 배운 차이를 반영", options: { fontSize: 11, color: GRAY, breakLine: true } },
    { text: "", options: { fontSize: 5, breakLine: true } },
    { text: "신고값 = 이론값 + 보정값", options: { fontSize: 12.5, bold: true, color: INK } },
  ], { x: 0.9, y: 5.44, w: 5.25, h: 1.64, fontFace: F, margin: 0, lineSpacing: 15 });

  secTitle(s, 6.88, 4.82, "정확도 · 검증", "8A7F7A");
  card(s, 6.88, 5.24, 5.9, 2.0);
  const rows = [
    ["기존 엑셀과 계산 일치", "최대 오차 0.19 MW", RED],
    ["예측 오차 (일괄 보정 → 온도별 곡선)", "3.63 → 1.33 MW", RED],
    ["데이터 취득값 일치 확인", "24.85262 = 24.8526", INK],
    ["계산 검증 항목 자동 점검", "186개 / 수정 시마다", INK],
  ];
  rows.forEach(([k, v, c], i) => {
    const y = 5.44 + i * 0.38;
    s.addText(k, {
      x: 7.2, y, w: 3.5, h: 0.32, fontFace: F, fontSize: 10.5, color: GRAY,
      margin: 0, valign: "middle",
    });
    s.addText(v, {
      x: 10.7, y, w: 1.85, h: 0.32, fontFace: F, fontSize: 11, bold: true, color: c,
      align: "right", margin: 0, valign: "middle",
    });
  });
  s.addText("※ 계산식이 바뀌면 186개 항목을 자동으로 다시 검사 — 오류를 사전에 차단", {
    x: 7.2, y: 6.94, w: 5.35, h: 0.26, fontFace: F, fontSize: 9,
    color: HINT, margin: 0,
  });

  s.addNotes("화면 5개로 구성했습니다. 계산은 2단 구조입니다 — 1단은 설계 성능곡선(기존 엑셀과 동일), "
    + "2단은 실제 시험 31건에서 배운 보정값입니다. '186개 자동 점검'은 계산식을 수정할 때마다 "
    + "프로그램이 스스로 186가지 항목을 다시 검사해 계산 오류를 사전에 막는 장치입니다.");
}

/* ══════════════ 3장 : 얼마나 정확해졌나 (일괄 보정 → 온도별 곡선) ══════════════ */
{
  const s = p.addSlide();
  s.background = { color: BG };
  head(s, 3, "얼마나 정확해졌나");

  secTitle(s, 0.55, 1.12, "종전에는 온도와 무관한 보정값 하나였습니다", RED,
    "이론값과 실제값의 차이를 평균해 전 온도에 같은 값을 적용 — '일괄 보정값'");

  /* ── 좌 : 보정값은 온도에 따라 크게 변한다 (실측 31건 산점도) ── */
  card(s, 0.55, 1.56, 6.1, 2.8);
  const PX = 1.34, PY = 1.94, PW = 5.06, PH = 1.72;      // 그림 영역
  const T0 = -5, T1 = 39.5, C0 = -5.5, C1 = 14.5;
  const tx = t => PX + ((t - T0) / (T1 - T0)) * PW;
  const cy = c => PY + ((C1 - c) / (C1 - C0)) * PH;

  s.addText("보정값 (MW)", {
    x: 0.68, y: 1.66, w: 2.2, h: 0.22, fontFace: F, fontSize: 8.5, bold: true,
    color: GRAY, margin: 0,
  });
  [-4, 0, 4, 8, 12].forEach(v => {                       // 가로 격자 + y 라벨
    s.addShape(p.ShapeType.line, {
      x: PX, y: cy(v), w: PW, h: 0,
      line: { color: v === 0 ? "DCD2CC" : "F1EBE7", width: 1 },
    });
    s.addText(v > 0 ? "+" + v : String(v), {
      x: PX - 0.56, y: cy(v) - 0.11, w: 0.5, h: 0.22, fontFace: F, fontSize: 8,
      color: HINT, align: "right", margin: 0, valign: "middle",
    });
  });
  [0, 10, 20, 30].forEach(v => s.addText(v + "°C", {     // x 라벨
    x: tx(v) - 0.3, y: PY + PH + 0.05, w: 0.6, h: 0.2, fontFace: F, fontSize: 8,
    color: HINT, align: "center", margin: 0,
  }));

  // 일괄 보정값 = 전체 평균. 온도와 무관하므로 수평선 하나다.
  const MEAN = SEED.reduce((a, r) => a + r.corr, 0) / SEED.length;
  s.addShape(p.ShapeType.line, {
    x: PX, y: cy(MEAN), w: PW, h: 0,
    line: { color: "6B625E", width: 1.75, dashType: "dash" },
  });
  // 라벨은 오른쪽 위 — 고온 구간은 전부 선 아래에 있어 그 위가 비어 있다
  s.addText("종전 : 일괄 보정값 +" + MEAN.toFixed(1) + " MW (온도 무관)", {
    x: PX + PW - 2.9, y: cy(MEAN) - 0.24, w: 2.9, h: 0.2, fontFace: F, fontSize: 8,
    bold: true, color: "6B625E", align: "right", margin: 0,
  });

  // 실측 31건 — 겨울(빨강) → 여름(주황)
  SEED.forEach(r => {
    s.addShape(p.ShapeType.ellipse, {
      x: tx(r.cit) - 0.055, y: cy(r.corr) - 0.055, w: 0.11, h: 0.11,
      fill: { color: r.cit < 10 ? RED : r.cit < 22 ? "F0431F" : ORG },
      line: { color: "FFFFFF", width: 0.75 },
    });
  });

  // 양 끝에서 얼마나 어긋나는지 — 세로선만 긋는다. 점이 촘촘해 값 라벨을
  // 그림 안에 두면 어디에 놓아도 점과 겹친다. 수치는 아래 범례에 적는다.
  const cold = SEED.reduce((a, r) => (r.corr > a.corr ? r : a));
  const hot = SEED.reduce((a, r) => (r.corr < a.corr ? r : a));
  [cold, hot].forEach(r => s.addShape(p.ShapeType.line, {
    x: tx(r.cit), y: Math.min(cy(r.corr), cy(MEAN)), w: 0,
    h: Math.abs(cy(r.corr) - cy(MEAN)), line: { color: INK, width: 1.25 },
  }));
  const lo = Math.min(...SEED.map(r => r.corr)), hi = Math.max(...SEED.map(r => r.corr));
  s.addText([
    { text: "실측 " + SEED.length + "건 — 보정값이 " + lo.toFixed(1) + " ~ +" + hi.toFixed(1)
        + " MW (폭 " + (hi - lo).toFixed(1) + " MW) 로 변합니다. ",
      options: { color: GRAY } },
    { text: "수평선 하나로는 양 끝을 동시에 맞출 수 없습니다.",
      options: { color: INK, bold: true } },
    { text: "\n세로선 = 양 끝에서 어긋나는 폭 : 겨울 +"
        + (cold.corr - MEAN).toFixed(1) + " MW · 여름 "
        + (hot.corr - MEAN).toFixed(1) + " MW",
      options: { color: HINT } },
  ], {
    x: 0.85, y: 3.93, w: 5.5, h: 0.40, fontFace: F, fontSize: 9,
    margin: 0, lineSpacing: 12,
  });

  /* ── 우 : 같은 데이터로 방식 비교 ── */
  card(s, 6.88, 1.56, 5.9, 2.8);
  s.addText("같은 데이터로 비교 — 시험 31건 교차검증", {
    x: 7.2, y: 1.74, w: 5.3, h: 0.28, fontFace: F, fontSize: 11.5, bold: true,
    color: INK, margin: 0, valign: "middle",
  });
  const CW = [2.24, 1.06, 0.76, 1.24], CX = [7.2, 9.44, 10.5, 11.26];
  ["보정 방식", "예측오차", "미달", "과대입찰"].forEach((t, i) => s.addText(t, {
    x: CX[i], y: 2.08, w: CW[i], h: 0.26, fontFace: F, fontSize: 9, bold: true,
    color: HINT, align: i ? "right" : "left", margin: 0, valign: "middle",
  }));
  s.addShape(p.ShapeType.line, {
    x: 7.2, y: 2.36, w: 5.3, h: 0, line: { color: LINE, width: 1 },
  });
  const cmp = [
    ["일괄 보정 (종전)", "3.63 MW", "10건", "51.9 MW", "8A7F7A", false],
    ["온도 구간평균", "1.52 MW", "4건", "10.5 MW", GRAY, false],
    ["온도별 곡선 (현재)", "1.33 MW", "2건", "5.3 MW", RED, true],
    ["＋ 안전마진 적용", "1.73 MW", "0건", "0.0 MW", RED, true],
  ];
  cmp.forEach(([m, e, sh, ov, col, on], i) => {
    const y = 2.42 + i * 0.4;
    if (on) s.addShape(p.ShapeType.rect, {
      x: 7.1, y: y - 0.02, w: 5.5, h: 0.36, fill: { color: TINT },
    });
    [m, e, sh, ov].forEach((v, k) => s.addText(v, {
      x: CX[k], y, w: CW[k], h: 0.32, fontFace: F, fontSize: 10.5, bold: on || k > 0,
      color: k === 0 ? INK : col, align: k ? "right" : "left",
      margin: 0, valign: "middle",
    }));
  });
  s.addText("예측오차 = 평균적으로 틀리는 폭  ·  미달 = 신고량을 못 지킨 횟수(31건 중)\n"
    + "과대입찰 = 미달 건들의 부족분 합계 — 페널티 위험에 노출된 총량", {
    x: 7.2, y: 4.02, w: 5.3, h: 0.32, fontFace: F, fontSize: 8.5,
    color: HINT, margin: 0, lineSpacing: 11,
  });

  /* ── 하단 : 왜 상수로는 안 되나 / 운용 순서 재검증 ── */
  secTitle(s, 0.55, 4.5, "하나의 값으로는 고칠 수 없는 구조", ORG);
  card(s, 0.55, 4.92, 6.1, 1.74, TINT);
  // 문장으로 쓰면 10.5pt 에서 줄이 넘쳐 카드를 벗어난다 → 미니 표로 정리
  [["겨울  −1.9°C", "실측 +12.9", "일괄 +" + MEAN.toFixed(1),
    (cold.corr - MEAN).toFixed(1) + " MW 낮게 신고 = 기회손실", RED],
   ["여름  30.7°C", "실측 −3.4", "일괄 +" + MEAN.toFixed(1),
    (MEAN - hot.corr).toFixed(1) + " MW 높게 신고 = 미달 위험", ORG],
  ].forEach(([a, b, c, d, col], i) => {
    const y = 5.12 + i * 0.46;
    s.addText(a, {
      x: 0.88, y, w: 1.35, h: 0.34, fontFace: F, fontSize: 10.5, bold: true,
      color: col, margin: 0, valign: "middle",
    });
    s.addText(b, {
      x: 2.26, y, w: 1.05, h: 0.34, fontFace: F, fontSize: 10.5, color: INK,
      margin: 0, valign: "middle",
    });
    s.addText(c, {
      x: 3.34, y, w: 1.05, h: 0.34, fontFace: F, fontSize: 10.5, color: "8A7F7A",
      margin: 0, valign: "middle",
    });
    s.addText("→  " + d, {
      x: 4.42, y, w: 2.08, h: 0.34, fontFace: F, fontSize: 10.5, bold: true,
      color: INK, margin: 0, valign: "middle",
    });
  });
  s.addText("틀리는 방향이 반대입니다. 일괄값을 올리면 여름 미달이 커지고, "
    + "내리면 겨울 기회손실이 커집니다.", {
    x: 0.88, y: 6.08, w: 5.46, h: 0.44, fontFace: F, fontSize: 10,
    color: GRAY, margin: 0, lineSpacing: 14,
  });

  // secTitle 의 hint 는 x+5.5·w6.7 고정이라 오른쪽 절반에서 쓰면 슬라이드를
  // 벗어난다(12.38~19.08). 설명은 카드 안에 넣는다.
  secTitle(s, 6.88, 4.5, "실제 운용 순서로 재검증", "8A7F7A");
  card(s, 6.88, 4.92, 5.9, 1.74);
  s.addText("과거만 보고 다음 시험을 예측 (23건)", {
    x: 7.2, y: 5.02, w: 2.75, h: 0.26, fontFace: F, fontSize: 8.5,
    color: HINT, margin: 0, valign: "middle",
  });
  const wf = [
    ["예측오차", "2.83 MW", "1.79 MW"],
    ["미달", "5건", "1건"],
    ["손실 합계 (과대입찰＋기회손실)", "58.3 MW", "30.0 MW"],
  ];
  s.addText("종전", {
    x: 10.0, y: 5.06, w: 1.2, h: 0.24, fontFace: F, fontSize: 9, bold: true,
    color: HINT, align: "right", margin: 0,
  });
  s.addText("현재", {
    x: 11.25, y: 5.06, w: 1.25, h: 0.24, fontFace: F, fontSize: 9, bold: true,
    color: RED, align: "right", margin: 0,
  });
  wf.forEach(([k, a, b], i) => {
    const y = 5.34 + i * 0.36;
    s.addText(k, {
      x: 7.2, y, w: 2.75, h: 0.3, fontFace: F, fontSize: 10, color: GRAY,
      margin: 0, valign: "middle",
    });
    s.addText(a, {
      x: 10.0, y, w: 1.2, h: 0.3, fontFace: F, fontSize: 10.5, color: "8A7F7A",
      align: "right", margin: 0, valign: "middle",
    });
    s.addText(b, {
      x: 11.25, y, w: 1.25, h: 0.3, fontFace: F, fontSize: 10.5, bold: true,
      color: RED, align: "right", margin: 0, valign: "middle",
    });
  });
  s.addText("※ 초기 학습 데이터가 적어 오차가 큽니다 — 시험이 쌓이면 줄어듭니다.", {
    x: 7.2, y: 6.38, w: 5.3, h: 0.24, fontFace: F, fontSize: 8.5,
    color: HINT, margin: 0,
  });

  card(s, 0.55, 6.78, 12.23, 0.5, INK);
  s.addText("보정값 하나 → 온도별 곡선 : 예측오차 3.63 → 1.33 MW, "
    + "신고량 미달 10건 → 0건 (안전마진 적용 시)", {
    x: 0.85, y: 6.83, w: 11.6, h: 0.4, fontFace: F, fontSize: 12, bold: true,
    color: "FFFFFF", margin: 0, valign: "middle",
  });

  s.addNotes("종전에는 이론값과 실제값의 차이를 평균해 온도와 무관하게 같은 보정값을 일괄 적용했습니다. "
    + "그런데 실제 보정값은 온도에 따라 -3.5에서 +12.9 MW까지 폭 16.4 MW로 변합니다. "
    + "수평선 하나로는 양 끝을 동시에 맞출 수 없습니다. 겨울에는 9.7 MW 낮게 신고해 팔 수 있는 만큼 "
    + "못 팔고, 여름에는 7.2 MW 높게 신고해 신고량을 못 지킬 위험이 생깁니다. 틀리는 방향이 반대라 "
    + "일괄값을 올리거나 내려도 한쪽이 나빠집니다. 온도별 곡선으로 바꾸면 예측오차가 3.63에서 "
    + "1.33 MW로 줄고, 안전마진을 적용하면 미달이 0건이 됩니다. "
    + "※ 비교는 '일괄'에 가능한 최선(학습 보정값 평균)을 준 값이라 실제 적용값이 이보다 좋을 수 없습니다. "
    + "재현: tool/scripts/method_compare.py");
}

/* ══════════════ 4장 : 진행상황 · 배포 · 향후 ══════════════ */
{
  const s = p.addSlide();
  s.background = { color: BG };
  head(s, 4, "어디까지 왔고, 앞으로");

  secTitle(s, 0.55, 1.12, "진행 현황", RED, "1차 개발 완료 · 현재 시운전 단계");

  const ms = [
    ["'26.6월", "기존 방식 분석", "엑셀 4개 계산 구조 파악", "완료"],
    ["'26.6월", "계산 엔진 개발", "기존 결과와 동일함 검증", "완료"],
    ["'26.7월", "데이터 자동 취득", "발전소 서버 직접 연결", "완료"],
    ["'26.8월", "프로그램 완성", "화면 5개 · 실행파일 배포", "완료"],
    ["'26.8월~", "시운전 검증", "실제 시험으로 정확도 확인", "진행중"],
    ["'26.9월", "정식 운영", "현업 적용", "예정"],
  ];
  const tlY = 2.42, x0 = 1.0, gap = 1.94;   // x0 0.85 이면 첫 라벨(cx-0.95)이 슬라이드를 벗어난다
  s.addShape(p.ShapeType.line, {
    x: x0, y: tlY, w: gap * (ms.length - 1), h: 0, line: { color: LINE, width: 3 },
  });
  s.addShape(p.ShapeType.line, {
    x: x0, y: tlY, w: gap * 4, h: 0, line: { color: RED, width: 3 },
  });
  ms.forEach(([dt, t, d, st], i) => {
    const cx = x0 + i * gap;
    const done = st === "완료", now = st === "진행중";
    const c = done ? RED : now ? ORG : "C9BFBB";
    // 날짜 (점 위)
    s.addText(dt, {
      x: cx - 0.7, y: tlY - 0.92, w: 1.4, h: 0.26, fontFace: F, fontSize: 11, bold: true,
      color: done || now ? INK : "9A908C", align: "center", margin: 0,
    });
    s.addText(st, {
      x: cx - 0.7, y: tlY - 0.62, w: 1.4, h: 0.24, fontFace: F, fontSize: 9.5, bold: true,
      color: c, align: "center", margin: 0,
    });
    if (now) s.addShape(p.ShapeType.ellipse, {
      x: cx - 0.28, y: tlY - 0.28, w: 0.56, h: 0.56,
      fill: { color: ORG, transparency: 80 }, line: { color: ORG, width: 1 },
    });
    s.addShape(p.ShapeType.ellipse, {
      x: cx - 0.16, y: tlY - 0.16, w: 0.32, h: 0.32, fill: { color: c },
      line: { color: "FFFFFF", width: 2 },
    });
    s.addText(t, {
      x: cx - 0.92, y: tlY + 0.26, w: 1.84, h: 0.3, fontFace: F, fontSize: 11.5, bold: true,
      color: done || now ? INK : "9A908C", align: "center", margin: 0,
    });
    s.addText(d, {
      x: cx - 0.95, y: tlY + 0.56, w: 1.9, h: 0.5, fontFace: F, fontSize: 9.5,
      color: GRAY, align: "center", margin: 0, lineSpacing: 12,
    });
  });

  // 하단 3분할
  const boxes = [
    ["배포 방법", RED, [
      "폴더 하나만 복사하면 끝 (설치 불필요)",
      "사내 PC에서 바로 실행",
      "엑셀·별도 프로그램 설치 필요 없음",
    ]],
    ["보안 — 자료 외부 유출 없음", ORG, [
      "모든 계산이 사내 PC 안에서만 수행",
      "외부 인터넷·외부 AI 서버 전송 없음",
      "데이터는 담당자 PC에만 저장",
    ]],
    ["향후 계획", "8A7F7A", [
      "시운전으로 실제 데이터 검증",
      "오류 발견 시 즉시 보완",
      "시험 결과가 쌓일수록 정확도 향상",
    ]],
  ];
  boxes.forEach(([t, c, items], i) => {
    const x = 0.55 + i * 4.24;
    card(s, x, 4.14, 3.9, 2.42);
    s.addShape(p.ShapeType.ellipse, { x: x + 0.28, y: 4.38, w: 0.26, h: 0.26, fill: { color: c } });
    s.addText(t, {
      x: x + 0.66, y: 4.33, w: 3.1, h: 0.36, fontFace: F, fontSize: 12.5, bold: true,
      color: INK, margin: 0, valign: "middle",
    });
    s.addText(items.map((v, k) => ({
      text: v, options: { bullet: true, breakLine: k < items.length - 1 },
    })), {
      x: x + 0.3, y: 4.82, w: 3.34, h: 1.6, fontFace: F, fontSize: 11, color: GRAY,
      paraSpaceAfter: 7, margin: 0, lineSpacing: 15,
    });
  });

  card(s, 0.55, 6.72, 12.23, 0.52, INK);
  s.addText("1차 개발 완료 — 현재 시운전 단계 · 실제 시험으로 검증하며 정확도를 계속 높여갑니다", {
    x: 0.85, y: 6.78, w: 11.6, h: 0.4, fontFace: F, fontSize: 12, bold: true,
    color: "FFFFFF", margin: 0, valign: "middle",
  });
  s.addNotes("6월 분석·엔진 개발, 7월 데이터 자동취득, 8월 프로그램 완성까지 마쳤고 현재 시운전 중입니다. "
    + "9월 정식 운영이 목표입니다. 배포는 폴더 복사만으로 가능하며, 모든 계산이 사내 PC 안에서만 "
    + "이뤄져 자료가 외부로 나가지 않습니다. ※ 마일스톤 날짜는 실제 일정에 맞게 수정하세요.");
}

p.writeFile({ fileName: DIR + "PPT1_공급가능용량_프로젝트보고.pptx" })
  .then(f => console.log("생성:", f));
