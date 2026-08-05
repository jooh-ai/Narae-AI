"""사내 DRM(xlsx → OLE2 암호화) 환경에서 템플릿 폴백이 동작하는지 검증.

현장 증상(2026-08): 번들 excel3_profile_template.xlsx 가 사내 문서보안으로
암호화되어 OLE2 컨테이너(D0 CF 11 E0 …)가 되고, 크기가 109,748 → 152,064 로 늘었다.
openpyxl 은 zip 이 아니라며 실패한다. 같은 내용의 .tpl 사본을 메모리에서 읽어 우회한다.
"""
import json

import pytest

from wirye_capacity import profile as P
from wirye_capacity.correction import aggregate_bins
from wirye_capacity.excel_io import ExcelOpenError, load_workbook_bytes
from wirye_capacity.store import _SEED
from wirye_capacity.theory import TheoryEngine

OLE2_HEADER = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
SEED = json.loads(_SEED.read_text(encoding="utf-8"))
RECS = [{"cit": r["cit"], "corr": r["corr"]} for r in SEED]


def test_fallback_tpl_exists_and_is_valid_xlsx():
    """DRM 회피 사본이 번들에 있고, 내용이 정상 xlsx 여야 한다."""
    import zipfile
    from pathlib import Path
    tpl = Path(P.FALLBACK_TEMPLATE)
    assert tpl.exists(), "excel3_profile_template.tpl 이 없습니다(빌드 시 번들 필요)"
    assert zipfile.is_zipfile(tpl)
    with zipfile.ZipFile(tpl) as z:
        assert "xl/workbook.xml" in z.namelist()


def test_tpl_content_matches_xlsx():
    """두 파일 내용이 동일해야 한다(사본이 낡으면 입찰 양식이 달라진다)."""
    from pathlib import Path
    assert Path(P.DEFAULT_TEMPLATE).read_bytes() == Path(P.FALLBACK_TEMPLATE).read_bytes()


def test_open_template_normal_path():
    wb = P.open_template()
    assert "Mode3" in wb.sheetnames


def test_open_template_falls_back_when_drm_encrypted(tmp_path, monkeypatch):
    """기본 템플릿이 DRM 암호화되면 .tpl 로 자동 폴백한다."""
    fake = tmp_path / "excel3_profile_template.xlsx"
    fake.write_bytes(OLE2_HEADER + b"\x00" * 4096)          # DRM 암호화 파일 위장
    monkeypatch.setattr(P, "DEFAULT_TEMPLATE", fake)
    wb = P.open_template()                                   # 예외 없이 열려야 함
    assert "Mode3" in wb.sheetnames


def test_explicit_user_path_does_not_fall_back(tmp_path, monkeypatch):
    """사용자가 직접 지정한 파일이 DRM 이면 조용히 다른 양식을 쓰지 않고 실패한다."""
    user = tmp_path / "내가_지정한_양식.xlsx"
    user.write_bytes(OLE2_HEADER + b"\x00" * 4096)
    with pytest.raises(ExcelOpenError) as e:
        P.open_template(user)
    assert "DRM" in str(e.value) or "암호화" in str(e.value)


def test_error_message_identifies_drm(tmp_path):
    """오류 메시지가 DRM 을 지목하고 경로·크기를 알려준다."""
    from wirye_capacity.excel_io import load_workbook_safe
    f = tmp_path / "drm.xlsx"
    f.write_bytes(OLE2_HEADER + b"\x00" * 1000)
    with pytest.raises(ExcelOpenError) as e:
        load_workbook_safe(f)
    msg = str(e.value)
    assert "DRM" in msg
    assert str(f) in msg                     # 전체 경로
    assert "바이트" in msg                    # 크기


def test_load_workbook_bytes_rejects_ole2():
    with pytest.raises(ExcelOpenError) as e:
        load_workbook_bytes(OLE2_HEADER + b"\x00" * 100, name="테스트")
    assert "OLE2" in str(e.value) or "DRM" in str(e.value)


def test_bid_file_generated_under_drm(tmp_path, monkeypatch):
    """DRM 환경에서도 입찰파일 생성이 끝까지 동작한다(폴백 경유)."""
    fake = tmp_path / "excel3_profile_template.xlsx"
    fake.write_bytes(OLE2_HEADER + b"\x00" * 4096)
    monkeypatch.setattr(P, "DEFAULT_TEMPLATE", fake)
    out = tmp_path / "bid.xlsx"
    P.fill_excel3_template(out, engine=TheoryEngine(),
                           correction_table=aggregate_bins(RECS))
    assert out.exists() and out.stat().st_size > 10_000
    import zipfile
    assert zipfile.is_zipfile(out)
