"""표 셀 편집은 [Test 결과 List-up] 에서만 허용된다.

왜 테스트로 못박는가
    QTableWidget 은 기본이 편집 가능이다. 새 표를 추가할 때 아무 설정을 안 하면
    더블클릭으로 계산 결과가 고쳐지고, 화면 숫자와 실제 계산이 어긋나는데 경고가
    없다. 2026-08 에 실제로 네 개 표(모델선정 2개·온도 프로파일·보정값 현황)가
    그 상태였다. 표가 늘어날 때마다 같은 실수가 나므로 불변식으로 고정한다.
"""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6")


@pytest.fixture(scope="module")
def win(tmp_path_factory):
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6 import QtWidgets

    import wirye_capacity.ui.app as app_mod

    holder: dict = {}

    def grab(self):
        holder["w"] = next(x for x in QtWidgets.QApplication.topLevelWidgets()
                           if isinstance(x, QtWidgets.QMainWindow))
        return 0

    real_exec = QtWidgets.QApplication.exec
    QtWidgets.QApplication.exec = grab
    try:
        app_mod.main([])
    finally:
        QtWidgets.QApplication.exec = real_exec
    w = holder["w"]
    w._connector = lambda: None          # RiMS 접속 시도 방지
    return w


# (속성명, 사람이 읽는 이름, 편집 허용 여부)
TABLES = [
    ("sel_loocv", "모델 선정 ① 학습셋 LOOCV", False),
    ("sel_test", "모델 선정 ② 테스트셋 검증", False),
    ("profile_tbl", "공급가능용량 산정 온도 프로파일", False),
    ("status_tbl", "온도 구간별 보정값 현황", False),
    ("list_tbl", "Test 결과 List-up", True),
]


@pytest.mark.parametrize("attr,label,editable", TABLES)
def test_only_listup_is_editable(win, attr, label, editable):
    from PySide6 import QtWidgets

    tb = getattr(win, attr)
    no_edit = QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
    if editable:
        assert tb.editTriggers() != no_edit, f"{label} 은 편집 가능해야 한다"
    else:
        assert tb.editTriggers() == no_edit, (
            f"{label} 이 편집 가능한 상태다 — 계산 결과 표는 고칠 수 없어야 한다")


def test_every_table_in_window_is_covered(win):
    """새 표를 추가하고 이 목록에 넣지 않으면 실패한다 — 누락 방지."""
    from PySide6 import QtWidgets

    found = {t.objectName() or id(t): t
             for t in win.findChildren(QtWidgets.QTableWidget)}
    known = {id(getattr(win, a)) for a, _l, _e in TABLES}
    missing = [t for k, t in found.items() if id(t) not in known]
    assert not missing, (
        f"TABLES 목록에 없는 표 {len(missing)}개 — 편집 허용 여부를 정하고 등록하십시오")


def test_method_column_is_wide_enough_for_longest_label(win):
    """'GP · Rational Quadratic' 이 '...' 로 잘리지 않는다.

    전부 Stretch 로 두면 좁은 창에서 잘린다. ResizeToContents 도 2px 모자랐다.
    """
    from wirye_capacity import select as S

    fm = win.sel_loocv.fontMetrics()
    need = max(fm.horizontalAdvance(v) for v in S.METHOD_LABEL.values())
    got = win.sel_loocv.horizontalHeader().sectionSize(0)
    assert got >= need + 8, f"방법 열 {got}px < 필요 {need}px — 라벨이 잘린다"
