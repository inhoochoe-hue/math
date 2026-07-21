from __future__ import annotations

import re


def split_problems(text: str) -> list[str]:
    """족보닷컴 계열의 'zb' 표식과 문제 번호 패턴을 이용해 문제를 분리한다."""
    normalized = text.replace("\u00a0", " ")

    # 이 자료에서 확인된 zb 마커를 우선 사용한다.
    parts = re.split(r"(?=\bzb\b)", normalized, flags=re.IGNORECASE)
    problems = [re.sub(r"^\s*zb\s*", "", p, flags=re.IGNORECASE).strip() for p in parts]
    problems = [p for p in problems if len(p) >= 20]

    if len(problems) >= 3:
        return problems

    # 일반 시험지의 1., 2., 3. 또는 1) 패턴 대체 처리
    parts = re.split(r"(?m)(?=^\s*\d{1,3}\s*[.\)])", normalized)
    return [p.strip() for p in parts if len(p.strip()) >= 20]
