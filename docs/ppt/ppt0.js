// PPT-0 : 표지 + 목차 (2장) — PPT-1 과 동일한 SK 브랜드 양식
// 프로젝트명 : 미리내 (MIRINAE) — "미리 내다보는 공급가능용량"
const pptx = require("pptxgenjs");
const p = new pptx();
p.layout = "LAYOUT_WIDE";              // 13.33 x 7.5 in
p.author = "발전운영팀";
p.title = "미리내 (MIRINAE)";

const RED = "EA002C", ORG = "F47725", INK = "1F1A18", GRAY = "6B625E";
const LINE = "E8E0DC", BG = "FFFFFF", TINT = "FFF4EE", HINT = "9A908C";
const F = "맑은 고딕";
const DIR = __dirname + "/";

// ── 여기만 고치면 됨 ──────────────────────────────────────────────
const NAME    = "미리내";
const NAME_EN = "M I R I N A E";
const TAGLINE = "미리 내다보는 공급가능용량";
const SUBTITLE= "전력시장 입찰 공급가능용량 자동산정 시스템";
const PLANT   = "위례열병합발전소";
const TEAM    = "발전운영팀";
const OWNER   = "○ ○ ○";
const DATE    = "2026. 08";
// ────────────────────────────────────────────────────────────────

/* ══════════════════ 1장 : 표지 ══════════════════ */
const s1 = p.addSlide();
s1.background = { color: INK };

// 좌측 SK 컬러 바 (레드 + 오렌지)
s1.addShape(p.ShapeType.rect, { x: 0,    y: 0, w: 0.15, h: 7.5, fill: { color: RED } });
s1.addShape(p.ShapeType.rect, { x: 0.15, y: 0, w: 0.15, h: 7.5, fill: { color: ORG } });

// 우측 궤도 악센트 — 얇은 원 2개 + 은은한 원 1개 + 붉은 점
//   "미리 내다본다"를 궤도(예측 경로) 이미지로 표현. 채운 도형을 크게 쓰면
//   덩어리처럼 보여서 외곽선 위주로 구성한다.
const ring = (x, y, d, color, w) => s1.addShape(p.ShapeType.ellipse, {
  x, y, w: d, h: d, fill: { color: INK, transparency: 100 },
  line: { color, width: w },
});
ring(7.95, 0.35, 8.10, "3A322F", 1.25);
ring(9.35, 1.75, 5.30, "4E4340", 1.25);
s1.addShape(p.ShapeType.ellipse, {
  x: 10.30, y: 2.70, w: 3.40, h: 3.40, fill: { color: ORG, transparency: 92 },
});
s1.addShape(p.ShapeType.ellipse, {           // 궤도 위의 점
  x: 11.86, y: 1.62, w: 0.26, h: 0.26, fill: { color: RED },
});

// 눈썹 문구
s1.addText(`${PLANT}  ·  ${TEAM}`, {
  x: 1.05, y: 1.42, w: 8.0, h: 0.34, fontFace: F, fontSize: 13, bold: true,
  color: ORG, charSpacing: 2, margin: 0, valign: "middle",
});

// 프로젝트명
s1.addText(NAME, {
  x: 1.0, y: 1.90, w: 8.0, h: 1.34, fontFace: F, fontSize: 66, bold: true,
  color: "FFFFFF", margin: 0, valign: "middle",
});
s1.addText(NAME_EN, {
  x: 1.05, y: 3.24, w: 8.0, h: 0.40, fontFace: F, fontSize: 17,
  color: "C9BFBB", charSpacing: 3, margin: 0, valign: "middle",
});

// 구분선
s1.addShape(p.ShapeType.rect, { x: 1.05, y: 3.86, w: 2.6, h: 0.045, fill: { color: RED } });

// 태그라인 + 부제
s1.addText(TAGLINE, {
  x: 1.0, y: 4.10, w: 8.4, h: 0.56, fontFace: F, fontSize: 25, bold: true,
  color: "FFFFFF", margin: 0, valign: "middle",
});
s1.addText(SUBTITLE, {
  x: 1.05, y: 4.70, w: 8.4, h: 0.36, fontFace: F, fontSize: 14,
  color: "A79D99", margin: 0, valign: "middle",
});

