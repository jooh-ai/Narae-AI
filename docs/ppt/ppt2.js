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

// ── 머리글 : 번호 + 프로젝트명(좌측) + 소속·담당자(우측) ──
function head(s, no) {
  s.addShape(p.ShapeType.rect, { x: 0, y: 0, w: 13.33, h: 1.0, fill: { color: INK } });
  s.addText(String(no).padStart(2, "0"), {
    x: 0.45, y: 0.2, w: 0.7, h: 0.6, fontFace: F, fontSize: 26, bold: true,
    color: ORG, margin: 0, valign: "middle",
  });
  // ← 여기에 프로젝트명을 입력
  s.addText("프로젝트명을 입력하세요", {
    x: 1.15, y: 0.2, w: 7.4, h: 0.6, fontFace: F, fontSize: 23, bold: true,
    color: "8E8480", margin: 0, valign: "middle",
  });
  // ← 여기에 소속 / 담당자
  s.addText("소속 : ○○팀", {
    x: 8.7, y: 0.17, w: 4.2, h: 0.32, fontFace: F, fontSize: 12,
    color: "C9BFBB", align: "right", margin: 0, valign: "middle",
  });
  s.addText("담당자 : 홍길동", {
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
    x: x + 0.4, y, w: 2.6, h: 0.34, fontFace: F, fontSize: 13.5, bold: true,
    color: INK, margin: 0, valign: "middle",
  });
  if (hint) s.addText(hint, {
    x: x + 3.05, y, w: 2.85, h: 0.34, fontFace: F, fontSize: 9.5,
    color: HINT, align: "right", margin: 0, valign: "middle",
  });
}
function slot(s, x, y, w, h, lines, size) {
  s.addText(lines.map((v, i) => ({
    text: v, options: { bullet: true, breakLine: i < lines.length - 1 },
  })), {
    x, y, w, h, fontFace: F, fontSize: size || 12, color: HINT,
    paraSpaceAfter: 7, margin: 0, lineSpacing: 15,
  });
}

for (let idx = 0; idx < 5; idx++) {
  const s = p.addSlide();
  s.background = { color: BG };
  head(s, idx + 1);

  /* ══ 좌측 : 목적 ══ */
  secTitle(s, 0.55, 1.18, "목적 — 왜 하는가", RED);
  card(s, 0.55, 1.60, 5.9, 1.62);
  slot(s, 0.9, 1.84, 5.25, 1.2, [
    "해결하려는 문제를 한 줄로",
    "기대 효과 (시간 절감 · 정확도 · 비용 등)",
    "적용 대상 설비 또는 업무 범위",
  ], 12);

  /* ══ 좌측 : 진행 현황 (4단계) ══ */
  secTitle(s, 0.55, 3.40, "진행 현황", ORG, "단계명·색은 수정 가능");
  const steps = ["기획", "개발", "검증", "적용"];
  const tlY = 4.32, x0 = 1.05, gap = 1.62;
  s.addShape(p.ShapeType.line, {
    x: x0, y: tlY, w: gap * (steps.length - 1), h: 0, line: { color: LINE, width: 3 },
  });
  s.addShape(p.ShapeType.line, {     // 완료 구간 — 진척에 맞춰 길이만 조정
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
      x: cx - 0.6, y: tlY - 0.56, w: 1.2, h: 0.24, fontFace: F, fontSize: 9.5, bold: true,
      color: c, align: "center", margin: 0,
    });
    s.addText(t, {
      x: cx - 0.7, y: tlY + 0.22, w: 1.4, h: 0.28, fontFace: F, fontSize: 12, bold: true,
      color: done || now ? INK : "9A908C", align: "center", margin: 0,
    });
  });

  /* ══ 좌측 : 핵심 지표 (무엇을 넣을지 예시 제시) ══ */
  secTitle(s, 0.55, 5.20, "핵심 지표", "8A7F7A", "정량 수치가 있으면 기입");
  card(s, 0.55, 5.62, 5.9, 1.62, TINT);
  const kpi = [
    ["예) 작업시간", "3h → 10분"],
    ["예) 오류 건수", "월 5건 → 0"],
    ["예) 적용 설비", "3 호기"],
  ];
  kpi.forEach(([k, v], i) => {
    const x = 0.9 + i * 1.83;
    s.addText(k, { x, y: 5.82, w: 1.72, h: 0.24, fontFace: F, fontSize: 9.5, color: HINT, margin: 0 });
    s.addText(v, { x, y: 6.06, w: 1.72, h: 0.36, fontFace: F, fontSize: 15, bold: true, color: INK, margin: 0 });
  });
  s.addText("※ 정량 수치가 없으면 정성 효과로 대체 — 예) 수작업 제거, 이력 관리 체계화, 판단 근거 확보", {
    x: 0.9, y: 6.55, w: 5.25, h: 0.56, fontFace: F, fontSize: 9.5, color: "9A908C",
    margin: 0, lineSpacing: 13,
  });

  /* ══ 우측 : 화면·사진 — 정사각형 2칸 나란히 ══ */
  secTitle(s, 6.88, 1.18, "화면 · 사진", "8A7F7A", "정사각형 영역");
  [0, 1].forEach(i => {
    const cx = 6.88 + i * 3.02;
    card(s, cx, 1.60, 2.88, 3.16, "FAF8F7");
    s.addShape(p.ShapeType.roundRect, {          // 2.54 × 2.54 정사각형 자리
      x: cx + 0.17, y: 1.77, w: 2.54, h: 2.54, rectRadius: 0.04,
      fill: { color: "F2EEEC" }, line: { color: LINE, width: 1, dashType: "dash" },
    });
    s.addText("사진 / 화면\n(정사각형)", {
      x: cx + 0.17, y: 1.77, w: 2.54, h: 2.54, fontFace: F, fontSize: 11,
      color: HINT, align: "center", valign: "middle", margin: 0, lineSpacing: 16,
    });
    s.addText("캡션 — 무엇을 보여주는지 한 줄", {
      x: cx + 0.12, y: 4.38, w: 2.64, h: 0.3, fontFace: F, fontSize: 9.5,
      color: HINT, align: "center", margin: 0,
    });
  });

  /* ══ 우측 : 향후 계획 ══ */
  secTitle(s, 6.88, 4.96, "향후 계획", RED, "다음 단계 · 일정");
  card(s, 6.88, 5.38, 5.9, 1.86);
  slot(s, 7.23, 5.62, 5.25, 1.4, [
    "다음 단계에서 할 일",
    "목표 시점 (예: 26년 4분기)",
    "필요한 지원 · 협조 사항",
  ], 12);

  s.addNotes("[발표 메모] 프로젝트명·담당자 → 목적 → 현재 단계 → 핵심 지표 → 향후 계획 순으로 "
    + "30초 내 설명. 회색 글씨는 모두 교체용 안내문이므로 발표 전 실제 내용으로 바꾸세요. "
    + "사진 영역은 정사각형이라 화면 캡처를 넣어도 비율이 뭉개지지 않습니다.");
}

p.writeFile({ fileName: DIR + "PPT2_팀프로젝트_발표양식.pptx" })
  .then(f => console.log("생성:", f));
