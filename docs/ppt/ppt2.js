// PPT-2 : 팀 소규모 프로젝트 발표 양식 (프로젝트당 1장 × 5장)
// PPT-1 과 동일한 SK 브랜드 양식 — 내용은 비워 두고 채우기만 하면 되도록 구성
const pptx = require("pptxgenjs");
const p = new pptx();
p.layout = "LAYOUT_WIDE";
p.author = "발전운영팀";
p.title = "팀 프로젝트 현황";

const RED = "EA002C", ORG = "F47725", INK = "1F1A18", GRAY = "6B625E";
const LINE = "E8E0DC", BG = "FFFFFF", TINT = "FFF4EE", HINT = "B3A9A5";
const F = "맑은 고딕";
const DIR = __dirname + "/";   // 이 스크립트와 같은 폴더의 s_*.png / 출력 pptx

function head(s, no, title, sub) {
  s.addShape(p.ShapeType.rect, { x: 0, y: 0, w: 13.33, h: 1.0, fill: { color: INK } });
  s.addText(String(no).padStart(2, "0"), {
    x: 0.45, y: 0.18, w: 0.7, h: 0.62, fontFace: F, fontSize: 26, bold: true,
    color: ORG, margin: 0, valign: "middle",
  });
  s.addText(title, {
    x: 1.15, y: 0.18, w: 5.6, h: 0.62, fontFace: F, fontSize: 23, bold: true,
    color: "FFFFFF", margin: 0, valign: "middle",
  });
  s.addText(sub, {
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
function secTitle(s, x, y, text, color) {
  s.addShape(p.ShapeType.ellipse, { x, y: y + 0.05, w: 0.26, h: 0.26, fill: { color: color || RED } });
  s.addText(text, {
    x: x + 0.4, y, w: 4.4, h: 0.36, fontFace: F, fontSize: 13.5, bold: true,
    color: INK, margin: 0, valign: "middle",
  });
}
// 채워 넣을 자리 — 회색 안내문(발표 전 교체)
function slot(s, x, y, w, h, lines, size) {
  s.addText(lines.map((v, i) => ({
    text: v, options: { bullet: true, breakLine: i < lines.length - 1 },
  })), {
    x, y, w, h, fontFace: F, fontSize: size || 12, color: HINT,
    paraSpaceAfter: 8, margin: 0, lineSpacing: 16,
  });
}

/* ── 5개 프로젝트 × 1장 ── */
const PROJECTS = [
  ["프로젝트 ①", "프로젝트명을 입력하세요"],
  ["프로젝트 ②", "프로젝트명을 입력하세요"],
  ["프로젝트 ③", "프로젝트명을 입력하세요"],
  ["프로젝트 ④", "프로젝트명을 입력하세요"],
  ["프로젝트 ⑤", "프로젝트명을 입력하세요"],
];

PROJECTS.forEach(([title, sub], idx) => {
  const s = p.addSlide();
  s.background = { color: BG };
  head(s, idx + 1, title, sub);

  /* ── 좌측 상단 : 목적 ── */
  secTitle(s, 0.55, 1.22, "목적 — 왜 하는가", RED);
  card(s, 0.55, 1.68, 5.9, 1.95);
  slot(s, 0.9, 1.95, 5.2, 1.45, [
    "해결하려는 문제를 한 줄로 적으세요",
    "기대 효과(시간 절감·정확도·비용 등)",
    "적용 대상 설비 또는 업무 범위",
  ], 12.5);

  /* ── 좌측 하단 : 진행 현황(4단계 타임라인) ── */
  secTitle(s, 0.55, 3.82, "진행 현황", ORG);
  const steps = ["기획", "개발", "검증", "적용"];
  const tlY = 5.00, x0 = 1.05, gap = 1.62;
  s.addShape(p.ShapeType.line, {
    x: x0, y: tlY, w: gap * (steps.length - 1), h: 0, line: { color: LINE, width: 3 },
  });
  s.addShape(p.ShapeType.line, {          // 완료 구간 — 실제 진척에 맞춰 길이 조정
    x: x0, y: tlY, w: gap, h: 0, line: { color: RED, width: 3 },
  });
  steps.forEach((t, i) => {
    const cx = x0 + i * gap;
    const done = i === 0, now = i === 1;
    const c = done ? RED : now ? ORG : "C9BFBB";
    s.addShape(p.ShapeType.ellipse, {
      x: cx - 0.15, y: tlY - 0.15, w: 0.3, h: 0.3, fill: { color: c },
      line: { color: "FFFFFF", width: 2 },
    });
    s.addText(done ? "완료" : now ? "진행중" : "예정", {
      x: cx - 0.6, y: tlY - 0.58, w: 1.2, h: 0.24, fontFace: F, fontSize: 9.5, bold: true,
      color: c, align: "center", margin: 0,
    });
    s.addText(t, {
      x: cx - 0.7, y: tlY + 0.22, w: 1.4, h: 0.28, fontFace: F, fontSize: 12, bold: true,
      color: done || now ? INK : "9A908C", align: "center", margin: 0,
    });
  });
  s.addText("※ 단계명·완료 표시는 프로젝트에 맞게 수정", {
    x: 0.55, y: 5.56, w: 5.9, h: 0.26, fontFace: F, fontSize: 9.5, color: HINT, margin: 0,
  });

  /* ── 좌측 최하단 : 주요 성과 / 수치 ── */
  card(s, 0.55, 5.86, 5.9, 1.38, TINT);
  s.addText("주요 성과 · 수치", {
    x: 0.9, y: 6.02, w: 5.2, h: 0.26, fontFace: F, fontSize: 11.5, bold: true,
    color: RED, margin: 0,
  });
  [0, 1, 2].forEach(i => {
    const x = 0.9 + i * 1.78;
    s.addText("항목", { x, y: 6.38, w: 1.6, h: 0.22, fontFace: F, fontSize: 9.5, color: HINT, margin: 0 });
    s.addText("00", { x, y: 6.60, w: 1.6, h: 0.42, fontFace: F, fontSize: 20, bold: true, color: INK, margin: 0 });
  });

  /* ── 우측 : 사진 / 화면 2칸 ── */
  secTitle(s, 6.88, 1.22, "화면 · 사진", "8A7F7A");
  [0, 1].forEach(i => {
    const y = 1.68 + i * 2.47;
    card(s, 6.88, y, 5.9, 2.32, "FAF8F7");
    s.addShape(p.ShapeType.roundRect, {
      x: 7.13, y: y + 0.17, w: 5.4, h: 1.72, rectRadius: 0.04,
      fill: { color: "F2EEEC" }, line: { color: LINE, width: 1, dashType: "dash" },
    });
    s.addText("이곳에 사진 또는 화면 캡처를 넣으세요", {
      x: 7.13, y: y + 0.17, w: 5.4, h: 1.72, fontFace: F, fontSize: 12,
      color: HINT, align: "center", valign: "middle", margin: 0,
    });
    s.addText("캡션 — 무엇을 보여주는 화면인지 한 줄", {
      x: 7.13, y: y + 1.95, w: 5.4, h: 0.26, fontFace: F, fontSize: 10.5,
      color: HINT, align: "center", margin: 0,
    });
  });

  /* ── 하단 바 : 향후 계획 ── */
  card(s, 6.88, 6.62, 5.9, 0.62, INK);
  s.addText("향후 계획 :  다음 단계에서 할 일을 한 줄로", {
    x: 7.18, y: 6.72, w: 5.3, h: 0.42, fontFace: F, fontSize: 11.5, bold: true,
    color: "E8DFDB", margin: 0, valign: "middle",
  });

  s.addNotes("[발표 메모] 프로젝트 목적 → 현재 단계 → 성과 수치 → 다음 계획 순으로 30초 내 설명. "
    + "회색 글씨는 모두 교체용 안내문이므로 발표 전 실제 내용으로 바꾸세요.");
});

p.writeFile({ fileName: DIR + "PPT2_팀프로젝트_발표양식.pptx" })
  .then(f => console.log("생성:", f));
