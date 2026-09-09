#!/usr/bin/env python3
"""Teams 공동 편집용 근태 관리 엑셀 생성.

HTML 도구는 브라우저에 저장되어 동시 편집이 되지 않는다. 이 엑셀은 Teams/SharePoint
공동 편집으로 모든 구성원이 동시에 자기 행을 고칠 수 있고, 30% 판정이 수식으로 자동
계산된다. 근무 유형은 드롭다운으로만 고를 수 있어 오입력이 원천 차단된다.

    python worktime/build_xlsx.py [출력경로]
"""
import sys
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import CellIsRule, FormulaRule

FONT = '맑은 고딕'
NAV, INK, DIM = '1C4E80', '16181D', '6B7280'
OK_BG, BAD_BG, WARN_BG, HEAD_BG, OFF_BG = 'E6F4EC', 'FBEAE9', 'FDF3DD', 'EEF1F5', 'F0F1F3'
THIN = Side(style='thin', color='D8DCE1')
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

# ── 근무 유형: (코드, 30% 충족, 휴가 인정시간, 설명) ──────────────────────
CODES = [
    ('8시간',     1, 0, '07:30~16:30 · 08:00~17:00 · 08:30~17:30 중 하나 — 30% 인원에 포함'),
    ('선택근로',  0, 0, '8시간 미만이거나 8시간을 넘는 선택적 근로 — 30% 미충족'),
    ('오전반차',  0, 4, '08:00~13:00 또는 08:30~13:30 휴가 후 13:00 / 13:30 출근'),
    ('오후반차',  0, 4, '오전 근무 후 점심 이후부터 휴가'),
    ('오전반반차',0, 2, '08:30~10:30 휴가 후 10:30 출근'),
    ('오후반반차',0, 2, '15:30까지 근무 후 15:30~17:30 휴가'),
    ('연차',      0, 8, '종일 휴가'),
    ('출장',      0, 0, '사외 활동 — 8시간이어도 30% 미충족'),
    ('교육',      0, 0, '사외 활동 — 30% 미충족'),
    ('건강검진',  0, 4, '반차 4시간으로 인정'),
    ('기타',      0, 0, '그 밖의 사유 — 메모에 사유를 적으세요'),
    ('휴직',      0, 0, '30% 모수에서 제외'),
]
MISS = [c for c, ok, *_ in CODES if not ok and c != '휴직']   # 30% 미충족 코드

