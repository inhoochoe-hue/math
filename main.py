from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from src.difficulty import DIFFICULTIES
from src.document_reader import read_source
from src.exporter import save_answer_docx, save_exam_docx, save_json
from src.generator_service import generate_exam
from src.problem_splitter import split_problems


def parse_distribution(value: str) -> dict[str, int]:
    result = {level: 0 for level in DIFFICULTIES}
    for pair in value.split(","):
        level, count = pair.split(":", 1)
        level = level.strip()
        if level not in result:
            raise argparse.ArgumentTypeError(f"지원하지 않는 난이도: {level}")
        result[level] = int(count)
    return result


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="학원용 중등 수학 난이도별 문항 생성기")
    parser.add_argument("input", type=Path)
    parser.add_argument("--distribution", type=parse_distribution, default=parse_distribution("하:2,중하:4,중:7,중상:5,상:2"))
    parser.add_argument("--types", default="객관식,주관식")
    parser.add_argument("--source-limit", type=int, default=30)
    parser.add_argument("--title", default="중등 수학 유형별 테스트")
    parser.add_argument("--academy", default=os.getenv("ACADEMY_NAME", "OO수학학원"))
    parser.add_argument("--repairs", type=int, choices=[0, 1, 2], default=1)
    args = parser.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit(".env에 OPENAI_API_KEY를 설정하세요.")
    if not args.input.exists():
        raise SystemExit(f"파일이 없습니다: {args.input}")

    base = Path(__file__).resolve().parent
    text, _ = read_source(args.input, base / "workspace" / "work")
    problems = split_problems(text)[: args.source_limit]
    print(f"원본 문제 후보 {len(problems)}개")

    def progress(message: str, current: int, target: int) -> None:
        print(f"[{current}/{target}] {message}")

    records = generate_exam(
        source_file=args.input.name,
        source_problems=problems,
        distribution=args.distribution,
        question_types=[x.strip() for x in args.types.split(",") if x.strip()],
        bank_path=base / "workspace" / "problem_bank.db",
        max_repairs=args.repairs,
        progress=progress,
    )
    run_dir = base / "workspace" / "outputs" / datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    save_exam_docx(records, run_dir / "학생용_문제지.docx", args.title, args.academy)
    save_answer_docx(records, run_dir / "교사용_정답해설.docx", args.title, args.academy)
    save_json(records, run_dir / "전체_생성결과.json")
    print(f"완료: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
