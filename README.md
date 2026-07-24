# HEIF → JPG/PNG 변환기

아이폰에서 촬영한 HEIF/HEIC 이미지를 JPG 또는 PNG로 변환하는 Python CLI 도구입니다.

## 특징

- 단일 파일 및 폴더(하위 폴더 포함) 일괄 변환
- JPG / PNG 출력 지원
- EXIF 방향 정보를 적용해 아이폰 사진의 회전 문제 방지
- JPEG 변환 시 EXIF 메타데이터 보존 및 품질 조절
- PNG 변환 시 투명도(알파 채널) 유지
- 출력 폴더 지정 시 원본 폴더 구조 유지

## 설치

```bash
pip install -r requirements.txt
```

## 사용법

```bash
# 단일 파일 변환 (기본: JPG, 원본 파일 옆에 저장)
python heif_converter.py photo.heic

# PNG로 변환
python heif_converter.py photo.heic -f png

# 폴더 전체를 변환하여 converted 폴더에 저장
python heif_converter.py ./photos -o ./converted -f jpg

# 하위 폴더까지 재귀 변환, JPEG 품질 95
python heif_converter.py ./photos -r -q 95

# 이미 존재하는 출력 파일 덮어쓰기
python heif_converter.py ./photos --overwrite
```

## 옵션

| 옵션 | 설명 |
| --- | --- |
| `source` | 변환할 HEIF 파일 또는 폴더 경로 (필수) |
| `-f`, `--format` | 출력 형식: `jpg`, `jpeg`, `png` (기본값: `jpg`) |
| `-o`, `--output` | 출력 폴더 (미지정 시 원본 옆에 저장) |
| `-q`, `--quality` | JPEG 품질 1–100 (기본값: 90, PNG에는 미적용) |
| `-r`, `--recursive` | 하위 폴더까지 재귀적으로 변환 |
| `--overwrite` | 이미 존재하는 출력 파일 덮어쓰기 |

## 요구 사항

- Python 3.9 이상
- [Pillow](https://python-pillow.org/)
- [pillow-heif](https://github.com/bigcat88/pillow_heif)
