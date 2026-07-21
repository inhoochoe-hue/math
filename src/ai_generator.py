from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI

from src.difficulty import DIFFICULTY_GUIDE
from src.models import GenerationResult

SYSTEM_PROMPT = """
너는 대한민국 중등 수학 전문 출제위원이다. 학원에서 실제 배포할 수 있는 새 문항을 만든다.
원본의 핵심 개념과 풀이 구조만 참고하고, 표현·상황·수치·조건·질문 방향을 충분히 바꾼다.

절대 규칙:
- 원문이나 보기를 그대로 복제하지 않는다.
- 숫자만 바꾼 문항은 만들지 않는다.
- 중학교 교육과정 범위를 벗어나지 않는다.
- 조건이 충분하고 정답이 하나로 결정되어야 한다.
- 객관식은 보기 5개, 정답 1개이며 오답은 실제 오개념에서 설계한다.
- 풀이와 정답을 직접 계산해 일치시킨다.
- 검산 가능한 산술식은 SymPy 문법 verification_expression과 결과 verification_expected를 제공한다.
- 식에는 ** 대신 ^를 쓰지 말고 SymPy용으로 **를 사용한다. 예: (3+5)/2, 2**3.
- 도형이나 그래프가 소실되어 해석 불가능하면 usable=false로 표시한다.
- 출력은 JSON 하나만 반환한다.
"""


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("AI 응답에서 JSON을 찾지 못했습니다.")
    return json.loads(text[start:end + 1])


def analyze_source(source_problem: str, model: str | None = None) -> dict[str, Any]:
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    model = model or os.environ.get("OPENAI_MODEL", "gpt-5-mini")
    prompt = f"""
다음 중등 수학 문제를 분석하라.

[원본]
{source_problem}

JSON 구조:
{{
  "grade": "중1/중2/중3/불명",
  "semester": "1학기/2학기/불명",
  "unit": "단원명",
  "concept": "세부 유형",
  "source_difficulty": "하/중하/중/중상/상",
  "solution_strategy": "풀이 구조",
  "required_knowledge": ["필요 개념"],
  "visual_dependency": false
}}
"""
    response = client.responses.create(model=model, instructions=SYSTEM_PROMPT, input=prompt)
    return _extract_json(response.output_text)


def generate_batch(
    source_problem: str,
    analysis: dict[str, Any],
    difficulty: str,
    count: int,
    question_types: list[str],
    model: str | None = None,
) -> list[dict[str, Any]]:
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    model = model or os.environ.get("OPENAI_MODEL", "gpt-5-mini")
    guide = DIFFICULTY_GUIDE[difficulty]
    prompt = f"""
다음 원본의 개념과 풀이 구조를 바탕으로 새로운 문항 {count}개를 작성하라.

[원본]
{source_problem}

[분석]
{json.dumps(analysis, ensure_ascii=False)}

[목표 난이도]
{difficulty}: {guide}

[허용 문항 형식]
{', '.join(question_types)}

각 문항은 서로 다른 변형 전략을 사용한다. 상황 변경만 하지 말고 조건 결합, 역문제,
질문 대상 변경, 자료 표현 변경 중 적어도 하나를 포함한다.

JSON 구조:
{{
  "variants": [
    {{
      "title": "유형명",
      "question_type": "객관식/주관식/서술형",
      "question": "완전한 문제",
      "choices": ["① ...", "② ...", "③ ...", "④ ...", "⑤ ..."],
      "answer": "정답",
      "solution": "교사가 검토할 수 있는 단계별 풀이",
      "difficulty": "{difficulty}",
      "difficulty_reason": "이 난이도로 판정한 이유",
      "variation_points": ["변형 내용"],
      "verification_expression": "SymPy로 계산 가능한 최종 검산식 또는 빈 문자열",
      "verification_expected": "검산식의 기대 숫자 또는 빈 문자열",
      "tags": ["단원", "세부유형"]
    }}
  ]
}}
주관식·서술형은 choices를 빈 배열로 둔다.
"""
    response = client.responses.create(model=model, instructions=SYSTEM_PROMPT, input=prompt)
    data = _extract_json(response.output_text)
    return list(data.get("variants", []))


def repair_variant(
    source_problem: str,
    analysis: dict[str, Any],
    item: dict[str, Any],
    errors: list[str],
    model: str | None = None,
) -> dict[str, Any]:
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    model = model or os.environ.get("OPENAI_MODEL", "gpt-5-mini")
    prompt = f"""
아래 생성 문항은 품질검사에 실패했다. 오류를 모두 고쳐 동일 JSON 구조의 문항 하나만 반환하라.
원본과 더 멀리 변형하되 개념은 유지한다.

[원본]
{source_problem}
[분석]
{json.dumps(analysis, ensure_ascii=False)}
[생성 문항]
{json.dumps(item, ensure_ascii=False)}
[오류]
{json.dumps(errors, ensure_ascii=False)}
"""
    response = client.responses.create(model=model, instructions=SYSTEM_PROMPT, input=prompt)
    return _extract_json(response.output_text)


def generate_variants(source_problem: str, count: int, target_difficulty: str, model: str | None = None) -> dict[str, Any]:
    """기존 CLI 호환 함수."""
    analysis = analyze_source(source_problem, model=model)
    levels = [target_difficulty] if target_difficulty in DIFFICULTY_GUIDE else [analysis.get("source_difficulty", "중")]
    variants: list[dict[str, Any]] = []
    variants.extend(generate_batch(source_problem, analysis, levels[0], count, ["객관식", "주관식", "서술형"], model))
    result = {"usable": not analysis.get("visual_dependency", False), "reason": "", "analysis": analysis, "variants": variants}
    return GenerationResult.model_validate(result).model_dump()
