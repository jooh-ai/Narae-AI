# 중단된 지점부터 다시 시작하기

토큰이 소진돼 작업이 끊기면, 다음 세션에서 **이 문서만 보고** 이어서 쓸 수 있다.

## 1. 지금 어디까지 됐나

```bash
node docs/ppt/build/build.js --list
```

```
진행  ■■■■□□□□□□□□□□□   3 / 15 장
남음  4, 5, 6, ...        → 다음: 슬라이드 4
```

`BUILD_STATE.json` 이 사실의 근거다. `slides/sNN.js` 파일이 **있으면 done**,
없으면 todo — 상태를 손으로 적지 않으므로 어긋날 일이 없다.

## 2. 읽을 것 (이 순서로, 이것만)

| 순서 | 파일 | 무엇을 얻나 |
|---|---|---|
| 1 | `docs/ppt/build/BUILD_STATE.json` | 다음 장 번호 · 제목 · 섹션 · `pending` 미결 사항 |
| 2 | `docs/ppt/build/theme.js` | 팔레트 · 좌표 상수 `G` · 그리기 도구 `d.*` |
| 3 | `docs/ppt/build/slides/` 중 최근 1~2개 | 장 파일의 작성 관례 |
| 4 | `docs/ppt/PLAN_final.md` §4 / §6 | 그 장의 메시지와 실측 수치 |

계획서 전체를 다시 읽을 필요는 없다. §4(15장 구성)와 §6(차트·표 데이터)만 본다.

## 3. 다음 장 쓰기

`slides/sNN.js` 하나를 만든다. 형식은 항상 같다.

```js
module.exports = (pptx, T, meta) => {
  const { C, G } = T;
  // idx 를 주면 머리글에 목차 명칭(theme.js 의 INDEX)이 자동으로 들어간다.
  // sec 는 그 옆에 붙는 부제다. 표지·목차·시연·Q&A 는 idx 없이 sec 만 준다.
  const { d } = T.shell(pptx, { sec: '모델 선정', idx: 4, step: 4 });
  T.title(d, '첫 행', '둘째 행 *핵심 어절만 강조*');
  T.lead(d, '리드 문장. _회백 강조_ 와 *앰버 강조* 를 쓴다.');
  // ... 본문 (d.zone / d.rect / d.seg / d.plab / d.sub / d.txt / d.big)
  d.hline(G.L, G.RULE2, G.W, C.rule, 1);
  T.foot(d, '이 장의 결론 한 문장. *강조어* 는 앰버.');
};
```

숫자 + 단위는 `d.bigUnit('1.29','MW',x,y,42)` 를 쓴다 — 박스 폭을 자막폭에
맞춰 잡아 주므로 뒤에 붙는 라벨과 겹치지 않는다. 직접 폭을 정할 때는
`T.textW(문자열, px)` 로 계산한다 (verify.py 와 같은 모델).

지킬 것 — 좌표는 **px(1280×720)** 로 쓴다. 활자는 4계급(§5.3.1)에서 고른다.
**차트·막대·게이지는 반드시 `d.zone(...)` 홈 면 위에**, 글은 바탕에 둔다.
종전 방식을 **선**으로 그릴 때는 `C.slateL` + 굵기 2.6 (면은 `C.slate`).

## 4. 붙여서 확인

```bash
python3 docs/ppt/build/refresh_data.py   # 데이터 → 장표 수치 재계산 (데이터 바뀐 뒤에만)
node    docs/ppt/build/build.js          # 있는 장만 붙여 pptx 생성 (항상 열린다)
python3 docs/ppt/build/verify.py         # 기하 검증 — 경계이탈·여백·글자넘침·겹침
```

새 시운전 회차는 `trial.py` 로 넣는다 — `predict`(실측 전) → `record --apply`(실측 후).
가드(IGV 미실시·습도계 이탈)가 여기서 걸린다. 절차는 `docs/ppt/DATA_REFRESH.md` §4.

**수치는 슬라이드에 직접 적지 않는다.** 전부 `deck_data.json` 에서 온다
(`refresh_data.py` 가 도구 코드를 그대로 호출해 만든다). 슬라이드 함수의 네 번째
인자 `D` 가 그 파일이다 — `D.impact.gp.mae` · `D.methods` · `D.bins` · `D.scatter` ·
`D.curves` · `D.commission` · `D.blanket`. 자세한 절차는 `docs/ppt/DATA_REFRESH.md`.

## 5. 커밋

장 2~3개마다 커밋·푸시한다. 끊겨도 잃는 작업이 최대 2~3장이다.

```bash
git add -A docs/ppt && git commit -m "feat(ppt): 슬라이드 N~M" \
  && git push -u origin claude/yirye-capacity-ppt-91eg5n
```

## 6. 18장이 끝나면

1. `python3 docs/ppt/build/verify.py` 통과까지 수정
2. 별도 전면 검토 패스 (계획서 §8 ⑥)
3. 발표자 노트 (`slide.addNotes`)
4. `BUILD_STATE.json` 의 `pending` 항목 처리