ROSTER = [
    ('김동환', '발전운영팀', '발전팀장', '팀장',   'A', ''),
    ('고재민', '정비기술팀', '정비팀장', '팀장',   'A', ''),
    ('임태균', '발전운영팀', '발전지원', '파트장', 'A', ''),
    ('정병철', '정비기술팀', '기계',     '파트장', 'A', ''),
    ('민준홍', '정비기술팀', '전기',     '파트장', 'A', ''),
    ('한승백', '정비기술팀', '제어',     '파트장', 'A', ''),
    ('박상호', '정비기술팀', '기계',     '구성원', 'B', ''),
    ('최규석', '정비기술팀', '기계',     '구성원', 'B', ''),
    ('김성진', '정비기술팀', '기계',     '구성원', 'B', ''),
    ('윤병권', '정비기술팀', '기계',     '구성원', 'B', ''),
    ('정상우', '정비기술팀', '기계',     '구성원', 'B', ''),
    ('김형준', '정비기술팀', '전기',     '구성원', 'B', ''),
    ('손현덕', '정비기술팀', '전기',     '구성원', 'B', ''),
    ('오승원', '정비기술팀', '전기',     '구성원', 'B', ''),
    ('주현',   '정비기술팀', '제어',     '구성원', 'B', ''),
    ('조주형', '정비기술팀', '제어',     '구성원', 'B', ''),
    ('양종수', '정비기술팀', '정비지원', '구성원', 'B', ''),
    ('강인성', '정비기술팀', '정비지원', '구성원', 'B', ''),
    ('권오선', '정비기술팀', '정비지원', '구성원', 'B', ''),
    ('정소망', '정비기술팀', '정비지원', '구성원', 'B', ''),
    ('윤승현', '정비기술팀', '정비지원', '구성원', 'B', 'Y'),   # 육아휴직
    ('양시웅', '발전운영팀', '발전지원', '구성원', 'C', ''),
    ('한준우', '발전운영팀', '발전지원', '구성원', 'C', ''),
    ('권민중', '발전운영팀', '발전지원', '구성원', 'C', ''),
]
HOLIDAYS = [
    ('2026-01-01', '신정'), ('2026-02-16', '설날 연휴'), ('2026-02-17', '설날'),
    ('2026-02-18', '설날 연휴'), ('2026-03-01', '삼일절'),
    ('2026-03-02', '삼일절 대체공휴일'), ('2026-05-01', '근로자의 날'),
    ('2026-05-05', '어린이날'), ('2026-05-24', '부처님오신날'),
    ('2026-05-25', '부처님오신날 대체공휴일'), ('2026-06-06', '현충일'),
    ('2026-08-15', '광복절'), ('2026-08-17', '광복절 대체공휴일'),
    ('2026-09-24', '추석 연휴'), ('2026-09-25', '추석'), ('2026-09-26', '추석 연휴'),
    ('2026-10-03', '개천절'), ('2026-10-05', '개천절 대체공휴일'),
    ('2026-10-09', '한글날'), ('2026-10-13', '회사 창립기념일'),
    ('2026-12-25', '성탄절'),
]

R0, R1 = 8, 8 + len(ROSTER) - 1          # 구성원 행 범위
LEAD0, LEAD1 = 8, 13                     # 직책자(A그룹) 행 범위
D0, D1 = 4, 34                           # 일자 열 범위 (D ~ AH)
DL, DR = get_column_letter(D0), get_column_letter(D1)


def style(c, *, bold=False, size=10, color=INK, fill=None, align='center', border=True,
          wrap=False):
    c.font = Font(name=FONT, bold=bold, size=size, color=color)
    if fill:
        c.fill = PatternFill('solid', fgColor=fill)
    c.alignment = Alignment(horizontal=align, vertical='center', wrap_text=wrap)
    if border:
        c.border = BOX
    return c


