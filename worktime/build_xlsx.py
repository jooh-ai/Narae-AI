#!/usr/bin/env python3
"""Teams · OneDrive 공동 편집용 근태 관리 엑셀 생성.

HTML 도구는 각자 브라우저에 저장되어 동시 편집이 되지 않는다. 이 엑셀은 Office 형식이라
Excel Online / 자동 저장 상태의 Excel 데스크톱에서 **모든 구성원이 동시에** 편집할 수 있다.

핵심은 규칙을 만족하는 근무 조합이 106가지로 유한하다는 것이다(worktime/gen_combos.js 가
HTML 의 규칙 엔진에서 직접 뽑는다). 드롭다운을 그 106가지로 제한하면

  · 규칙 위반 입력이 원천 차단되고
  · 실근로 · 휴가 · 30% 충족 여부를 조회만 하면 되므로
  · 30% 판정 · 월 총량 · OT 잔여 · 주별 근로시간이 전부 수식으로 계산된다

즉 엑셀에서도 HTML 과 같은 규칙으로 판정한다.

    node worktime/gen_combos.js > worktime/data/combos.json
    python worktime/build_xlsx.py [출력경로]
"""
import json
import subprocess
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Protection, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

HERE = Path(__file__).resolve().parent
FONT = '맑은 고딕'
NAV, INK, DIM = '1C4E80', '16181D', '6B7280'
OK_BG, BAD_BG, WARN_BG = 'E6F4EC', 'FBEAE9', 'FDF3DD'
HEAD_BG, OFF_BG, IN_BG, CAND_BG = 'EEF1F5', 'F0F1F3', 'FFFDE7', 'FFF3B0'
THIN = Side(style='thin', color='D8DCE1')
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

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

N = len(ROSTER)
R0, R1 = 8, 8 + N - 1            # 구성원 행
LEAD0, LEAD1 = 8, 13             # 직책자(A그룹) 행
M0, M1 = 2, 1 + N                # 명부 행
D0, D1 = 4, 34                   # 일자 열 (D ~ AH)
DL, DR = get_column_letter(D0), get_column_letter(D1)
WEEKS = 6                        # 한 달에 걸치는 최대 주 수
ROW_SUM = {'인원': 33, '필요': 34, '판정': 35, '직책자': 36}


def load_combos():
    p = HERE / 'data' / 'combos.json'
    try:
        out = subprocess.run(['node', str(HERE / 'gen_combos.js')],
                             capture_output=True, text=True, check=True, timeout=120)
        rows = json.loads(out.stdout)
        p.parent.mkdir(exist_ok=True)
        p.write_text(json.dumps(rows, ensure_ascii=False, indent=1))
        return rows, '규칙 엔진에서 새로 생성'
    except Exception as err:                       # node 가 없으면 저장된 목록으로
        if not p.exists():
            raise SystemExit(f'조합 목록을 만들 수 없습니다: {err}')
        return json.loads(p.read_text()), '저장된 목록 사용'


def st(c, *, bold=False, size=10, color=INK, fill=None, align='center', border=True,
       fmt=None, locked=True):
    c.font = Font(name=FONT, bold=bold, size=size, color=color)
    if fill:
        c.fill = PatternFill('solid', fgColor=fill)
    c.alignment = Alignment(horizontal=align, vertical='center')
    if border:
        c.border = BOX
    if fmt:
        c.number_format = fmt
    c.protection = Protection(locked=locked)
    return c


