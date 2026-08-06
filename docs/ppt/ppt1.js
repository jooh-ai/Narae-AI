// PPT-1 : 공급가능용량 자동산정 Tool 개발 보고 (3장)
// SK 브랜드 — 레드 EA002C / 오렌지 F47725
const pptx = require("pptxgenjs");
const p = new pptx();
p.layout = "LAYOUT_WIDE";              // 13.3 x 7.5 in
p.author = "발전운영팀";
p.title = "공급가능용량 자동산정 Tool";

const RED = "EA002C", ORG = "F47725", INK = "1F1A18", GRAY = "6B625E";
const LINE = "E8E0DC", BG = "FFFFFF", TINT = "FFF4EE";
const F = "맑은 고딕";
const DIR = __dirname + "/";   // 이 스크립트와 같은 폴더의 s_*.png / 출력 pptx

// ── 공통: 슬라이드 머리 ──
function head(s, no, title, sub) {
  s.addShape(p.ShapeType.rect, { x: 0, y: 0, w: 13.33, h: 1.0, fill: { color: INK } });
  s.addText(String(no).padStart(2, "0"), {
    x: 0.45, y: 0.18, w: 0.7, h: 0.62, fontFace: F, fontSize: 26, bold: true,
    color: ORG, align: "left", margin: 0, valign: "middle",
  });
  s.addText(title, {
    x: 1.15, y: 0.18, w: 5.6, h: 0.62, fontFace: F, fontSize: 23, bold: true,
    color: "FFFFFF", margin: 0, valign: "middle",
  });
  if (sub) s.addText(sub, {
    x: 6.85, y: 0.18, w: 6.05, h: 0.62, fontFace: F, fontSize: 12.5,
    color: "C9BFBB", align: "right", margin: 0, valign: "middle",
  });
}
function card(s, x, y, w, h, fill) {
  s.addShape(p.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.06, fill: { color: fill || "FFFFFF" },
    line: { color: LINE, width: 1 },
    shadow: { type: "outer", angle: 90, blur: 8, offset: 1, color: "D8CFCA", opacity: 0.5 },
  });
}
function dot(s, x, y, n, color) {   // 번호 원형 배지
  s.addShape(p.ShapeType.ellipse, { x, y, w: 0.34, h: 0.34, fill: { color: color || RED } });
  s.addText(String(n), {
    x, y, w: 0.34, h: 0.34, fontFace: F, fontSize: 13, bold: true,
    color: "FFFFFF", align: "center", valign: "middle", margin: 0,
  });
}