def build(path):
    wb = Workbook()

    # ══ 사용안내 ═══════════════════════════════════════════════════════
    gd = wb.active
    gd.title = '사용안내'
    lines = [
        ('위례 근태 관리 — Teams 공동 편집용', 14, True, NAV),
        ('', 10, False, INK),
        ('이 파일은 Teams(SharePoint)에 두고 모든 구성원이 동시에 편집합니다. '
         '각자 자기 행만 고치면 되고, 30% 판정은 자동으로 계산됩니다.', 10, False, INK),
        ('', 10, False, INK),
        ('1. 「근태」 시트 — 자기 이름 행에서 해당 날짜 칸을 고릅니다.', 11, True, NAV),
        ('   · 빈칸이 8시간 근무입니다. 8시간을 채우는 날은 아무것도 넣지 마세요.', 10, False, INK),
        ('   · 8시간을 못 채우는 날만 드롭다운에서 사유를 고릅니다.', 10, False, INK),
        ('   · 노란 칸(B1·B2)에 연·월을 넣으면 날짜와 요일이 자동으로 바뀝니다.', 10, False, INK),
        ('   · 맨 아래 판정 행이 빨갛게 되면 그날 30%가 미달입니다 — 서로 조율하세요.', 10, False, INK),
        ('', 10, False, INK),
        ('2. 「OT」 시트 — 날짜별 OT 시간을 시간 단위로 넣습니다 (1시간 45분 = 1.75).', 11, True, NAV),
        ('   · 월 합계와 잔여가 자동 계산됩니다. 기본 가능시간은 노란 칸에 직접 넣으세요.', 10, False, INK),
        ('   · 휴가를 쓰면 그 시간만큼 OT 가능시간이 자동으로 늘어납니다.', 10, False, INK),
        ('', 10, False, INK),
        ('3. 「명부」·「공휴일」 — 인원 변동과 휴일이 바뀔 때만 고칩니다.', 11, True, NAV),
        ('', 10, False, INK),
        ('근무 시각 조합이 규칙에 맞는지 확인하려면', 11, True, NAV),
        ('worktime/index.html (근태·초과근무 관리 도구) 의 「규칙 · 검증기」 탭을 쓰세요. '
         '코어타임·휴게시간·반차 배치 규칙을 시각 단위로 검증해 줍니다.', 10, False, INK),
        ('', 10, False, INK),
        ('30% 판정 기준', 11, True, NAV),
        ('필요 인원 = 활성 인원(휴직 제외) × 30%, 올림. 직책자(팀장·파트장) 중 1명 이상이 '
         '8시간에 포함되어야 합니다. 파트 최소 인원 조건은 팀장 승인 시 유예됩니다.', 10, False, INK),
    ]
    for i, (txt, sz, bold, col) in enumerate(lines, start=1):
        c = gd.cell(row=i, column=1, value=txt)
        c.font = Font(name=FONT, size=sz, bold=bold, color=col)
        c.alignment = Alignment(vertical='center', wrap_text=False)
    gd.column_dimensions['A'].width = 110

    # ══ 코드 ═══════════════════════════════════════════════════════════
    cd = wb.create_sheet('코드')
    for j, h in enumerate(['근무 유형', '30% 충족', '휴가 인정(h)', '설명'], start=1):
        style(cd.cell(row=1, column=j, value=h), bold=True, fill=HEAD_BG, size=9)
    for i, (code, ok, lv, desc) in enumerate(CODES, start=2):
        style(cd.cell(row=i, column=1, value=code), align='left')
        style(cd.cell(row=i, column=2, value=ok))
        style(cd.cell(row=i, column=3, value=lv))
        style(cd.cell(row=i, column=4, value=desc), align='left', size=9, color=DIM)
    style(cd.cell(row=1, column=6, value='30% 미충족 코드'), bold=True, fill=HEAD_BG, size=9)
    for i, code in enumerate(MISS, start=2):
        style(cd.cell(row=i, column=6, value=code), align='left')
    style(cd.cell(row=1, column=8, value='요일'), bold=True, fill=HEAD_BG, size=9)
    for i, d in enumerate(['일', '월', '화', '수', '목', '금', '토'], start=2):
        style(cd.cell(row=i, column=8, value=d))
    for col, w in zip('ABCDEFGH', [13, 9, 11, 62, 3, 15, 3, 6]):
        cd.column_dimensions[col].width = w

    # ══ 명부 ═══════════════════════════════════════════════════════════
    rs = wb.create_sheet('명부')
    for j, h in enumerate(['이름', '팀', '파트', '직책', '그룹', '휴직'], start=1):
        style(rs.cell(row=1, column=j, value=h), bold=True, fill=HEAD_BG, size=9)
    for i, row in enumerate(ROSTER, start=2):
        for j, v in enumerate(row, start=1):
            style(rs.cell(row=i, column=j, value=v), align='left' if j <= 4 else 'center')
    style(rs.cell(row=len(ROSTER) + 3, column=1, value='활성 인원'), bold=True, align='left')
    style(rs.cell(row=len(ROSTER) + 3, column=2,
                  value=f'=COUNTA(A2:A{len(ROSTER)+1})-COUNTIF(F2:F{len(ROSTER)+1},"Y")'),
          bold=True, fill=OK_BG)
    style(rs.cell(row=len(ROSTER) + 4, column=1, value='30% 필요 인원'), bold=True, align='left')
    style(rs.cell(row=len(ROSTER) + 4, column=2,
                  value=f'=ROUNDUP(B{len(ROSTER)+3}*0.3,0)'), bold=True, fill=OK_BG)
    rs.cell(row=len(ROSTER) + 6, column=1,
            value='휴직 열에 Y 를 넣으면 30% 모수에서 빠집니다. '
                  '순서를 바꾸면 「근태」·「OT」 시트의 이름도 함께 바뀝니다.').font = \
        Font(name=FONT, size=9, color=DIM)
    for col, w in zip('ABCDEF', [10, 12, 10, 8, 6, 6]):
        rs.column_dimensions[col].width = w

    # ══ 공휴일 ═════════════════════════════════════════════════════════
    hs = wb.create_sheet('공휴일')
    for j, h in enumerate(['날짜', '명칭'], start=1):
        style(hs.cell(row=1, column=j, value=h), bold=True, fill=HEAD_BG, size=9)
    for i, (d, n) in enumerate(HOLIDAYS, start=2):
        c = hs.cell(row=i, column=1, value=d)
        style(c, align='center')
        c.number_format = 'yyyy-mm-dd'
        style(hs.cell(row=i, column=2, value=n), align='left')
    hs.cell(row=len(HOLIDAYS) + 3, column=1,
            value='날짜는 반드시 날짜 형식(2027-01-01)으로 넣으세요. '
                  '설날·추석·부처님오신날은 음력이라 매년 확인이 필요합니다.').font = \
        Font(name=FONT, size=9, color=DIM)
    hs.column_dimensions['A'].width = 14
    hs.column_dimensions['B'].width = 26

    _sheet_attend(wb)
    _sheet_ot(wb)
    wb.save(path)
    return path


