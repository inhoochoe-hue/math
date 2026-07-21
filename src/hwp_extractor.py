from __future__ import annotations

import platform
import re
import shutil
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


def convert_hwp_to_hwpx(hwp_path: Path, hwpx_path: Path) -> Path:
    """Windows에 설치된 한글(Hancom)을 자동화해 HWP를 HWPX로 변환한다."""
    if platform.system() != "Windows":
        raise RuntimeError("HWP 변환은 Windows와 한글 프로그램이 설치된 환경에서 실행해야 합니다.")

    try:
        import pythoncom  # type: ignore
        import win32com.client  # type: ignore
    except ImportError as exc:
        raise RuntimeError("pywin32가 없습니다. pip install pywin32를 실행하세요.") from exc

    hwp_path = hwp_path.resolve()
    hwpx_path = hwpx_path.resolve()
    hwpx_path.parent.mkdir(parents=True, exist_ok=True)

    # Streamlit 실행 스레드에서 COM 사용 준비
    pythoncom.CoInitialize()

    hwp = None

    try:
        hwp = win32com.client.gencache.EnsureDispatch(
            "HWPFrame.HwpObject"
        )

        # 보안 경고를 줄이기 위한 한글 공식 자동화 모듈 등록 시도
        try:
            hwp.RegisterModule(
                "FilePathCheckDLL",
                "FilePathCheckerModule"
            )
        except Exception:
            pass

        opened = hwp.Open(
            str(hwp_path),
            "HWP",
            "forceopen:true"
        )

        if not opened:
            raise RuntimeError(
                f"한글에서 파일을 열지 못했습니다: {hwp_path}"
            )

        saved = hwp.SaveAs(
            str(hwpx_path),
            "HWPX",
            ""
        )

        if not saved or not hwpx_path.exists():
            raise RuntimeError("HWPX 변환에 실패했습니다.")

    finally:
        if hwp is not None:
            try:
                hwp.Quit()
            except Exception:
                pass

        # 현재 스레드에서 COM 사용 종료
        pythoncom.CoUninitialize()

    return hwpx_path


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def extract_text_from_hwpx(hwpx_path: Path) -> str:
    """HWPX ZIP 안의 section XML에서 본문과 수식 스크립트를 순서대로 추출한다."""
    chunks: list[str] = []

    with zipfile.ZipFile(hwpx_path) as zf:
        section_names = sorted(
            name for name in zf.namelist()
            if re.search(r"(^|/)section\d+\.xml$", name, re.IGNORECASE)
        )
        if not section_names:
            raise ValueError("HWPX에서 section XML을 찾지 못했습니다.")

        for name in section_names:
            root = ET.fromstring(zf.read(name))
            for elem in root.iter():
                local = _local_name(elem.tag).lower()
                text = (elem.text or "").strip()

                # 일반 글자와 한글 수식 개체의 스크립트를 보존한다.
                if local in {"t", "text", "script"} and text:
                    chunks.append(text)
                elif local in {"linebreak", "br"}:
                    chunks.append("\n")

                # 문단 종료를 줄바꿈으로 처리한다.
                if local in {"p", "paragraph"}:
                    chunks.append("\n")

    text = " ".join(chunks)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_hwp_text(input_path: Path, work_dir: Path) -> tuple[str, Path]:
    """HWP 또는 HWPX를 받아 텍스트와 사용된 HWPX 경로를 반환한다."""
    suffix = input_path.suffix.lower()
    work_dir.mkdir(parents=True, exist_ok=True)

    if suffix == ".hwpx":
        hwpx_path = work_dir / input_path.name
        if input_path.resolve() != hwpx_path.resolve():
            shutil.copy2(input_path, hwpx_path)
    elif suffix == ".hwp":
        hwpx_path = work_dir / f"{input_path.stem}.hwpx"
        convert_hwp_to_hwpx(input_path, hwpx_path)
    else:
        raise ValueError("지원 형식은 .hwp 또는 .hwpx입니다.")

    return extract_text_from_hwpx(hwpx_path), hwpx_path
