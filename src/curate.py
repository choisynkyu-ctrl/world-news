"""Gemini(무료 등급)로 후보 기사 중 TOP 10을 고르고 한국어로 요약한다."""
import json
import os
import time

import requests

from .config import CATEGORIES, MODELS

API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

PROMPT = """당신은 한국 독자를 위한 국제뉴스 에디터입니다.
아래는 여러 해외 언론의 최근 24시간 기사 후보 목록입니다. 전 세계적으로 가장 중요한 이슈 10개를 고르세요.

선정 기준:
- 세계 정치·경제·안보·기술·기후 등에 미치는 영향의 크기를 최우선으로 봅니다.
- 여러 언론이 함께 다룬 사건일수록 중요도가 높을 가능성이 큽니다. 같은 사건을 다룬 후보들은 하나의 이슈로 묶고, 묶인 후보 번호를 모두 source_ids에 넣습니다.
- 한 분야나 한 지역에 치우치지 않게 균형을 맞추되, 중요도가 우선입니다.
- 연예·스포츠 단신, 생활 정보, 의견 칼럼은 정말 세계적인 사건이 아니면 제외합니다.

작성 규칙 (모두 한국어, 자연스러운 뉴스 문체):
- rank: 1이 가장 중요. 1~10 중복 없이.
- category: 다음 중 하나: {categories}
- region: 관련 지역 (예: 미국, 유럽, 중동, 동아시아, 글로벌)
- title: 30자 안팎의 기사 제목
- short_title: 카카오톡 알림용, 15자 이내의 아주 짧은 제목
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


def _format_candidates(items: list[dict]) -> str:
    lines = []
    for it in items:
        line = f"[{it['id']}] ({it['source']}) {it['title']}"
        if it["summary"]:
            line += f" — {it['summary']}"
        lines.append(line)
    return "\n".join(lines)


def _call(model: str, prompt: str) -> dict:
    """Gemini 호출. 일시 오류(429/5xx)는 재시도, 모델 없음(404)은 예외로 올려 다음 모델을 시도."""
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.3},
    }
    headers = {"x-goog-api-key": os.environ["GEMINI_API_KEY"]}
    for attempt in range(4):
        r = requests.post(API.format(model=model), headers=headers, json=body, timeout=180)
        if r.status_code == 200:
            data = r.json()
            text = "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])
            print(f"[curate] {model} 사용, tokens={data.get('usageMetadata', {})}")
            return json.loads(text)
        if r.status_code in (429, 500, 503) and attempt < 3:
            wait = 20 * (attempt + 1)
            print(f"[curate] {model} {r.status_code}, {wait}초 후 재시도")
            time.sleep(wait)
            continue
        raise RuntimeError(f"Gemini {model} 오류 {r.status_code}: {r.text[:500]}")
    raise RuntimeError("unreachable")


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


def curate(items: list[dict], date_label: str) -> dict:
    prompt = PROMPT.format(
        categories=", ".join(CATEGORIES), date=date_label,
        n=len(items), candidates=_format_candidates(items),
    )
    errors = []
    data = None
    for model in MODELS:  # 첫 모델이 없어졌거나 실패하면 다음 모델로
        try:
            data = _call(model, prompt)
            _validate(data)
            break
        except Exception as e:
            print(f"[curate] {model} 실패: {e}")
            errors.append(f"{model}: {e}")
            data = None
    if data is None:
        raise RuntimeError("모든 Gemini 모델 실패:\n" + "\n".join(errors))

    by_id = {it["id"]: it for it in items}
    stories = sorted(data["stories"], key=lambda s: s["rank"])[:10]
    for i, s in enumerate(stories, start=1):
        s["rank"] = i
        s["sources"] = [
            {"name": by_id[sid]["source"], "title": by_id[sid]["title"], "link": by_id[sid]["link"]}
            for sid in dict.fromkeys(s.pop("source_ids")) if isinstance(sid, int) and sid in by_id
        ]
    return {"headline_of_day": data.get("headline_of_day", ""), "stories": stories}
