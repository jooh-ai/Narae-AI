/* v3 가 쓰는 그림 파일 이름. 한 곳에 모아 둔다 — 담당자가 캡처를 다시 올리면
   파일명이 그대로이므로 이 표만 맞으면 장표가 따라온다.

   엑셀 캡처는 담당자가 직접 찍어 올린 실물이다(2026-09-16). 파일명에 어느
   단계인지 적혀 있어 그대로 둔다. `xl1_gap` 만 우리가 만든 것인데, 실적 시트가
   가로 20열이 넘어 장표에서 글자가 안 읽히므로 **같은 파일에서 세 열만 오려**
   나란히 붙인 것이다(`crop_shot.py`). 픽셀은 원본 그대로다.            */
'use strict';
module.exports = {
  xl1:     '엑셀1-1_날짜, 시간 입력 후(RiMS 데이터 가져오기).png',
  xl1log:  '엑셀1-2_Base Load Test 실적 정리.png',
  xl2:     '엑셀2-1_G열 대기압 입력 후 온도별 이론값 생성.png',
  xl2blt:  '엑셀2-2_IGV Turn up 적용 및, 테스트 온도 지점의 실제 출력과 이론값 비교하여 BTL(보정값) 적용.png',
  xl3:     'xl_profile.png',
  xl1gap:  'xl1_gap.png',
  toolWin: 'tool_window.png',
  toolIn:  'tool_input.png',
  toolCur: 'tool_curve.png',
  toolOut: 'tool_out.png',   // 위 절반 — 출력 곡선 (도구 화면에서 오린 것)
  toolGap: 'tool_gap.png',   // 아래 절반 — 온도별 차이와 실측점
  toolMod: 'tool_models.png',
  toolStatus: 'tool_status.png',
  /* 2026-09-17 추가 — 회신 "시뮬레이션 기능이나 loocv 기능도 캡쳐해서
     흐름에 맞게 넣으면 좋겠다". `ui_shots.py` 가 오프스크린으로 뽑았고,
     장표에서 글자가 읽히도록 `crop_shot.py` 로 필요한 부분만 오렸다. */
  toolSim:   'tool_sim.png',        // 출력 시뮬레이션 탭 (조건 넣고 실행한 화면)
  toolSimOut:'tool_sim_out.png',    // 그 결과 칸만 — 계산이 이어지는 자리
  toolLoocv: 'tool_loocv_top.png',  // 모델 선정 탭의 교차검증 표 (상위 3개 + 판정)
  toolList:'tool_list.png',
  ci:      'ci_narae.png',
};