/* ══════════════ 1장 : 왜 만들었나 ══════════════ */
{
  const s = p.addSlide();
  s.background = { color: BG };
  head(s, 1, "왜 만들었나", "매일 전기 판매량을 정확히 신고해야 합니다");

  // 상황 설명 3단계 흐름
  const steps = [
    ["매일 신고", "내일 우리 발전소가\n낼 수 있는 전기량을\n전력거래소에 신고", RED],
    ["온도가 변수", "같은 발전소라도\n날씨(기온)에 따라\n출력이 크게 달라짐", ORG],
    ["정확도가 곧 돈", "적게 신고 → 덜 팔아 손해\n못 지키면 → 페널티", "8A7F7A"],
  ];
  steps.forEach(([t, d, c], i) => {
    const x = 0.55 + i * 4.24;
    card(s, x, 1.35, 3.9, 1.72);
    s.addShape(p.ShapeType.ellipse, { x: x + 0.28, y: 1.62, w: 0.42, h: 0.42, fill: { color: c } });
    s.addText(String(i + 1), {
      x: x + 0.28, y: 1.62, w: 0.42, h: 0.42, fontFace: F, fontSize: 15, bold: true,
      color: "FFFFFF", align: "center", valign: "middle", margin: 0,
    });
    s.addText(t, {
      x: x + 0.85, y: 1.58, w: 2.8, h: 0.4, fontFace: F, fontSize: 15, bold: true,
      color: INK, margin: 0, valign: "middle",
    });
    s.addText(d, {
      x: x + 0.28, y: 2.12, w: 3.35, h: 0.82, fontFace: F, fontSize: 11.5,
      color: GRAY, margin: 0, lineSpacing: 16,
    });
  });

  // 문제 → 해결 (Before / After)
  s.addText("지금까지는 이렇게 했습니다", {
    x: 0.55, y: 3.32, w: 5.9, h: 0.34, fontFace: F, fontSize: 14, bold: true,
    color: GRAY, margin: 0,
  });
  card(s, 0.55, 3.72, 5.9, 2.72, "F7F4F2");
  s.addText([
    { text: "담당자가 엑셀 4개를 오가며 직접 계산", options: { bullet: true, breakLine: true } },
    { text: "테스트 결과를 손으로 옮겨 적고 평균을 냄", options: { bullet: true, breakLine: true } },
    { text: "한 번 만드는 데 시간이 오래 걸림", options: { bullet: true, breakLine: true } },
    { text: "사람이 하는 일이라 실수 가능성이 있음", options: { bullet: true } },
  ], {
    x: 0.9, y: 4.05, w: 5.2, h: 1.6, fontFace: F, fontSize: 13, color: INK,
    paraSpaceAfter: 8, margin: 0,
  });
  s.addText("＂엑셀 4개 · 수작업 · 반복＂", {
    x: 0.9, y: 5.78, w: 5.2, h: 0.4, fontFace: F, fontSize: 13, italic: true,
    color: GRAY, margin: 0,
  });

  s.addText("그래서 이렇게 바꿨습니다", {
    x: 6.88, y: 3.32, w: 5.9, h: 0.34, fontFace: F, fontSize: 14, bold: true,
    color: RED, margin: 0,
  });
  card(s, 6.88, 3.72, 5.9, 2.72, TINT);
  s.addText([
    { text: "날짜만 입력하면 발전소 데이터를 자동으로 가져옴", options: { bullet: true, breakLine: true } },
    { text: "계산·보정·검증까지 프로그램이 처리", options: { bullet: true, breakLine: true } },
    { text: "신고용 엑셀 파일까지 자동 생성", options: { bullet: true, breakLine: true } },
    { text: "계산 결과는 기존 엑셀과 동일함을 확인", options: { bullet: true } },
  ], {
    x: 7.23, y: 4.05, w: 5.2, h: 1.6, fontFace: F, fontSize: 13, color: INK,
    paraSpaceAfter: 8, margin: 0,
  });
  s.addText("＂날짜 입력 → 클릭 한 번＂", {
    x: 7.23, y: 5.78, w: 5.2, h: 0.4, fontFace: F, fontSize: 13, italic: true, bold: true,
    color: RED, margin: 0,
  });

  // 하단 성과 요약
  card(s, 0.55, 6.62, 12.23, 0.62, INK);
  const kpi = [["작업 시간", "수 시간 → 클릭 한 번"], ["계산 정확도", "기존 엑셀과 동일 (오차 0.18MW)"],
               ["예측 오차", "1.42 → 1.24 MW 개선"], ["자동 검증", "150건 상시 점검"]];
  kpi.forEach(([k, v], i) => {
    const x = 0.85 + i * 3.02;
    s.addText(k, { x, y: 6.72, w: 2.9, h: 0.2, fontFace: F, fontSize: 9.5, color: "A99F9B", margin: 0 });
    s.addText(v, { x, y: 6.92, w: 2.9, h: 0.24, fontFace: F, fontSize: 11.5, bold: true, color: "FFFFFF", margin: 0 });
  });
  s.addNotes("전력 판매를 위해 매일 '내일 낼 수 있는 전기량'을 신고합니다. 기온에 따라 출력이 달라지고, 신고값이 정확해야 손해도 페널티도 없습니다. 기존에는 엑셀 4개를 오가며 손으로 계산했는데, 이를 프로그램 하나로 자동화했습니다.");
}

