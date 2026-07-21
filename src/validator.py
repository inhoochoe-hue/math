from __future__ import annotations

import re
from typing import Any


def basic_validate_variant(item: dict[str, Any]) -> list[str]:
    """형식·객관식 중복·빈 정답 등을 검사한다."""
    errors: list[str] = []
    question = str(item.get("question", "")).strip()
    answer = str(item.get("answer", "")).strip()
    choices = item.get("choices", [])

    if len(question) < 15:
        errors.append("문제 문장이 너무 짧습니다.")
    if not answer:
        errors.append("정답이 없습니다.")
    if item.get("question_type") == "객관식":
        if not isinstance(choices, list) or len(choices) != 5:
            errors.append("객관식 보기가 5개가 아닙니다.")
        else:
            normalized = [re.sub(r"^[①②③④⑤1-5.()\s]+", "", str(x)).strip() for x in choices]
            if len(set(normalized)) != 5:
                errors.append("객관식 보기에 중복이 있습니다.")

    return errors


def attach_validation(result: dict[str, Any]) -> dict[str, Any]:
    for item in result.get("variants", []):
        errors = basic_validate_variant(item)
        item["validation"] = {
            "passed": not errors,
            "errors": errors,
        }
    return result
