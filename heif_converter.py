#!/usr/bin/env python3
"""HEIF/HEIC 이미지를 JPG 또는 PNG로 변환하는 CLI 도구.

아이폰에서 촬영한 .heic / .heif 사진을 JPEG 또는 PNG 형식으로 변환합니다.
단일 파일과 폴더(하위 폴더 포함) 일괄 변환을 모두 지원하며, EXIF 방향 정보와
메타데이터를 최대한 보존합니다.

사용 예시:
    # 단일 파일 변환 (기본: JPG)
    python heif_converter.py photo.heic

    # PNG로 변환
    python heif_converter.py photo.heic -f png

    # 폴더 전체를 변환하여 output 폴더에 저장
    python heif_converter.py ./photos -o ./converted -f jpg

    # 하위 폴더까지 재귀적으로 변환, JPEG 품질 95
    python heif_converter.py ./photos -r -q 95
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError:
    sys.exit(
        "오류: Pillow 가 설치되어 있지 않습니다.\n"
        "설치: pip install pillow pillow-heif"
    )

try:
    import pillow_heif

    pillow_heif.register_heif_opener()
except ImportError:
    sys.exit(
        "오류: pillow-heif 가 설치되어 있지 않습니다.\n"
        "설치: pip install pillow-heif"
    )


# 변환 대상으로 인식할 입력 확장자
HEIF_EXTENSIONS = {".heic", ".heif", ".hif"}

# 출력 형식별 설정
FORMAT_CONFIG = {
    "jpg": {"pillow_format": "JPEG", "extension": ".jpg"},
    "jpeg": {"pillow_format": "JPEG", "extension": ".jpg"},
    "png": {"pillow_format": "PNG", "extension": ".png"},
}


def find_heif_files(source: Path, recursive: bool) -> list[Path]:
    """변환할 HEIF 파일 목록을 반환한다."""
    if source.is_file():
        return [source]

    pattern = "**/*" if recursive else "*"
    return sorted(
        p
        for p in source.glob(pattern)
        if p.is_file() and p.suffix.lower() in HEIF_EXTENSIONS
    )


def build_output_path(
    src_file: Path,
    source_root: Path,
    output_root: Path | None,
    extension: str,
) -> Path:
    """입력 파일에 대응하는 출력 경로를 계산한다.

    출력 폴더가 지정되면 원본의 폴더 구조를 유지하고,
    지정되지 않으면 원본 파일 옆에 저장한다.
    """
    if output_root is None:
        return src_file.with_suffix(extension)

    if source_root.is_file():
        return output_root / (src_file.stem + extension)

    relative = src_file.relative_to(source_root)
    return output_root / relative.with_suffix(extension)


def convert_file(
    src_file: Path,
    dst_file: Path,
    pillow_format: str,
    quality: int,
    overwrite: bool,
) -> tuple[bool, str]:
    """단일 HEIF 파일을 변환한다.

    Returns:
        (성공 여부, 메시지)
    """
    if dst_file.exists() and not overwrite:
        return False, f"건너뜀 (이미 존재): {dst_file.name}"

    try:
        with Image.open(src_file) as img:
            # EXIF 방향 정보를 실제 픽셀에 적용 (아이폰 사진 회전 문제 방지)
            img = ImageOps.exif_transpose(img)

            save_kwargs: dict = {}
            exif = img.info.get("exif")

            if pillow_format == "JPEG":
                # JPEG 는 알파 채널을 지원하지 않으므로 RGB 로 변환
                if img.mode in ("RGBA", "P", "LA"):
                    img = img.convert("RGB")
                save_kwargs["quality"] = quality
                save_kwargs["optimize"] = True
                if exif:
                    save_kwargs["exif"] = exif
            elif pillow_format == "PNG":
                save_kwargs["optimize"] = True

            dst_file.parent.mkdir(parents=True, exist_ok=True)
            img.save(dst_file, format=pillow_format, **save_kwargs)

        return True, f"변환 완료: {src_file.name} -> {dst_file.name}"
    except Exception as exc:  # noqa: BLE001 - 사용자에게 원인 보고
        return False, f"실패: {src_file.name} ({exc})"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="HEIF/HEIC 이미지를 JPG 또는 PNG로 변환합니다.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "source",
        type=Path,
        help="변환할 HEIF 파일 또는 폴더 경로",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["jpg", "jpeg", "png"],
        default="jpg",
        help="출력 형식 (기본값: jpg)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="출력 폴더 (미지정 시 원본 파일 옆에 저장)",
    )
    parser.add_argument(
        "-q",
        "--quality",
        type=int,
        default=90,
        metavar="1-100",
        help="JPEG 품질 (1-100, 기본값: 90, PNG 에는 미적용)",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="하위 폴더까지 재귀적으로 변환",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="이미 존재하는 출력 파일을 덮어쓰기",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if not args.source.exists():
        print(f"오류: 경로를 찾을 수 없습니다: {args.source}", file=sys.stderr)
        return 1

    if not 1 <= args.quality <= 100:
        print("오류: 품질(-q)은 1에서 100 사이여야 합니다.", file=sys.stderr)
        return 1

    config = FORMAT_CONFIG[args.format]
    files = find_heif_files(args.source, args.recursive)

    if not files:
        print("변환할 HEIF/HEIC 파일을 찾지 못했습니다.")
        return 0

    print(f"총 {len(files)}개 파일을 {args.format.upper()} 형식으로 변환합니다.\n")

    succeeded = 0
    failed = 0
    for src_file in files:
        dst_file = build_output_path(
            src_file, args.source, args.output, config["extension"]
        )
        ok, message = convert_file(
            src_file,
            dst_file,
            config["pillow_format"],
            args.quality,
            args.overwrite,
        )
        print(("  ✓ " if ok else "  ✗ ") + message)
        if ok:
            succeeded += 1
        else:
            failed += 1

    print(f"\n완료: 성공 {succeeded}개, 실패/건너뜀 {failed}개")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
