"""Gemini(무료 등급)로 후보 이슈를 고르고 요약한 뒤, 보도 언론사 수를 더한 점수로 TOP 10을 정한다."""
import json
import os
import time

import requests

from .config import (CANDIDATE_ISSUES, CATEGORIES, COVERAGE_CAP, COVERAGE_WEIGHT,
                     FEEDS, MODELS, OUTLET_ALIASES, TRUSTED_OUTLETS)

API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

PROMPT = """당신은 한국 독자를 위한 국제뉴스 에디터입니다.
아래는 여러 해외 언론의 최근 24시간 기사 후보 목록입니다. 전 세계적으로 가장 중요한 이슈 {k}개를 고르세요.

선정 기준:
- 세계 정치·경제·안보·기술·기후 등에 미치는 영향의 크기를 최우선으로 봅니다.
- 여러 언론이 함께 다룬 사건일수록 중요도가 높을 가능성이 큽니다. 같은 사건을 다룬 후보들은 하나의 이슈로 묶고, 묶인 후보 번호를 모두 source_ids에 넣습니다.
  단, 같은 구체적 사건만 묶고 넓은 주제(예: '트럼프 관련 소식 전반')로 여러 사건을 한데 묶지 마세요.
- 한 분야나 한 지역에 치우치지 않게 균형을 맞추되, 중요도가 우선입니다.
- 연예·스포츠 단신, 생활 정보, 의견 칼럼은 정말 세계적인 사건이 아니면 제외합니다.

작성 규칙 (모두 한국어, 자연스러운 뉴스 문체):
- rank: 1이 가장 중요. 1~{k} 중복 없이.
- category: 다음 중 하나: {categories}
- region: 관련 지역 (예: 미국, 유럽, 중동, 동아시아, 글로벌)
- title: 30자 안팎의 기사 제목
- short_title: 공백 포함 12자 이내의 아주 짧은 제목
- summary: 핵심 사실 2~3문장. 후보 목록에 있는 정보만 사용하고, 없는 수치나 사실을 지어내지 마세요.
- why_it_matters: 이 뉴스가 왜 중요한지, 한국이나 세계에 주는 의미 한 문장
- headline_of_day: 오늘 세계 뉴스 흐름을 한 문장으로 요약

아래 형식의 JSON만 출력하세요:
{{"headline_of_day": "...", "stories": [{{"rank": 1, "category": "...", "region": "...", "title": "...", "short_title": "...", "summary": "...", "why_it_matters": "...", "source_ids": [0, 5]}}]}}

오늘 날짜(KST): {date}

기사 후보 {n}건:
{candidates}
"""

REQUIRED = ["rank", "category", "region", "title", "short_title", "summary", "why_it_matters", "source_ids"]


def _outlet(it: dict) -> str:
    """기사의 언론사 이름 (예전 데이터는 outlet이 없어 피드 이름으로 대신)."""
    name = it.get("outlet") or it["source"]
    return OUTLET_ALIASES.get(name, name)


# 보도량에 세는 언론사 = 직접 받는 피드의 언론사 + 허용 목록
COUNTED_OUTLETS = TRUSTED_OUTLETS | {OUTLET_ALIASES.get(n, n) for n, _ in FEEDS if not n.startswith("Google News")}


def _score(stories: list[dict]) -> list[dict]:
    """Gemini 순위와 보도 언론사 수를 합친 점수로 다시 정렬한다.

    중요도 = Gemini 순위를 0~1로 환산 (1위=1, 꼴찌=0)
    보도량 = (주요 언론사 수 - 1) / (COVERAGE_CAP - 1), 최대 1
    점수   = (1 - COVERAGE_WEIGHT) × 중요도 + COVERAGE_WEIGHT × 보도량
    """
    n = len(stories)
    for i, s in enumerate(stories):
        outlets = len({src["name"] for src in s["sources"] if src["name"] in COUNTED_OUTLETS})
        importance = 1.0 if n == 1 else (n - 1 - i) / (n - 1)
        coverage = (min(max(outlets, 1), COVERAGE_CAP) - 1) / (COVERAGE_CAP - 1)
        s["llm_rank"] = i + 1
        s["outlets"] = outlets
        s["score"] = round((1 - COVERAGE_WEIGHT) * importance + COVERAGE_WEIGHT * coverage, 3)
    # 점수가 같으면 Gemini 순위가 높은 쪽
    return sorted(stories, key=lambda s: (-s["score"], s["llm_rank"]))


