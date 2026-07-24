# HEIF → JPG/PNG 변환기

아이폰에서 촬영한 HEIF/HEIC 이미지를 JPG 또는 PNG로 변환하는 Python 도구입니다.
명령줄(CLI)과 클릭으로 쓰는 그래픽(GUI) 두 가지 방식을 제공합니다.

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

## GUI 사용법 (권장)

폴더를 통째로 변환할 때 가장 편합니다. 터미널에서 다음을 실행하면 창이 열립니다.

```bash
python heif_converter_gui.py
```

1. **입력 폴더** — 변환할 HEIC 사진이 들어있는 폴더를 선택합니다.
2. **출력 폴더** — 변환된 파일을 저장할 새 폴더를 선택합니다. (입력 폴더를 고르면
   옆에 `converted` 폴더가 자동으로 제안됩니다.)
3. 출력 형식(JPG/PNG), JPEG 품질, 하위 폴더 포함 여부, 덮어쓰기 여부를 지정합니다.
4. **변환 시작**을 누르면 진행 상황이 실시간으로 표시되고, 원본 폴더 구조를
   유지한 채 새 폴더에 저장됩니다.

> GUI는 파이썬 표준 라이브러리 `tkinter`를 사용합니다. 리눅스에서 `tkinter`가
> 없다는 오류가 나면 `sudo apt install python3-tk`로 설치하세요. Windows/macOS의
> 공식 파이썬에는 기본 포함되어 있습니다.

## CLI 사용법

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
- GUI 사용 시 `tkinter` (파이썬 표준 라이브러리; 리눅스는 `python3-tk` 패키지)
