from __future__ import annotations

import os
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from src.difficulty import DIFFICULTIES, default_distribution
from src.document_reader import read_source
from src.exporter import save_answer_docx, save_exam_docx, save_json
from src.generator_service import generate_exam
from src.problem_splitter import split_problems

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "workspace" / "uploads"
OUTPUT_DIR = BASE_DIR / "workspace" / "outputs"
BANK_PATH = BASE_DIR / "workspace" / "problem_bank.db"

st.set_page_config(page_title="학원용 중등 수학 문항 생성기", page_icon="📘", layout="wide")
st.title("📘 학원용 중등 수학 문항 생성기")
st.caption("기출·자체교재의 풀이 구조를 분석해 난이도별 신규 문항과 정답지를 생성합니다.")

if not os.getenv("OPENAI_API_KEY"):
    st.error(".env 파일에 OPENAI_API_KEY를 설정한 뒤 다시 실행하세요.")
    st.stop()

with st.sidebar:
    st.header("시험지 설정")
    academy = st.text_input("학원명", os.getenv("ACADEMY_NAME", "OO수학학원"))
    exam_title = st.text_input("시험지 제목", "중등 수학 유형별 테스트")
    total = st.number_input("총 출제 문항", min_value=1, max_value=100, value=20)
    st.caption("난이도별 문항 수의 합이 총 문항 수와 같아야 합니다.")

    defaults = default_distribution(int(total))
    distribution: dict[str, int] = {}
    for level in DIFFICULTIES:
        distribution[level] = st.number_input(
            f"{level} 문항", min_value=0, max_value=100, value=defaults[level], key=f"difficulty_{level}"
        )

    qtypes = st.multiselect("문항 형식", ["객관식", "주관식", "서술형"], default=["객관식", "주관식"])
    source_limit = st.number_input("분석할 원본 문제 수", min_value=1, max_value=200, value=30)
    repairs = st.selectbox("자동 재검수 횟수", [0, 1, 2], index=1)

uploaded = st.file_uploader("HWP/HWPX/DOCX/TXT 문제 자료를 올리세요", type=["hwp", "hwpx", "docx", "txt"])

if uploaded:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = Path(uploaded.name).name
    upload_path = UPLOAD_DIR / safe_name
    upload_path.write_bytes(uploaded.getbuffer())
    st.success(f"업로드 완료: {safe_name}")

    if st.button("문제 추출 미리보기"):
        try:
            text, _ = read_source(upload_path, BASE_DIR / "workspace" / "work")
            problems = split_problems(text)
            st.session_state["source_text"] = text
            st.session_state["source_problems"] = problems
            st.info(f"문제 후보 {len(problems)}개를 찾았습니다.")
            for i, problem in enumerate(problems[:5], 1):
                with st.expander(f"원본 문제 {i}"):
                    st.text(problem[:2000])
        except Exception as exc:
            st.exception(exc)

    can_generate = sum(distribution.values()) == int(total) and bool(qtypes)
    if not can_generate:
        st.warning(f"현재 난이도별 합계는 {sum(distribution.values())}문항입니다. 총 {int(total)}문항과 맞춰주세요.")

    if st.button("난이도별 시험지 생성", type="primary", disabled=not can_generate):
        try:
            text, _ = read_source(upload_path, BASE_DIR / "workspace" / "work")
            problems = split_problems(text)[: int(source_limit)]
            progress_bar = st.progress(0)
            status = st.empty()

            def on_progress(message: str, current: int, target: int) -> None:
                status.write(f"{message}: {current}/{target}")
                progress_bar.progress(min(current / target, 1.0))

            records = generate_exam(
                source_file=safe_name,
                source_problems=problems,
                distribution=distribution,
                question_types=qtypes,
                bank_path=BANK_PATH,
                max_repairs=int(repairs),
                progress=on_progress,
            )

            run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            run_dir = OUTPUT_DIR / run_id
            run_dir.mkdir(parents=True, exist_ok=True)
            exam_path = run_dir / "학생용_문제지.docx"
            answer_path = run_dir / "교사용_정답해설.docx"
            json_path = run_dir / "전체_생성결과.json"
            save_exam_docx(records, exam_path, exam_title, academy)
            save_answer_docx(records, answer_path, exam_title, academy)
            save_json(records, json_path)

            passed = [r for r in records if r.get("quality", {}).get("passed")]
            failed = [r for r in records if not r.get("quality", {}).get("passed")]
            st.session_state["latest_records"] = records
            st.session_state["latest_files"] = (exam_path, answer_path, json_path)
            st.success(f"완료: 사용 가능 {len(passed)}문항 / 검토 필요 {len(failed)}문항")
        except Exception as exc:
            st.exception(exc)

if "latest_records" in st.session_state:
    records = st.session_state["latest_records"]
    rows = []
    for i, record in enumerate(records, 1):
        item = record.get("variant", {})
        quality = record.get("quality", {})
        rows.append({
            "번호": i,
            "단원": record.get("analysis", {}).get("unit", ""),
            "난이도": item.get("difficulty", ""),
            "형식": item.get("question_type", ""),
            "문제": item.get("question", "")[:80],
            "품질점수": quality.get("score", 0),
            "통과": quality.get("passed", False),
        })
    st.subheader("생성 결과 검토")
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    exam_path, answer_path, json_path = st.session_state["latest_files"]
    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button("학생용 문제지 다운로드", exam_path.read_bytes(), exam_path.name)
    with c2:
        st.download_button("교사용 정답지 다운로드", answer_path.read_bytes(), answer_path.name)
    with c3:
        st.download_button("JSON 원본 다운로드", json_path.read_bytes(), json_path.name)