/* ══════════════ 2장 : 무엇을 만들었나 ══════════════ */
{
  const s = p.addSlide();
  s.background = { color: BG };
  head(s, 2, "무엇을 만들었나", "화면 5개짜리 Windows 프로그램");

  // 좌: 기능 목록
  const feats = [
    ["공급가능용량 산정", "날짜만 입력 → 자동 취득 → 신고파일 생성"],
    ["온도별 보정값 현황", "구간별 데이터가 충분한지 신호등 표시"],
    ["테스트 결과 목록", "지금까지 쌓인 시험 결과 관리"],
    ["출력 시뮬레이션", "조건을 넣어 예상 출력 확인 · 시험 후 대조"],
    ["출력곡선 비교", "이론값과 보정 후 값을 그래프로 비교"],
  ];
  feats.forEach(([t, d], i) => {
    const y = 1.32 + i * 1.06;
    dot(s, 0.6, y + 0.1, i + 1, i < 3 ? RED : ORG);
    s.addText(t, {
      x: 1.08, y: y + 0.02, w: 4.6, h: 0.32, fontFace: F, fontSize: 14, bold: true,
      color: INK, margin: 0, valign: "middle",
    });
    s.addText(d, {
      x: 1.08, y: y + 0.36, w: 4.7, h: 0.5, fontFace: F, fontSize: 11.5,
      color: GRAY, margin: 0, lineSpacing: 15,
    });
  });

  // 우: 화면 사진 2장
  card(s, 6.05, 1.28, 6.75, 2.62);
  s.addImage({ path: DIR + "s_run.png", x: 6.2, y: 1.42, w: 6.45, h: 2.34 });
  s.addText("① 공급가능용량 산정 화면", {
    x: 6.05, y: 3.93, w: 6.75, h: 0.26, fontFace: F, fontSize: 10.5, color: GRAY,
    align: "center", margin: 0,
  });

  card(s, 6.05, 4.3, 6.75, 2.62);
  s.addImage({ path: DIR + "s_chart.png", x: 6.2, y: 4.44, w: 6.45, h: 2.34 });
  s.addText("⑤ 출력곡선 비교 — 이론값(회색) vs 보정 후(빨강)", {
    x: 6.05, y: 6.95, w: 6.75, h: 0.26, fontFace: F, fontSize: 10.5, color: GRAY,
    align: "center", margin: 0,
  });

  // 좌하단: 계산 방식 한 줄 설명
  card(s, 0.55, 6.62, 5.25, 0.62, TINT);
  s.addText("계산 방식 : 설계 이론값 + 실제 시험으로 배운 보정값", {
    x: 0.8, y: 6.72, w: 4.9, h: 0.42, fontFace: F, fontSize: 11.5, bold: true,
    color: RED, margin: 0, valign: "middle",
  });
  s.addNotes("화면 5개로 구성했습니다. 계산 방식은 설계 이론값에 실제 시험에서 배운 보정값을 더하는 구조입니다. 시험 성적표로 비유하면, 교과서 예상 점수(이론값)에 실제 시험에서 늘 얼마씩 차이 나는지(보정값)를 반영하는 것입니다.");
}

