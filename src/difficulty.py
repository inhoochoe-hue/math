from __future__ import annotations

DIFFICULTIES = ["하", "중하", "중", "중상", "상"]

DIFFICULTY_GUIDE = {
    "하": "핵심 개념을 바로 적용한다. 계산 단계 1~2개, 함정 없음, 수치가 단순하다.",
    "중하": "기본 개념을 적용하되 간단한 식 변형 또는 조건 해석이 한 번 필요하다.",
    "중": "두 개 이상의 조건을 연결하거나 표준적인 응용 상황을 식으로 바꾸어야 한다.",
    "중상": "조건을 역으로 해석하거나 여러 단계의 식 변형, 경우 구분 중 하나가 필요하다.",
    "상": "핵심 개념은 교육과정 안에 있으나 조건 결합, 역문제, 숨은 제약, 복합 추론이 필요하다.",
}


def expand_distribution(distribution: dict[str, int]) -> list[str]:
    result: list[str] = []
    for level in DIFFICULTIES:
        result.extend([level] * max(int(distribution.get(level, 0)), 0))
    return result


def default_distribution(total: int) -> dict[str, int]:
    # 학원 일일 테스트용 균형 배분
    weights = {"하": 0.10, "중하": 0.20, "중": 0.35, "중상": 0.25, "상": 0.10}
    raw = {k: int(total * v) for k, v in weights.items()}
    remainder = total - sum(raw.values())
    order = ["중", "중상", "중하", "상", "하"]
    for i in range(remainder):
        raw[order[i % len(order)]] += 1
    return raw