def sheet_codes(wb, combos):
    """근무 조합표 — 드롭다운 목록이자 모든 계산의 조회 원천."""
    ws = wb.create_sheet('코드')
    head = ['코드', '유형', '근무 시각', '실근로(h)', '휴가(h)', '30%충족', '휴가 블록', '구분']
    for j, h in enumerate(head, start=1):
        st(ws.cell(row=1, column=j, value=h), bold=True, fill=HEAD_BG, size=9)
    for i, r in enumerate(combos, start=2):
        st(ws.cell(row=i, column=1, value=r['code']), align='left', size=9)
        st(ws.cell(row=i, column=2, value=r['label']), size=9)
        st(ws.cell(row=i, column=3, value=f"{r['start']}~{r['end']}" if r['start'] else ''),
           size=9, color=DIM)
        st(ws.cell(row=i, column=4, value=r['work']), size=9, fmt='0.##')
        st(ws.cell(row=i, column=5, value=r['leave']), size=9, fmt='0.##')
        st(ws.cell(row=i, column=6, value=r['meets8']), size=9)
        st(ws.cell(row=i, column=7, value=r['block']), size=9, color=DIM)
        st(ws.cell(row=i, column=8, value=r['group']), size=9, color=DIM)

    meets = [r['code'] for r in combos if r['meets8']]
    swap  = [r['code'] for r in combos
             if not r['meets8'] and r['group'] in ('근무', '반차', '반반차')]
    for col, title, items in [(10, '30% 충족 코드', meets), (11, '조율 가능 코드', swap)]:
        st(ws.cell(row=1, column=col, value=title), bold=True, fill=HEAD_BG, size=9)
        for i, code in enumerate(items, start=2):
            st(ws.cell(row=i, column=col, value=code), align='left', size=9)
    st(ws.cell(row=1, column=13, value='요일'), bold=True, fill=HEAD_BG, size=9)
    for i, d in enumerate(['일', '월', '화', '수', '목', '금', '토'], start=2):
        st(ws.cell(row=i, column=13, value=d), size=9)

    for col, w in zip('ABCDEFGH', [17, 10, 13, 10, 9, 9, 14, 10]):
        ws.column_dimensions[col].width = w
    ws.column_dimensions['J'].width = 17
    ws.column_dimensions['K'].width = 17
    ws.column_dimensions['M'].width = 6
    ws.sheet_state = 'hidden'
    ws.protection.sheet = True
    return len(combos), len(meets), len(swap)


def sheet_roster(wb):
    ws = wb.create_sheet('명부')
    for j, h in enumerate(['이름', '팀', '파트', '직책', '그룹', '휴직'], start=1):
        st(ws.cell(row=1, column=j, value=h), bold=True, fill=HEAD_BG, size=9)
    for i, row in enumerate(ROSTER, start=M0):
        for j, v in enumerate(row, start=1):
            st(ws.cell(row=i, column=j, value=v),
               align='left' if j <= 4 else 'center', locked=False)
    st(ws.cell(row=M1 + 2, column=1, value='활성 인원'), bold=True, align='left')
    st(ws.cell(row=M1 + 2, column=2,
               value=f'=COUNTA(A{M0}:A{M1})-COUNTIF(F{M0}:F{M1},"Y")'), bold=True, fill=OK_BG)
    st(ws.cell(row=M1 + 3, column=1, value='30% 필요 인원'), bold=True, align='left')
    st(ws.cell(row=M1 + 3, column=2, value=f'=ROUNDUP(B{M1+2}*0.3,0)'), bold=True, fill=OK_BG)
    ws.cell(row=M1 + 5, column=1,
            value='휴직 열에 Y 를 넣으면 30% 모수에서 빠집니다. '
                  '순서를 바꾸면 다른 시트의 이름도 함께 바뀝니다.').font = \
        Font(name=FONT, size=9, color=DIM)
    for col, w in zip('ABCDEF', [10, 12, 10, 8, 6, 6]):
        ws.column_dimensions[col].width = w
    ws.protection.sheet = True


def sheet_holidays(wb):
    ws = wb.create_sheet('공휴일')
    for j, h in enumerate(['날짜', '명칭'], start=1):
        st(ws.cell(row=1, column=j, value=h), bold=True, fill=HEAD_BG, size=9)
    for i, (d, n) in enumerate(HOLIDAYS, start=2):
        st(ws.cell(row=i, column=1, value=d), fmt='yyyy-mm-dd', locked=False)
        st(ws.cell(row=i, column=2, value=n), align='left', locked=False)
    ws.cell(row=len(HOLIDAYS) + 3, column=1,
            value='날짜는 반드시 날짜 형식(2027-01-01)으로 넣으세요. '
                  '설날·추석·부처님오신날은 음력이라 매년 확인이 필요합니다. '
                  '사내 휴무일도 여기에 추가하세요.').font = Font(name=FONT, size=9, color=DIM)
    ws.column_dimensions['A'].width = 14
    ws.column_dimensions['B'].width = 26
    ws.protection.sheet = True