/* ══════════════ 3장 : 진행상황 · 배포 · 향후 ══════════════ */
{
  const s = p.addSlide();
  s.background = { color: BG };
  head(s, 3, "어디까지 왔고, 앞으로", "2026년 8월 기준 · 발전운영팀");

  // 마일스톤 타임라인
  s.addText("진행 현황", {
    x: 0.55, y: 1.18, w: 4, h: 0.28, fontFace: F, fontSize: 14, bold: true, color: INK, margin: 0,
  });
  const ms = [
    ["기존 방식 분석", "엑셀 4개 계산 구조 파악", "완료"],
    ["계산 엔진 개발", "기존 결과와 동일함 검증", "완료"],
    ["데이터 자동 취득", "발전소 서버 직접 연결", "완료"],
    ["프로그램 완성", "화면 5개 · 실행파일 배포", "완료"],
    ["시운전 검증", "실제 시험으로 정확도 확인", "진행중"],
    ["정식 운영", "현업 적용", "예정"],
  ];
  const tlY = 2.32;
  s.addShape(p.ShapeType.line, {
    x: 0.85, y: tlY, w: 1.94 * (ms.length - 1), h: 0, line: { color: LINE, width: 3 },
  });
  s.addShape(p.ShapeType.line, {
    x: 0.85, y: tlY, w: 7.55, h: 0, line: { color: RED, width: 3 },
  });
  ms.forEach(([t, d, st], i) => {
    const cx = 0.85 + i * 1.94;
    const done = st === "완료", now = st === "진행중";
    const c = done ? RED : now ? ORG : "C9BFBB";
    s.addShape(p.ShapeType.ellipse, {
      x: cx - 0.16, y: tlY - 0.16, w: 0.32, h: 0.32, fill: { color: c },
      line: { color: "FFFFFF", width: 2 },
    });
    if (now) s.addShape(p.ShapeType.ellipse, {
      x: cx - 0.28, y: tlY - 0.28, w: 0.56, h: 0.56,
      fill: { color: ORG, transparency: 80 }, line: { color: ORG, width: 1 },
    });
    s.addText(st, {
      x: cx - 0.62, y: tlY - 0.78, w: 1.24, h: 0.26, fontFace: F, fontSize: 9.5, bold: true,
      color: c, align: "center", margin: 0,
    });
    s.addText(t, {
      x: cx - 0.9, y: tlY + 0.26, w: 1.8, h: 0.3, fontFace: F, fontSize: 11.5, bold: true,
      color: done || now ? INK : "9A908C", align: "center", margin: 0,
    });
    s.addText(d, {
      x: cx - 0.95, y: tlY + 0.56, w: 1.9, h: 0.5, fontFace: F, fontSize: 9.5,
      color: GRAY, align: "center", margin: 0, lineSpacing: 12,
    });
  });

  // 하단 3분할: 배포 / 보안 / 향후
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
    card(s, x, 3.98, 3.9, 2.52);
    s.addShape(p.ShapeType.ellipse, { x: x + 0.28, y: 4.24, w: 0.28, h: 0.28, fill: { color: c } });
    s.addText(t, {
      x: x + 0.68, y: 4.18, w: 3.1, h: 0.4, fontFace: F, fontSize: 13, bold: true,
      color: INK, margin: 0, valign: "middle",
    });
    s.addText(items.map((v, k) => ({
      text: v, options: { bullet: true, breakLine: k < items.length - 1 },
    })), {
      x: x + 0.3, y: 4.7, w: 3.34, h: 1.6, fontFace: F, fontSize: 11.5, color: GRAY,
      paraSpaceAfter: 7, margin: 0, lineSpacing: 15,
    });
  });

  // 결론 바
  card(s, 0.55, 6.66, 12.23, 0.6, INK);
  s.addText("1차 개발 완료 — 현재 시운전 단계 · 실제 시험으로 검증하며 정확도를 계속 높여갑니다", {
    x: 0.85, y: 6.74, w: 11.6, h: 0.44, fontFace: F, fontSize: 12.5, bold: true,
    color: "FFFFFF", margin: 0, valign: "middle",
  });
  s.addNotes("1차 개발은 완료됐고 지금은 시운전 단계입니다. 배포는 폴더 복사만으로 가능하며, 모든 계산이 사내 PC 안에서만 이뤄져 자료가 외부로 나가지 않습니다. 앞으로 실제 시험 결과를 쌓아가며 정확도를 높일 계획입니다.");
}

p.writeFile({ fileName: DIR + "PPT1_공급가능용량_프로젝트보고.pptx" })
  .then(f => console.log("생성:", f));