// 하단 정보 (소속 / 담당자 / 보고일)
s1.addShape(p.ShapeType.rect, { x: 1.05, y: 5.95, w: 6.9, h: 0.02, fill: { color: "3D3532" } });
[["소 속", TEAM], ["담 당 자", OWNER], ["보 고 일", DATE]].forEach(([k, v], i) => {
  const x = 1.05 + i * 2.35;
  s1.addText(k, {
    x, y: 6.20, w: 2.1, h: 0.26, fontFace: F, fontSize: 10,
    color: ORG, charSpacing: 1, margin: 0, valign: "middle",
  });
  s1.addText(v, {
    x, y: 6.46, w: 2.1, h: 0.34, fontFace: F, fontSize: 15, bold: true,
    color: "FFFFFF", margin: 0, valign: "middle",
  });
});

s1.addNotes(
  "[표지] 프로젝트명 '미리내'는 은하수를 뜻하는 순우리말이면서, "
  + "'미리 내다본다'는 뜻을 함께 담았습니다. 기온만 알면 내일 낼 수 있는 출력을 미리 "
  + "내다보고 입찰한다 — 이 도구가 하는 일 그대로입니다.\n"
  + "담당자 이름과 보고일은 파일 상단 상수(OWNER, DATE)에서 한 번에 바꿀 수 있습니다."
);

/* ══════════════════ 2장 : 목차 ══════════════════ */
const s2 = p.addSlide();
s2.background = { color: BG };

// 머리글 — PPT-1 과 동일한 검정 바
s2.addShape(p.ShapeType.rect, { x: 0, y: 0, w: 13.33, h: 1.0, fill: { color: INK } });
s2.addText("목차", {
  x: 0.75, y: 0.2, w: 3.0, h: 0.6, fontFace: F, fontSize: 23, bold: true,
  color: "FFFFFF", margin: 0, valign: "middle",
});
s2.addText("CONTENTS", {
  x: 1.85, y: 0.28, w: 3.0, h: 0.44, fontFace: F, fontSize: 12,
  color: ORG, charSpacing: 3, margin: 0, valign: "middle",
});
s2.addText(`${NAME}  ·  ${TEAM}`, {
  x: 8.7, y: 0.2, w: 4.2, h: 0.6, fontFace: F, fontSize: 12,
  color: "C9BFBB", align: "right", margin: 0, valign: "middle",
});

// 목차 6칸 — 2열 × 3행 (내용은 비워 둠)
const COLX = [0.75, 6.98], ROWY = [1.85, 3.65, 5.45];
const BOXW = 5.60, BOXH = 1.52;
for (let i = 0; i < 6; i++) {
  const x = COLX[i % 2], y = ROWY[Math.floor(i / 2)];
  const no = String(i + 1).padStart(2, "0");

  // 번호 타일
  s2.addShape(p.ShapeType.roundRect, {
    x, y, w: 0.92, h: 0.92, rectRadius: 0.08, fill: { color: TINT },
    line: { color: "F6D9C8", width: 1 },
  });
  s2.addText(no, {
    x, y, w: 0.92, h: 0.92, fontFace: F, fontSize: 26, bold: true,
    color: i < 3 ? RED : ORG, align: "center", valign: "middle", margin: 0,
  });

  // 제목 자리 (← 여기에 목차 항목을 입력)
  s2.addText("제목을 입력하세요", {
    x: x + 1.16, y: y + 0.04, w: BOXW - 1.16, h: 0.46, fontFace: F, fontSize: 17,
    bold: true, color: HINT, margin: 0, valign: "middle",
  });
  // 밑줄
  s2.addShape(p.ShapeType.rect, {
    x: x + 1.16, y: y + 0.56, w: BOXW - 1.16, h: 0.015, fill: { color: LINE },
  });
  // 한 줄 설명 자리 (선택)
  s2.addText("한 줄 설명 — 필요 없으면 지우세요", {
    x: x + 1.16, y: y + 0.62, w: BOXW - 1.16, h: 0.30, fontFace: F, fontSize: 11,
    color: "C4BAB6", margin: 0, valign: "middle",
  });
}

// 하단 바
s2.addShape(p.ShapeType.rect, { x: 0, y: 7.30, w: 13.33, h: 0.20, fill: { color: INK } });
s2.addShape(p.ShapeType.rect, { x: 0, y: 7.30, w: 3.2, h: 0.20, fill: { color: ORG } });

s2.addNotes(
  "[목차] 회색 글씨는 모두 교체용 안내문입니다. 6칸이 남으면 빈 칸의 도형·글상자를 "
  + "선택해 삭제하면 되고, 더 필요하면 한 칸을 복사해 붙여 넣으세요.\n"
  + "번호 타일 색은 앞 3개 레드(EA002C), 뒤 3개 오렌지(F47725)로 되어 있습니다."
);

p.writeFile({ fileName: DIR + "PPT0_미리내_표지_목차.pptx" })
  .then(f => console.log("생성:", f));
