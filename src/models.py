from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field

Difficulty = Literal["하", "중하", "중", "중상", "상"]
QuestionType = Literal["객관식", "주관식", "서술형"]


class SourceAnalysis(BaseModel):
    grade: str = "불명"
    semester: str = "불명"
    unit: str = "미분류"
    concept: str = "미분류"
    source_difficulty: Difficulty = "중"
    solution_strategy: str = ""
    required_knowledge: list[str] = Field(default_factory=list)
    visual_dependency: bool = False


class VariantProblem(BaseModel):
    title: str
    question_type: QuestionType
    question: str
    choices: list[str] = Field(default_factory=list)
    answer: str
    solution: str
    difficulty: Difficulty
    difficulty_reason: str = ""
    variation_points: list[str] = Field(default_factory=list)
    verification_expression: str = ""
    verification_expected: str = ""
    tags: list[str] = Field(default_factory=list)


class GenerationResult(BaseModel):
    usable: bool = True
    reason: str = ""
    analysis: SourceAnalysis
    variants: list[VariantProblem] = Field(default_factory=list)