def _day_header(ws, title):
    """근태 · OT 시트 공통 머리 — 연·월 입력과 날짜·요일·휴일 행."""
    style(ws.cell(row=1, column=1, value='연'), bold=True, align='right', border=False)
    c = ws.cell(row=1, column=2, value=2026)
    style(c, bold=True, fill='FFFF00')
    style(ws.cell(row=2, column=1, value='월'), bold=True, align='right', border=False)
    c = ws.cell(row=2, column=2, value=9)
    style(c, bold=True, fill='FFFF00')
    t = ws.cell(row=1, column=4, value=title)
    t.font = Font(name=FONT, bold=True, size=13, color=NAV)
    ws.cell(row=2, column=4, value='노란 칸에 연·월을 넣으면 날짜와 요일이 자동으로 바뀝니다').font = \
        Font(name=FONT, size=9, color=DIM)

    for col in range(D0, D1 + 1):
        L = get_column_letter(col)
        style(ws.cell(row=4, column=col,
                      value=f'=IF(MONTH(DATE($B$1,$B$2,COLUMN()-3))<>$B$2,"",COLUMN()-3)'),
              bold=True, fill=HEAD_BG, size=9)
        style(ws.cell(row=5, column=col,
                      value=f'=IF({L}$4="","",INDEX(코드!$H$2:$H$8,'
                            f'WEEKDAY(DATE($B$1,$B$2,{L}$4))))'),
              fill=HEAD_BG, size=9, color=DIM)
        style(ws.cell(row=6, column=col,
                      value=f'=IF({L}$4="","",IF(OR(WEEKDAY(DATE($B$1,$B$2,{L}$4),2)>5,'
                            f'COUNTIF(공휴일!$A$2:$A$400,DATE($B$1,$B$2,{L}$4))>0),"휴일",""))'),
              fill=HEAD_BG, size=8, color=DIM)
        ws.column_dimensions[L].width = 9.5
    for col, w in zip('ABC', [10, 10, 6]):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = 'D8'