def day_header(ws, title, note):
    """연·월 입력 + 주 순번 · 일자 · 요일 · 휴일 행 (근태 · OT · 시간 공통)."""
    st(ws.cell(row=1, column=1, value='연'), bold=True, align='right', border=False)
    st(ws.cell(row=1, column=2, value=2026), bold=True, fill='FFFF00', locked=False)
    st(ws.cell(row=2, column=1, value='월'), bold=True, align='right', border=False)
    st(ws.cell(row=2, column=2, value=9), bold=True, fill='FFFF00', locked=False)
    ws.cell(row=1, column=4, value=title).font = Font(name=FONT, bold=True, size=13, color=NAV)
    ws.cell(row=2, column=4, value=note).font = Font(name=FONT, size=9, color=DIM)
    st(ws.cell(row=3, column=1, value='주'), size=8, color=DIM, fill=HEAD_BG)

    for col in range(D0, D1 + 1):
        L = get_column_letter(col)
        st(ws.cell(row=3, column=col,
                   value=f'=IF({L}4="","",INT(({L}4-1+MOD(WEEKDAY(DATE($B$1,$B$2,1))+5,7))/7)+1)'),
           size=8, color=DIM, fill=HEAD_BG)
        st(ws.cell(row=4, column=col,
                   value='=IF(MONTH(DATE($B$1,$B$2,COLUMN()-3))<>$B$2,"",COLUMN()-3)'),
           bold=True, fill=HEAD_BG, size=9)
        st(ws.cell(row=5, column=col,
                   value=f'=IF({L}$4="","",INDEX(코드!$M$2:$M$8,WEEKDAY(DATE($B$1,$B$2,{L}$4))))'),
           fill=HEAD_BG, size=9, color=DIM)
        st(ws.cell(row=6, column=col,
                   value=f'=IF({L}$4="","",IF(OR(WEEKDAY(DATE($B$1,$B$2,{L}$4),2)>5,'
                         f'COUNTIF(공휴일!$A$2:$A$400,DATE($B$1,$B$2,{L}$4))>0),"휴일",""))'),
           fill=HEAD_BG, size=8, color=DIM)
        ws.column_dimensions[L].width = 13
    for col, w in zip('ABC', [10, 10, 6]):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = 'D8'


def member_rows(ws):
    for j, h in enumerate(['이름', '파트', '그룹'], start=1):
        st(ws.cell(row=7, column=j, value=h), bold=True, fill=HEAD_BG, size=9)
    for i in range(N):
        r, m = R0 + i, M0 + i
        st(ws.cell(row=r, column=1, value=f'=IF(명부!A{m}="","",명부!A{m})'),
           bold=True, align='left', size=9.5)
        st(ws.cell(row=r, column=2, value=f'=IF(명부!C{m}="","",명부!C{m})'),
           align='left', size=9, color=DIM)
        st(ws.cell(row=r, column=3, value=f'=IF(명부!E{m}="","",명부!E{m})'),
           size=9, color=DIM)


