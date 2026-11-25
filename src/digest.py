"""저장된 날짜별 TOP 10을 모아 주간(최근 7일)·월간(최근 30일) 흐름을 요약한다."""
import json
from datetime import date, timedelta

from .config import DATA_DIR
from .curate import generate

# (키, 기간 일수, 요약하려면 필요한 최소 데이터 일수)
PERIODS = [("weekly", 7, 2), ("monthly", 30, 8)]

PROMPT = """당신은 한국 독자를 위한 국제뉴스 에디터입니다.
아래는 날짜별 세계 주요 뉴스 TOP 10 목록입니다. 기간별로 세계 뉴스의 큰 흐름을 요약하세요.

작성 규칙 (한국어, 자연스러운 뉴스 문체):
- 각 요약은 2~3문장. 날짜별 나열이 아니라, 여러 날에 걸쳐 이어진 핵심 흐름과 가장 큰 사건 위주로 씁니다.
- 목록에 있는 정보만 사용하고, 없는 수치나 사실을 지어내지 마세요.
- 요청된 기간의 키만 출력합니다.

요청 기간: {periods}

아래 형식의 JSON만 출력하세요:
{{{keys}}}

{sections}
"""

LABELS = {"weekly": "최근 7일", "monthly": "최근 30일"}


def _load(d: date, days: int, today: dict) -> list[tuple[date, dict]]:
    """d를 포함한 최근 days일의 데이터 (오늘 것은 아직 저장 전이라 직접 받음)."""
    out = [(d, today)]
    for i in range(1, days):
        x = d - timedelta(days=i)
        p = DATA_DIR / f"{x.isoformat()}.json"
        if p.exists():
            out.append((x, json.loads(p.read_text(encoding="utf-8"))))
    return sorted(out, key=lambda t: t[0])


def _format(days: list[tuple[date, dict]]) -> str:
    lines = []
    for d, data in days:
        lines.append(f"## {d.isoformat()}")
        lines += [f"{s['rank']}. [{s['category']}] {s['title']} — {s['summary']}" for s in data["stories"]]
    return "\n".join(lines)


def digest(today: dict, d: date) -> dict:
    """{"weekly": {"text": ..., "days": n}, "monthly": {...}}. 데이터가 부족한 기간은 뺀다.
    요약은 부가 기능이라 실패해도 빈 dict를 돌려주고 빌드는 계속한다."""
    periods = {}
    for key, span, need in PERIODS:
        days = _load(d, span, today)
        if len(days) >= need:
            periods[key] = days
    # 월간이 주간과 같은 날짜들만 담고 있으면 의미가 없으므로 뺀다
    if "monthly" in periods and len(periods["monthly"]) == len(periods.get("weekly", [])):
        del periods["monthly"]
    if not periods:
        print("[digest] 쌓인 데이터가 부족해 주간·월간 요약을 건너뜁니다")
        return {}

    # 월간 목록이 주간 목록을 포함하므로 가장 긴 기간의 데이터만 보내고, 기간별 범위를 알려준다
    longest = max(periods.values(), key=len)
    period_desc = ", ".join(
        f"{k}({LABELS[k]}: {v[0][0].isoformat()} ~ {v[-1][0].isoformat()})" for k, v in periods.items()
    )
    prompt = PROMPT.format(
        periods=period_desc,
        keys=", ".join(f'"{k}": "..."' for k in periods),
        sections=_format(longest),
    )

    def validate(data: dict) -> None:
        for k in periods:
            if not isinstance(data.get(k), str) or not data[k].strip():
                raise ValueError(f"{k} 요약 누락: {data!r:.200}")

    try:
        data = generate(prompt, validate, rounds=3, tag="digest")
    except Exception as e:
        print(f"[digest] 요약 실패, 건너뜀: {e}")
        return {}
    return {k: {"text": data[k].strip(), "days": len(v)} for k, v in periods.items()}