def _member_rows(ws):
    """명부 시트를 참조하는 이름·파트·그룹 열."""
    for j, h in enumerate(['이름', '파트', '그룹'], start=1):
        style(ws.cell(row=7, column=j, value=h), bold=True, fill=HEAD_BG, size=9)
    for i in range(len(ROSTER)):
        r, m = R0 + i, 2 + i
        style(ws.cell(row=r, column=1, value=f'=IF(명부!A{m}="","",명부!A{m})'),
              bold=True, align='left', size=9.5)
        style(ws.cell(row=r, column=2, value=f'=IF(명부!C{m}="","",명부!C{m})'),
              align='left', size=9, color=DIM)
        style(ws.cell(row=r, column=3, value=f'=IF(명부!E{m}="","",명부!E{m})'),
              size=9, color=DIM)


def _sheet_attend(wb):
    ws = wb.create_sheet('근태', 1)
    _day_header(ws, '근태 — 빈칸이 8시간 근무입니다. 못 채우는 날만 사유를 고르세요')
    _member_rows(ws)

    for i in range(len(ROSTER)):
        for col in range(D0, D1 + 1):
            style(ws.cell(row=R0 + i, column=col), size=9)

    dv = DataValidation(type='list', formula1=f'=코드!$A$2:$A${len(CODES)+1}',
                        allow_blank=True, showDropDown=False)
    dv.error = '드롭다운에 있는 근무 유형만 넣을 수 있습니다.'
    dv.errorTitle = '허용되지 않는 값'
    dv.prompt = '빈칸 = 8시간 근무. 8시간을 못 채우는 날만 사유를 고르세요.'
    dv.promptTitle = '근무 유형'
    ws.add_data_validation(dv)
    dv.add(f'{DL}{R0}:{DR}{R1}')

    active = f'명부!$B${len(ROSTER)+3}'
    miss   = f'코드!$F$2:$F${len(MISS)+1}'
    leads  = f'COUNTIF(명부!$E$2:$E${len(ROSTER)+1},"A")'
    labels = [(33, '8시간 인원'), (34, f'필요 인원 (30%)'), (35, '판정'), (36, '직책자 8시간')]
    for r, lab in labels:
        style(ws.cell(row=r, column=1, value=lab), bold=True, align='left',
              fill=HEAD_BG, size=9)
        style(ws.cell(row=r, column=2), fill=HEAD_BG)
        style(ws.cell(row=r, column=3), fill=HEAD_BG)
    for col in range(D0, D1 + 1):
        L = get_column_letter(col)
        alive = f'({active}-COUNTIF({L}${R0}:{L}${R1},"휴직"))'
        style(ws.cell(row=33, column=col,
                      value=f'=IF({L}$6="휴일","",{alive}'
                            f'-SUMPRODUCT(COUNTIF({L}${R0}:{L}${R1},{miss})))'),
              bold=True, fill=HEAD_BG, size=9)
        style(ws.cell(row=34, column=col,
                      value=f'=IF({L}$6="휴일","",ROUNDUP({alive}*0.3,0))'),
              fill=HEAD_BG, size=9, color=DIM)
        style(ws.cell(row=35, column=col,
                      value=f'=IF({L}$6="휴일","",IF({L}33>={L}34,"충족","미달"))'),
              bold=True, size=9)
        style(ws.cell(row=36, column=col,
                      value=f'=IF({L}$6="휴일","",{leads}-COUNTIF({L}${LEAD0}:{L}${LEAD1},"휴직")'
                            f'-SUMPRODUCT(COUNTIF({L}${LEAD0}:{L}${LEAD1},{miss})))'),
              size=9)

    grid = f'{DL}{R0}:{DR}{R1}'
    ws.conditional_formatting.add(grid, FormulaRule(
        formula=[f'{DL}$6="휴일"'], fill=PatternFill('solid', fgColor=OFF_BG), stopIfTrue=False))
    ws.conditional_formatting.add(grid, FormulaRule(
        formula=[f'{DL}{R0}<>""'], fill=PatternFill('solid', fgColor=WARN_BG)))
    ws.conditional_formatting.add(f'{DL}35:{DR}35', CellIsRule(
        operator='equal', formula=['"미달"'],
        fill=PatternFill('solid', fgColor=BAD_BG),
        font=Font(name=FONT, bold=True, color='B3261E')))
    ws.conditional_formatting.add(f'{DL}35:{DR}35', CellIsRule(
        operator='equal', formula=['"충족"'],
        fill=PatternFill('solid', fgColor=OK_BG),
        font=Font(name=FONT, bold=True, color='0F7B4F')))
    ws.conditional_formatting.add(f'{DL}36:{DR}36', CellIsRule(
        operator='lessThan', formula=['1'], fill=PatternFill('solid', fgColor=WARN_BG)))

    ws.cell(row=38, column=1,
            value='판정이 「미달」인 날은 서로 조율해 8시간 근무 인원을 채우세요. '
                  '직책자 8시간이 0이면 팀장·파트장 중 한 명이 8시간을 맡아야 합니다. '
                  '근무 시각 조합이 규칙에 맞는지는 worktime/index.html 의 검증기로 확인하세요.').font = \
        Font(name=FONT, size=9, color=DIM)