def sheet_attend(wb, nc, nmeets, nswap):
    ws = wb.create_sheet('근태')
    day_header(ws, '근태 — 빈칸이 8시간 근무입니다. 못 채우는 날만 드롭다운에서 고르세요',
               '노란 칸에 연·월을 넣으면 날짜와 요일이 바뀝니다 · '
               '드롭다운에는 규칙을 통과하는 조합만 들어 있어 위반 입력이 불가능합니다')
    member_rows(ws)
    for i in range(N):
        for col in range(D0, D1 + 1):
            st(ws.cell(row=R0 + i, column=col), size=9, locked=False)

    dv = DataValidation(type='list', formula1=f'=코드!$A$2:$A${nc+1}', allow_blank=True)
    dv.error = '드롭다운에 있는 조합만 넣을 수 있습니다. 목록에 없으면 규칙 위반입니다.'
    dv.errorTitle = '사용할 수 없는 조합'
    dv.prompt = ('빈칸 = 8시간 근무.\n'
                 '근무 0830-1730 · 오전반 1300-1700 처럼 유형과 시각을 함께 고릅니다.')
    dv.promptTitle = '근무 조합'
    ws.add_data_validation(dv)
    dv.add(f'{DL}{R0}:{DR}{R1}')

    active = f'명부!$B${M1+2}'
    meets  = f'코드!$J$2:$J${nmeets+1}'
    for key, r in ROW_SUM.items():
        st(ws.cell(row=r, column=1, value={'인원': '8시간 인원', '필요': '필요 인원 (30%)',
                                           '판정': '판정', '직책자': '직책자 8시간'}[key]),
           bold=True, align='left', fill=HEAD_BG, size=9)
        st(ws.cell(row=r, column=2), fill=HEAD_BG)
        st(ws.cell(row=r, column=3), fill=HEAD_BG)
    for col in range(D0, D1 + 1):
        L = get_column_letter(col)
        blanks = (f'SUMPRODUCT((명부!$F${M0}:$F${M1}<>"Y")*({L}${R0}:{L}${R1}=""))'
                  f'+SUMPRODUCT(COUNTIF({L}${R0}:{L}${R1},{meets}))')
        lead   = (f'SUMPRODUCT((명부!$F${M0}:$F${M0+5}<>"Y")*({L}${LEAD0}:{L}${LEAD1}=""))'
                  f'+SUMPRODUCT(COUNTIF({L}${LEAD0}:{L}${LEAD1},{meets}))')
        st(ws.cell(row=ROW_SUM['인원'], column=col,
                   value=f'=IF({L}$6="휴일","",{blanks})'), bold=True, fill=HEAD_BG, size=9)
        st(ws.cell(row=ROW_SUM['필요'], column=col,
                   value=f'=IF({L}$6="휴일","",ROUNDUP({active}*0.3,0))'),
           fill=HEAD_BG, size=9, color=DIM)
        st(ws.cell(row=ROW_SUM['판정'], column=col,
                   value=f'=IF({L}$6="휴일","",IF({L}{ROW_SUM["인원"]}>={L}{ROW_SUM["필요"]},'
                         f'"충족","미달"))'), bold=True, size=9)
        st(ws.cell(row=ROW_SUM['직책자'], column=col,
                   value=f'=IF({L}$6="휴일","",{lead})'), size=9)

    grid = f'{DL}{R0}:{DR}{R1}'
    # 미달인 날에 8시간으로 바꿔줄 수 있는 사람 — 출장·교육·연차는 후보가 아니다
    ws.conditional_formatting.add(grid, FormulaRule(
        formula=[f'AND({DL}${ROW_SUM["판정"]}="미달",'
                 f'COUNTIF(코드!$K$2:$K${nswap+1},{DL}{R0})>0)'],
        fill=PatternFill('solid', fgColor=CAND_BG),
        font=Font(name=FONT, bold=True, size=9, color='8A5A00'), stopIfTrue=True))
    ws.conditional_formatting.add(grid, FormulaRule(
        formula=[f'{DL}$6="휴일"'], fill=PatternFill('solid', fgColor=OFF_BG)))
    ws.conditional_formatting.add(grid, FormulaRule(
        formula=[f'{DL}{R0}<>""'], fill=PatternFill('solid', fgColor=IN_BG)))
    row_j = f'{DL}{ROW_SUM["판정"]}:{DR}{ROW_SUM["판정"]}'
    ws.conditional_formatting.add(row_j, CellIsRule(
        operator='equal', formula=['"미달"'], fill=PatternFill('solid', fgColor=BAD_BG),
        font=Font(name=FONT, bold=True, size=9, color='B3261E')))
    ws.conditional_formatting.add(row_j, CellIsRule(
        operator='equal', formula=['"충족"'], fill=PatternFill('solid', fgColor=OK_BG),
        font=Font(name=FONT, bold=True, size=9, color='0F7B4F')))
    ws.conditional_formatting.add(
        f'{DL}{ROW_SUM["직책자"]}:{DR}{ROW_SUM["직책자"]}',
        CellIsRule(operator='lessThan', formula=['1'],
                   fill=PatternFill('solid', fgColor=WARN_BG)))

    ws.cell(row=38, column=1,
            value='판정이 「미달」인 날은 노랗게 강조된 칸이 조율 후보입니다 — '
                  '그 사람이 8시간 근무로 바꾸면 충족됩니다 (출장·교육·연차는 후보에서 제외). '
                  '직책자 8시간이 0이면 팀장·파트장 중 한 명이 8시간을 맡아야 합니다.').font = \
        Font(name=FONT, size=9, color=DIM)
    ws.protection.sheet = True


def sheet_ot(wb):
    ws = wb.create_sheet('OT')
    day_header(ws, 'OT — 날짜별 초과근로 시간',
               '1시간 45분은 1.75 로 넣습니다 (분 단위 신청) · '
               '월 합계와 잔여는 「개인요약」 시트에서 봅니다')
    member_rows(ws)
    for i in range(N):
        for col in range(D0, D1 + 1):
            st(ws.cell(row=R0 + i, column=col), size=9, fmt='0.##', locked=False)
    ws.conditional_formatting.add(f'{DL}{R0}:{DR}{R1}', CellIsRule(
        operator='greaterThan', formula=['0'], fill=PatternFill('solid', fgColor=IN_BG)))
    ws.cell(row=R1 + 3, column=1,
            value='선택근로 시간과 OT 시간은 나눠서 관리합니다. '
                  '자정을 넘긴 OT 도 시간만 합쳐서 넣으면 됩니다.').font = \
        Font(name=FONT, size=9, color=DIM)
    ws.protection.sheet = True


