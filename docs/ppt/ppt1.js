// PPT-1 : 공급가능용량 자동산정 Tool 개발 보고 (3장)
// SK 브랜드 — 레드 EA002C / 오렌지 F47725
const pptx = require("pptxgenjs");
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
    ["온도가 변수입니다", "같은 발전소라도 기온에 따라\n출력이 376~469 MW 로 변동", ORG],
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
    { text: "기존 엑셀과 동일 계산 확인 (오차 0.18 MW)", options: { bullet: true } },
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
    ["32", "건", "축적된 시험 결과\n(−1.9 ~ 36.1°C)", RED],
    ["0.18", "MW", "기존 엑셀 대비\n최대 계산 오차", INK],
    ["1.24", "MW", "예측 오차\n(1.42 → 12% 개선)", RED],
    ["61", "개", "자동 산출 온도 구간\n(−20 ~ 40°C)", INK],
    ["±0.5", "%", "입찰 허용범위\n(약 ±2 MW)", "8A7F7A"],
  ];
  kpi.forEach(([v, u, l, c], i) => stat(s, 0.95 + i * 2.4, 6.24, 2.25, v, u, l, c));

  s.addNotes("전력 판매를 위해 매일 '내일 낼 수 있는 전기량'을 신고합니다. 기온에 따라 출력이 376~469MW로 "
    + "크게 달라지고, 허용범위가 ±0.5%(약 ±2MW)라 정확도가 중요합니다. 기존에는 엑셀 4개를 오가며 "
    + "손으로 계산했는데 이를 자동화했고, 기존 엑셀과 계산이 동일함을 오차 0.18MW로 확인했습니다.");
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
    ["s_list.png", "시험 결과 목록", "누적 32건 관리\n(날짜·온도·측정값)", RED],
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
    { text: "실제 시험 32건에서 배운 차이를 반영", options: { fontSize: 11, color: GRAY, breakLine: true } },
    { text: "", options: { fontSize: 5, breakLine: true } },
    { text: "신고값 = 이론값 + 보정값", options: { fontSize: 12.5, bold: true, color: INK } },
  ], { x: 0.9, y: 5.44, w: 5.25, h: 1.64, fontFace: F, margin: 0, lineSpacing: 15 });

  secTitle(s, 6.88, 4.82, "정확도 · 검증", "8A7F7A");
  card(s, 6.88, 5.24, 5.9, 2.0);
  const rows = [
    ["기존 엑셀과 계산 일치", "최대 오차 0.18 MW", RED],
    ["예측 오차 (시험 32건 교차검증)", "1.42 → 1.24 MW", RED],
    ["데이터 취득값 일치 확인", "24.85262 = 24.8526", INK],
    ["계산 검증 항목 자동 점검", "150개 / 수정 시마다", INK],
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
  s.addText("※ 계산식이 바뀌면 150개 항목을 자동으로 다시 검사 — 오류를 사전에 차단", {
    x: 7.2, y: 6.94, w: 5.35, h: 0.26, fontFace: F, fontSize: 9,
    color: HINT, margin: 0,
  });

  s.addNotes("화면 5개로 구성했습니다. 계산은 2단 구조입니다 — 1단은 설계 성능곡선(기존 엑셀과 동일), "
    + "2단은 실제 시험 32건에서 배운 보정값입니다. '150개 자동 점검'은 계산식을 수정할 때마다 "
    + "프로그램이 스스로 150가지 항목을 다시 검사해 계산 오류를 사전에 막는 장치입니다.");
}

/* ══════════════ 3장 : 진행상황 · 배포 · 향후 ══════════════ */
{
  const s = p.addSlide();
  s.background = { color: BG };
  head(s, 3, "어디까지 왔고, 앞으로");

  secTitle(s, 0.55, 1.12, "진행 현황", RED, "1차 개발 완료 · 현재 시운전 단계");

  const ms = [
    ["'26.6월", "기존 방식 분석", "엑셀 4개 계산 구조 파악", "완료"],
    ["'26.6월", "계산 엔진 개발", "기존 결과와 동일함 검증", "완료"],
    ["'26.7월", "데이터 자동 취득", "발전소 서버 직접 연결", "완료"],
    ["'26.8월", "프로그램 완성", "화면 5개 · 실행파일 배포", "완료"],
    ["'26.8월~", "시운전 검증", "실제 시험으로 정확도 확인", "진행중"],
    ["'26.9월", "정식 운영", "현업 적용", "예정"],
  ];
  const tlY = 2.42, x0 = 0.85, gap = 1.94;
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