def _sheet_ot(wb):
    ws = wb.create_sheet('OT', 2)
    _day_header(ws, 'OT — 날짜별 초과근로 시간 (1시간 45분 = 1.75)')
    _member_rows(ws)

    tot, base, plus, left = D1 + 1, D1 + 2, D1 + 3, D1 + 4
    for col, h in [(tot, '월 합계'), (base, '기본 가능시간'), (plus, '휴가 가산'), (left, '잔여')]:
        style(ws.cell(row=7, column=col, value=h), bold=True, fill=HEAD_BG, size=9)
        ws.column_dimensions[get_column_letter(col)].width = 12
    for i in range(len(ROSTER)):
        r = R0 + i
        for col in range(D0, D1 + 1):
            c = style(ws.cell(row=r, column=col), size=9)
            c.number_format = '0.##'
        style(ws.cell(row=r, column=tot, value=f'=SUM({DL}{r}:{DR}{r})'),
              bold=True, fill=HEAD_BG, size=9).number_format = '0.##'
        style(ws.cell(row=r, column=base, value=None), fill='FFFF00', size=9).number_format = '0.##'
        a = f'근태!{DL}{r}:{DR}{r}'
        style(ws.cell(row=r, column=plus,
                      value=f'=COUNTIF({a},"연차")*8+(COUNTIF({a},"오전반차")+'
                            f'COUNTIF({a},"오후반차")+COUNTIF({a},"건강검진"))*4+'
                            f'(COUNTIF({a},"오전반반차")+COUNTIF({a},"오후반반차"))*2'),
              size=9, color=DIM).number_format = '0.##'
        style(ws.cell(row=r, column=left,
                      value=f'={get_column_letter(base)}{r}+{get_column_letter(plus)}{r}'
                            f'-{get_column_letter(tot)}{r}'),
              bold=True, size=9).number_format = '0.##'
    lc = get_column_letter(left)
    ws.conditional_formatting.add(f'{lc}{R0}:{lc}{R1}', CellIsRule(
        operator='lessThan', formula=['0'], fill=PatternFill('solid', fgColor=BAD_BG),
        font=Font(name=FONT, bold=True, color='B3261E')))
    ws.cell(row=R1 + 3, column=1,
            value='노란 칸(기본 가능시간)에 사내 HR 시스템의 그 달 OT 가능 시간을 넣으세요. '
                  '휴가를 쓰면 그 시간만큼 가능시간이 자동으로 늘어납니다. '
                  'OT 는 분 단위로 신청하므로 1시간 45분은 1.75 로 넣습니다.').font = \
        Font(name=FONT, size=9, color=DIM)


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else 'worktime/위례_근태관리.xlsx'
    print(build(out))