def _format_candidates(items: list[dict]) -> str:
    lines = []
    for it in items:
        line = f"[{it['id']}] ({_outlet(it)}) {it['title']}"
        if it["summary"]:
            line += f" — {it['summary']}"
        lines.append(line)
    return "\n".join(lines)


class Busy(Exception):
    """일시적 혼잡(429/5xx) — 나중에 다시 시도할 가치가 있음."""


def _call(model: str, prompt: str) -> dict:
    """Gemini 1회 호출. 혼잡이면 Busy, 그 밖의 오류(모델 없음 등)는 RuntimeError."""
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.3},
    }
    headers = {"x-goog-api-key": os.environ["GEMINI_API_KEY"]}
    try:
        r = requests.post(API.format(model=model), headers=headers, json=body, timeout=300)
    except requests.RequestException as e:
        raise Busy(str(e))
    if r.status_code == 200:
        data = r.json()
        text = "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
        print(f"[curate] {model} 사용, tokens={data.get('usageMetadata', {})}")
        return json.loads(text)
    if r.status_code in (429, 500, 502, 503, 504):
        raise Busy(f"{r.status_code}")
    raise RuntimeError(f"오류 {r.status_code}: {r.text[:300]}")


def _validate(data: dict) -> None:
    stories = data.get("stories")
    if not isinstance(stories, list) or len(stories) < 5:
        raise ValueError(f"stories가 부족합니다: {stories!r:.200}")
    for s in stories:
        missing = [k for k in REQUIRED if k not in s]
        if missing:
            raise ValueError(f"필드 누락 {missing}: {s!r:.200}")
        if s["category"] not in CATEGORIES:
            s["category"] = "기타"


def generate(prompt: str, validate, rounds: int = 8, tag: str = "curate") -> dict:
    """모델을 번갈아 가며 Gemini를 호출한다. 무료 등급은 혼잡 시 503을 자주 주므로
    rounds번까지 기다렸다 재시도한다 (8회면 최대 약 20분)."""
    models = list(MODELS)
    errors: list[str] = []
    for rnd in range(rounds):
        for model in list(models):
            try:
                data = _call(model, prompt)
                validate(data)
                return data
            except Busy as e:
                print(f"[{tag}] {model} 혼잡({e})")
            except Exception as e:  # 모델 없음·응답 형식 오류 → 이 모델은 제외
                print(f"[{tag}] {model} 실패: {e}")
                errors.append(f"{model}: {e}")
                models.remove(model)
        if not models or rnd == rounds - 1:
            break
        wait = min(30 * (rnd + 1), 240)
        print(f"[{tag}] 모든 모델 혼잡, {wait}초 후 다시 시도 ({rnd + 1}/{rounds})")
        time.sleep(wait)
    raise RuntimeError("Gemini 호출 실패 (혼잡 또는 오류):\n" + "\n".join(errors))


def curate(items: list[dict], date_label: str) -> dict:
    prompt = PROMPT.format(
        k=CANDIDATE_ISSUES, categories=", ".join(CATEGORIES), date=date_label,
        n=len(items), candidates=_format_candidates(items),
    )
    data = generate(prompt, _validate)

    by_id = {it["id"]: it for it in items}
    stories = sorted(data["stories"], key=lambda s: s["rank"])
    for s in stories:
        s["sources"] = [
            {"name": _outlet(by_id[sid]), "title": by_id[sid]["title"], "link": by_id[sid]["link"]}
            for sid in dict.fromkeys(s.pop("source_ids")) if isinstance(sid, int) and sid in by_id
        ]
    stories = _score(stories)[:10]
    for i, s in enumerate(stories, start=1):
        s["rank"] = i
        print(f"[curate] {i}위 (Gemini {s['llm_rank']}위, 언론사 {s['outlets']}곳, 점수 {s['score']}) {s['title']}")
    return {"headline_of_day": data.get("headline_of_day", ""), "stories": stories}
