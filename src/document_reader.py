from __future__ import annotations

from pathlib import Path
from docx import Document

from src.hwp_extractor import extract_hwp_text


def read_source(path: Path, work_dir: Path) -> tuple[str, Path | None]:
    suffix = path.suffix.lower()
    if suffix in {".hwp", ".hwpx"}:
        text, converted = extract_hwp_text(path, work_dir)
        return text, converted
    if suffix == ".txt":
        return path.read_text(encoding="utf-8"), None
    if suffix == ".docx":
        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip()), None
    raise ValueError("지원 파일 형식: .hwp, .hwpx, .docx, .txt")