def sheet_hours(wb, nc):
    """계산용 — 근태 시트의 코드를 실근로시간으로 바꾼다 (빈칸 = 소정근로일이면 8시간)."""
    ws = wb.create_sheet('시간')
    day_header(ws, '시간 (계산용) — 근태 시트의 코드를 실근로시간으로 바꾼 값입니다',
               '이 시트는 직접 고치지 마세요')
    member_rows(ws)
    for i in range(N):
        r = R0 + i
        for col in range(D0, D1 + 1):
            L = get_column_letter(col)
            st(ws.cell(row=r, column=col,
                       value=f'=IF(근태!{L}$4="",0,IF(근태!{L}{r}="",'
                             f'IF(근태!{L}$6="휴일",0,8),'
                             f'IFERROR(INDEX(코드!$D$2:$D${nc+1},'
                             f'MATCH(근태!{L}{r},코드!$A$2:$A${nc+1},0)),0)))'),
               size=9, fmt='0.##')
    ws.sheet_state = 'hidden'
    ws.protection.sheet = True


def sheet_summary(wb, nc, nmeets):
    ws = wb.create_sheet('개인요약')
    ws.cell(row=1, column=1, value='개인요약 — 월 총량 · OT 잔여 · 주별 근로시간').font = \
        Font(name=FONT, bold=True, size=13, color=NAV)
    ws.cell(row=2, column=1,
            value='「근태」 시트의 연·월을 따릅니다. 노란 칸(OT 기본 가능시간)만 직접 넣으세요 — '
                  '휴가를 쓰면 그 시간만큼 OT 한도가 자동으로 늘어납니다.').font = \
        Font(name=FONT, size=9, color=DIM)

    cols = ['이름', '파트', '그룹', '소정근로일', '기본 총량', '휴가', '조정 총량',
            '실근로', '총량 대비', 'OT 합계', 'OT 기본', 'OT 한도', 'OT 잔여', '8시간 일수'] \
        + [f'{w}주' for w in range(1, WEEKS + 1)] + ['최대 주', '주 64h']
    for j, h in enumerate(cols, start=1):
        st(ws.cell(row=7, column=j, value=h), bold=True, fill=HEAD_BG, size=9)
        ws.column_dimensions[get_column_letter(j)].width = 11 if j > 3 else 10

    A = f'근태!$D$4:$AH$4'          # 일자
    H = f'근태!$D$6:$AH$6'          # 휴일
    W = f'근태!$D$3:$AH$3'          # 주 순번
    CODE = f'코드!$A$2:$A${nc+1}'
    LEAVE = f'코드!$E$2:$E${nc+1}'
    MEET = f'코드!$J$2:$J${nmeets+1}'
    for i in range(N):
        r, m = R0 + i, M0 + i
        row = f'근태!$D${r}:$AH${r}'
        st(ws.cell(row=r, column=1, value=f'=IF(명부!A{m}="","",명부!A{m})'),
           bold=True, align='left', size=9.5)
        st(ws.cell(row=r, column=2, value=f'=IF(명부!C{m}="","",명부!C{m})'),
           align='left', size=9, color=DIM)
        st(ws.cell(row=r, column=3, value=f'=IF(명부!E{m}="","",명부!E{m})'), size=9, color=DIM)
        st(ws.cell(row=r, column=4, value=f'=SUMPRODUCT(({A}<>"")*({H}=""))'), size=9)
        st(ws.cell(row=r, column=5, value=f'=D{r}*8'), size=9, fmt='0.##')
        st(ws.cell(row=r, column=6,
                   value=f'=SUMPRODUCT(COUNTIF({row},{CODE}),{LEAVE})'), size=9, fmt='0.##')
        st(ws.cell(row=r, column=7, value=f'=E{r}-F{r}'), bold=True, size=9, fmt='0.##',
           fill=HEAD_BG)
        st(ws.cell(row=r, column=8, value=f'=SUM(시간!$D${r}:$AH${r})'), bold=True, size=9,
           fmt='0.##', fill=HEAD_BG)
        st(ws.cell(row=r, column=9, value=f'=H{r}-G{r}'), bold=True, size=9, fmt='+0.##;-0.##;0')
        st(ws.cell(row=r, column=10, value=f'=SUM(OT!$D${r}:$AH${r})'), size=9, fmt='0.##')
        st(ws.cell(row=r, column=11, value=None), fill='FFFF00', size=9, fmt='0.##',
           locked=False)
        st(ws.cell(row=r, column=12, value=f'=K{r}+F{r}'), size=9, fmt='0.##', color=DIM)
        st(ws.cell(row=r, column=13, value=f'=L{r}-J{r}'), bold=True, size=9, fmt='0.##')
        st(ws.cell(row=r, column=14,
                   value=f'=SUMPRODUCT(({H}="")*({A}<>"")*({row}=""))'
                         f'+SUMPRODUCT(COUNTIF({row},{MEET}))'), size=9)
        for w in range(1, WEEKS + 1):
            st(ws.cell(row=r, column=14 + w,
                       value=f'=SUMPRODUCT(({W}={w})*(시간!$D${r}:$AH${r}+OT!$D${r}:$AH${r}))'),
               size=9, fmt='0.##;;')
        first, last = get_column_letter(15), get_column_letter(14 + WEEKS)
        st(ws.cell(row=r, column=15 + WEEKS, value=f'=MAX({first}{r}:{last}{r})'),
           bold=True, size=9, fmt='0.##')
        st(ws.cell(row=r, column=16 + WEEKS,
                   value=f'=IF({get_column_letter(15+WEEKS)}{r}>64,"초과","적합")'), size=9)

    dif = get_column_letter(9)
    ws.conditional_formatting.add(f'{dif}{R0}:{dif}{R1}', CellIsRule(
        operator='lessThan', formula=['0'], fill=PatternFill('solid', fgColor=WARN_BG)))
    rem = get_column_letter(13)
    ws.conditional_formatting.add(f'{rem}{R0}:{rem}{R1}', CellIsRule(
        operator='lessThan', formula=['0'], fill=PatternFill('solid', fgColor=BAD_BG),
        font=Font(name=FONT, bold=True, size=9, color='B3261E')))
    v64 = get_column_letter(16 + WEEKS)
    ws.conditional_formatting.add(f'{v64}{R0}:{v64}{R1}', CellIsRule(
        operator='equal', formula=['"초과"'], fill=PatternFill('solid', fgColor=BAD_BG),
        font=Font(name=FONT, bold=True, size=9, color='B3261E')))

    ws.cell(row=R1 + 3, column=1,
            value='주별 근로시간은 정규 + OT 이고 64시간을 넘으면 빨갛게 표시됩니다. '
                  '탄력근무 3개월 평균 52시간 판정은 달을 넘겨야 하므로 '
                  'index.html 의 「탄력근무 52/64」 탭에서 확인하세요.').font = \
        Font(name=FONT, size=9, color=DIM)
    ws.freeze_panes = 'D8'
    ws.protection.sheet = True


