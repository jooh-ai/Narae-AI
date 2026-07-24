#!/usr/bin/env python3
"""HEIF/HEIC → JPG/PNG 변환기 GUI.

폴더를 선택하면 그 안의 HEIF/HEIC 이미지를 지정한 형식으로 변환하여
새 폴더에 저장하는 그래픽 인터페이스입니다. 변환 로직은
``heif_converter`` 모듈의 함수를 그대로 재사용합니다.

실행:
    python heif_converter_gui.py
"""

from __future__ import annotations

import queue
import threading
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from heif_converter import (
    FORMAT_CONFIG,
    build_output_path,
    convert_file,
    find_heif_files,
)


class ConverterApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("HEIF → JPG/PNG 변환기")
        root.minsize(560, 480)

        # 워커 스레드 → GUI 스레드로 진행 메시지를 전달하는 큐
        self._queue: queue.Queue = queue.Queue()
        self._worker: threading.Thread | None = None

        # --- 상태 변수 ---
        self.input_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.fmt = tk.StringVar(value="jpg")
        self.quality = tk.IntVar(value=90)
        self.recursive = tk.BooleanVar(value=True)
        self.overwrite = tk.BooleanVar(value=False)

        self._build_ui()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        pad = {"padx": 8, "pady": 4}
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill="both", expand=True)
        main.columnconfigure(1, weight=1)

        # 입력 폴더
        ttk.Label(main, text="입력 폴더").grid(row=0, column=0, sticky="w", **pad)
        ttk.Entry(main, textvariable=self.input_dir).grid(
            row=0, column=1, sticky="ew", **pad
        )
        ttk.Button(main, text="찾아보기…", command=self._pick_input).grid(
            row=0, column=2, **pad
        )

        # 출력 폴더
        ttk.Label(main, text="출력 폴더").grid(row=1, column=0, sticky="w", **pad)
        ttk.Entry(main, textvariable=self.output_dir).grid(
            row=1, column=1, sticky="ew", **pad
        )
        ttk.Button(main, text="찾아보기…", command=self._pick_output).grid(
            row=1, column=2, **pad
        )

        # 옵션 프레임
        opts = ttk.LabelFrame(main, text="옵션", padding=10)
        opts.grid(row=2, column=0, columnspan=3, sticky="ew", **pad)
        opts.columnconfigure(1, weight=1)

        ttk.Label(opts, text="출력 형식").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        fmt_frame = ttk.Frame(opts)
        fmt_frame.grid(row=0, column=1, sticky="w")
        ttk.Radiobutton(fmt_frame, text="JPG", variable=self.fmt, value="jpg",
                        command=self._toggle_quality).pack(side="left", padx=(0, 12))
        ttk.Radiobutton(fmt_frame, text="PNG", variable=self.fmt, value="png",
                        command=self._toggle_quality).pack(side="left")

        ttk.Label(opts, text="JPEG 품질").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        q_frame = ttk.Frame(opts)
        q_frame.grid(row=1, column=1, sticky="ew")
        q_frame.columnconfigure(0, weight=1)
        self.quality_scale = ttk.Scale(
            q_frame, from_=1, to=100, variable=self.quality,
            command=lambda v: self.quality.set(int(float(v))),
        )
        self.quality_scale.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.quality_label = ttk.Label(q_frame, textvariable=self.quality, width=4)
        self.quality_label.grid(row=0, column=1)

        ttk.Checkbutton(opts, text="하위 폴더까지 포함", variable=self.recursive).grid(
            row=2, column=0, columnspan=2, sticky="w", padx=6, pady=2
        )
        ttk.Checkbutton(opts, text="기존 파일 덮어쓰기", variable=self.overwrite).grid(
            row=3, column=0, columnspan=2, sticky="w", padx=6, pady=2
        )

        # 변환 버튼 + 진행 표시줄
        self.convert_btn = ttk.Button(main, text="변환 시작", command=self._start)
        self.convert_btn.grid(row=3, column=0, columnspan=3, sticky="ew", **pad)

        self.progress = ttk.Progressbar(main, mode="determinate")
        self.progress.grid(row=4, column=0, columnspan=3, sticky="ew", **pad)

        # 로그 영역
        ttk.Label(main, text="진행 상황").grid(row=5, column=0, sticky="w", **pad)
        log_frame = ttk.Frame(main)
        log_frame.grid(row=6, column=0, columnspan=3, sticky="nsew", **pad)
        main.rowconfigure(6, weight=1)
        log_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)

        self.log = tk.Text(log_frame, height=10, state="disabled", wrap="word")
        self.log.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(log_frame, command=self.log.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.log.configure(yscrollcommand=scroll.set)

    # --------------------------------------------------------------- 이벤트
    def _pick_input(self) -> None:
        path = filedialog.askdirectory(title="입력 폴더 선택")
        if path:
            self.input_dir.set(path)
            # 출력 폴더가 비어있으면 기본값 제안
            if not self.output_dir.get():
                self.output_dir.set(str(Path(path).parent / "converted"))

    def _pick_output(self) -> None:
        path = filedialog.askdirectory(title="출력 폴더 선택")
        if path:
            self.output_dir.set(path)

    def _toggle_quality(self) -> None:
        state = "normal" if self.fmt.get() == "jpg" else "disabled"
        self.quality_scale.configure(state=state)

    def _log(self, message: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", message + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    # --------------------------------------------------------------- 변환
    def _start(self) -> None:
        if self._worker and self._worker.is_alive():
            return

        input_dir = self.input_dir.get().strip()
        output_dir = self.output_dir.get().strip()

        if not input_dir or not Path(input_dir).is_dir():
            messagebox.showerror("오류", "유효한 입력 폴더를 선택하세요.")
            return
        if not output_dir:
            messagebox.showerror("오류", "출력 폴더를 지정하세요.")
            return
        if Path(output_dir).resolve() == Path(input_dir).resolve():
            messagebox.showerror("오류", "출력 폴더는 입력 폴더와 달라야 합니다.")
            return

        files = find_heif_files(Path(input_dir), self.recursive.get())
        if not files:
            messagebox.showinfo("알림", "변환할 HEIF/HEIC 파일을 찾지 못했습니다.")
            return

        # 로그 초기화 및 UI 잠금
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self.convert_btn.configure(state="disabled", text="변환 중…")
        self.progress.configure(maximum=len(files), value=0)
        self._log(f"총 {len(files)}개 파일을 {self.fmt.get().upper()} 형식으로 변환합니다.\n")

        # 워커 스레드에 넘길 값 (GUI 변수는 워커에서 직접 읽지 않음)
        params = {
            "files": files,
            "source": Path(input_dir),
            "output": Path(output_dir),
            "config": FORMAT_CONFIG[self.fmt.get()],
            "quality": self.quality.get(),
            "overwrite": self.overwrite.get(),
        }
        self._worker = threading.Thread(
            target=self._run_conversion, args=(params,), daemon=True
        )
        self._worker.start()
        self.root.after(100, self._poll_queue)

    def _run_conversion(self, params: dict) -> None:
        """워커 스레드: 변환을 수행하고 결과를 큐로 보고한다."""
        succeeded = 0
        failed = 0
        for src_file in params["files"]:
            dst_file = build_output_path(
                src_file, params["source"], params["output"],
                params["config"]["extension"],
            )
            ok, message = convert_file(
                src_file, dst_file, params["config"]["pillow_format"],
                params["quality"], params["overwrite"],
            )
            if ok:
                succeeded += 1
            else:
                failed += 1
            self._queue.put(("progress", ok, message))

        self._queue.put(("done", succeeded, failed))

    def _poll_queue(self) -> None:
        """GUI 스레드: 큐에서 메시지를 꺼내 화면을 갱신한다."""
        try:
            while True:
                kind, *rest = self._queue.get_nowait()
                if kind == "progress":
                    ok, message = rest
                    self._log(("  ✓ " if ok else "  ✗ ") + message)
                    self.progress.step(1)
                elif kind == "done":
                    succeeded, failed = rest
                    self._log(f"\n완료: 성공 {succeeded}개, 실패/건너뜀 {failed}개")
                    self.convert_btn.configure(state="normal", text="변환 시작")
                    messagebox.showinfo(
                        "완료",
                        f"변환이 끝났습니다.\n성공 {succeeded}개, 실패/건너뜀 {failed}개",
                    )
                    return
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)


def main() -> None:
    root = tk.Tk()
    ConverterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
