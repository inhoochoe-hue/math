from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Callable

from src.ai_generator import analyze_source, generate_batch, repair_variant
from src.difficulty import DIFFICULTIES
from src.quality import assess_variant
from src.storage import ProblemBank

ProgressCallback = Callable[[str, int, int], None]


def generate_exam(
    source_file: str,
    source_problems: list[str],
    distribution: dict[str, int],
    question_types: list[str],
    bank_path: Path,
    max_repairs: int = 1,
    progress: ProgressCallback | None = None,
) -> list[dict[str, Any]]:
    targets: list[str] = []
    for level in DIFFICULTIES:
        targets += [level] * int(distribution.get(level, 0))
    if not targets:
        raise ValueError("생성할 문제 수가 0개입니다.")
    if not source_problems:
        raise ValueError("원본 문제를 찾지 못했습니다.")

    bank = ProblemBank(bank_path)
    analysis_cache: dict[int, dict[str, Any]] = {}
    generated: list[dict[str, Any]] = []
    questions: list[str] = []
    total = len(targets)

    grouped = Counter(targets)
    task_index = 0
    source_cursor = 0
    for difficulty, count in grouped.items():
        remaining = count
        while remaining > 0:
            source_index = source_cursor % len(source_problems)
            source_cursor += 1
            source = source_problems[source_index]
            if source_index not in analysis_cache:
                analysis_cache[source_index] = analyze_source(source)
            analysis = analysis_cache[source_index]
            if analysis.get("visual_dependency"):
                continue

            batch_count = min(remaining, 3)
            candidates = generate_batch(source, analysis, difficulty, batch_count, question_types)
            source_id = bank.add_source(source_file, source_index + 1, source, analysis)

            for item in candidates:
                quality = assess_variant(source, item, questions)
                repair_count = 0
                while not quality["passed"] and repair_count < max_repairs:
                    item = repair_variant(source, analysis, item, quality["errors"])
                    quality = assess_variant(source, item, questions)
                    repair_count += 1

                record = {
                    "source_number": source_index + 1,
                    "source_problem": source,
                    "analysis": analysis,
                    "variant": item,
                    "quality": quality,
                }
                generated.append(record)
                if quality["passed"]:
                    questions.append(item.get("question", ""))
                bank.add_variant(source_id, analysis, item, quality)
                task_index += 1
                if progress:
                    progress(f"{difficulty} 문항 생성", task_index, total)
                if task_index >= total:
                    return generated
            remaining -= len(candidates)
    return generated