def sheet_guide(wb, nc, source):
    ws = wb.create_sheet('사용안내', 0)
    L = [
        ('위례 근태 관리 — Teams · OneDrive 공동 편집용', 14, True, NAV),
        ('', 10, False, INK),
        ('이 파일은 Teams 또는 OneDrive 공유 폴더에 두고 모든 구성원이 동시에 편집합니다. '
         '각자 자기 행만 고치면 되고, 30% 판정·월 총량·OT 잔여는 전부 자동으로 계산됩니다.', 10, False, INK),
        ('', 10, False, INK),
        ('■ 반드시 지켜주세요 — 동시 편집이 되려면', 11, True, 'B3261E'),
        ('   · Excel Online(브라우저)으로 열거나, Excel 데스크톱에서 자동 저장(AutoSave)을 켜고 여세요.', 10, False, INK),
        ('   · 파일을 자기 PC로 복사해서 열면 별개 파일이 되어 다른 사람 입력이 반영되지 않습니다.', 10, False, INK),
        ('', 10, False, INK),
        ('■ 근태 시트 — 자기 이름 행에서 날짜 칸을 고릅니다', 11, True, NAV),
        ('   · 빈칸이 8시간 근무입니다. 8시간을 채우는 날은 아무것도 넣지 마세요.', 10, False, INK),
        (f'   · 드롭다운에는 규칙을 통과하는 {nc}가지 조합만 들어 있습니다. '
         '「근무 0830-1730」「오전반 1300-1700」처럼 유형과 시각을 함께 고릅니다.', 10, False, INK),
        ('   · 목록에 없는 조합은 규칙 위반이라 아예 넣을 수 없습니다 — '
         '코어타임·휴게시간·반차 배치 규칙이 드롭다운 자체에 반영되어 있습니다.', 10, False, INK),
        ('   · 맨 아래 판정 행이 빨갛게 되면 그날 30%가 미달입니다. '
         '노랗게 강조된 칸이 조율 후보 — 그 사람이 8시간으로 바꾸면 충족됩니다.', 10, False, INK),
        ('   · 노란 칸(B1·B2)에 연·월을 넣으면 날짜와 요일이 자동으로 바뀝니다.', 10, False, INK),
        ('', 10, False, INK),
        ('■ OT 시트 — 날짜별 초과근로 시간', 11, True, NAV),
        ('   · 1시간 45분은 1.75 로 넣습니다 (OT 는 분 단위로 신청).', 10, False, INK),
        ('   · 자정을 넘긴 OT 도 시간만 합쳐서 넣으면 됩니다.', 10, False, INK),
        ('', 10, False, INK),
        ('■ 개인요약 시트 — 월 총량과 OT 잔여', 11, True, NAV),
        ('   · 휴가를 쓰면 월 총량이 그만큼 줄고(160h − 연차 8h = 152h), '
         'OT 가능시간은 그만큼 늘어납니다.', 10, False, INK),
        ('   · 노란 칸(OT 기본 가능시간)에 사내 HR 시스템의 그 달 값을 넣으세요.', 10, False, INK),
        ('   · 주별 근로시간(정규+OT)이 64시간을 넘으면 빨갛게 표시됩니다.', 10, False, INK),
        ('', 10, False, INK),
        ('■ 명부 · 공휴일 — 인원 변동과 휴일이 바뀔 때만', 11, True, NAV),
        ('   · 명부 휴직 열에 Y 를 넣으면 30% 모수에서 빠집니다.', 10, False, INK),
        ('   · 공휴일에 사내 휴무일·창립기념일도 추가하세요.', 10, False, INK),
        ('', 10, False, INK),
        ('■ 이 파일이 하지 않는 것 — index.html 도구에서 확인하세요', 11, True, NAV),
        ('   · 탄력근무 3개월 평균 52시간 판정 (달을 넘기는 계산)', 10, False, INK),
        ('   · 목록에 없는 조합이 왜 안 되는지 이유 설명 (규칙 검증기)', 10, False, INK),
        ('', 10, False, INK),
        ('시트 보호가 걸려 있지만 암호는 없습니다. 수식을 고쳐야 하면 '
         '[검토] → [시트 보호 해제] 를 누르세요.', 9, False, DIM),
        (f'근무 조합 {nc}가지는 index.html 의 규칙 엔진에서 직접 뽑았습니다 ({source}). '
         '규칙이 바뀌면 python worktime/build_xlsx.py 로 다시 만드세요.', 9, False, DIM),
    ]
    for i, (txt, sz, bold, col) in enumerate(L, start=1):
        c = ws.cell(row=i, column=1, value=txt)
        c.font = Font(name=FONT, size=sz, bold=bold, color=col)
    ws.column_dimensions['A'].width = 120
    ws.protection.sheet = True


def build(path):
    combos, source = load_combos()
    wb = Workbook()
    wb.remove(wb.active)
    nc, nmeets, nswap = sheet_codes(wb, combos)
    sheet_attend(wb, nc, nmeets, nswap)
    sheet_ot(wb)
    sheet_summary(wb, nc, nmeets)
    sheet_hours(wb, nc)
    sheet_roster(wb)
    sheet_holidays(wb)
    sheet_guide(wb, nc, source)
    wb.move_sheet('코드', offset=len(wb.sheetnames))
    wb.move_sheet('시간', offset=len(wb.sheetnames))
    wb.active = 0
    wb.save(path)
    print(f'{path}  ({nc}개 조합 · 30% 충족 {nmeets}건 · 조율 후보 {nswap}건 · {source})')
    return path


if __name__ == '__main__':
    build(sys.argv[1] if len(sys.argv) > 1 else str(HERE / '위례_근태관리.xlsx'))
