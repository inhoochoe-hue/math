from __future__ import annotations

import re
from typing import Any

from rapidfuzz.fuzz import ratio
from sympy import N, sympify


def normalize_text(text: str) -> str:
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"[①②③④⑤⑥⑦⑧⑨⑩]", "", text)
    return text.lower()


def verify_expression(expression: str, expected: str) -> tuple[bool, str]:
    if not expression.strip() or not expected.strip():
        return True, "검산식 미제공"
    try:
        actual = N(sympify(expression, evaluate=True))
        target = N(sympify(expected, evaluate=True))
        passed = bool(abs(float(actual - target)) < 1e-9)
        return passed, f"계산값={actual}, 기대값={target}"
    except Exception as exc:
        return False, f"검산식 해석 실패: {exc}"


def assess_variant(source: str, item: dict[str, Any], existing_questions: list[str] | None = None) -> dict[str, Any]:
    existing_questions = existing_questions or []
    errors: list[str] = []
    warnings: list[str] = []
    question = str(item.get("question", "")).strip()
    answer = str(item.get("answer", "")).strip()
    choices = item.get("choices", [])

    if len(question) < 20:
        errors.append("문제 문장이 지나치게 짧습니다.")
    if not answer:
        errors.append("정답이 없습니다.")
    if item.get("question_type") == "객관식":
        if not isinstance(choices, list) or len(choices) != 5:
            errors.append("객관식 보기는 정확히 5개여야 합니다.")
        elif len({normalize_text(str(x)) for x in choices}) != 5:
            errors.append("객관식 보기에 중복이 있습니다.")

    source_similarity = ratio(normalize_text(source), normalize_text(question))
    if source_similarity >= 82:
        errors.append(f"원본과 너무 유사합니다({source_similarity}%).")
    elif source_similarity >= 70:
        warnings.append(f"원본과 유사도가 다소 높습니다({source_similarity}%).")

    duplicate_similarity = max(
        [ratio(normalize_text(question), normalize_text(q)) for q in existing_questions] or [0]
    )
    if duplicate_similarity >= 88:
        errors.append(f"기존 생성 문항과 중복 가능성이 큽니다({duplicate_similarity}%).")

    calc_ok, calc_note = verify_expression(
        str(item.get("verification_expression", "")),
        str(item.get("verification_expected", "")),
    )
    if not calc_ok:
        errors.append(calc_note)

    return {
        "passed": not errors,
        "score": max(0, 100 - 25 * len(errors) - 5 * len(warnings)),
        "errors": errors,
        "warnings": warnings,
        "source_similarity": source_similarity,
        "duplicate_similarity": duplicate_similarity,
        "calculation_check": calc_note,
    }
