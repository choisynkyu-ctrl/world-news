"""RSS 피드에서 최근 기사 후보를 모은다."""
import html
import re
import time
from datetime import datetime, timedelta, timezone

import feedparser
import requests

from .config import FEEDS, LOOKBACK_HOURS, MAX_PER_FEED

UA = "feedparser/6.0 daily-news-digest/1.0"  # 일부 언론(Guardian)은 브라우저 위장 UA를 차단
_TAG = re.compile(r"<[^>]+>")


def _clean(text: str, limit: int) -> str:
    text = html.unescape(_TAG.sub(" ", text or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def _published(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            return datetime.fromtimestamp(time.mktime(t), tz=timezone.utc)
    return None


def collect() -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    items: list[dict] = []
    seen_titles: set[str] = set()

    for source, url in FEEDS:
        try:
            resp = requests.get(url, headers={"User-Agent": UA}, timeout=20)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
        except Exception as e:  # 한 소스가 실패해도 계속 진행
            print(f"[collect] {source} 실패: {e}")
            continue

        count = 0
        for entry in feed.entries:
            if count >= MAX_PER_FEED:
                break
            title = _clean(entry.get("title", ""), 200)
            link = entry.get("link", "")
            if not title or not link:
                continue
            pub = _published(entry)
            if pub and pub < cutoff:
                continue
            key = title.lower()
            if key in seen_titles:
                continue
            seen_titles.add(key)
            items.append({
                "id": len(items),
                "source": source,
                "title": title,
                "summary": _clean(entry.get("summary", ""), 300),
                "link": link,
                "published": pub.isoformat() if pub else None,
            })
            count += 1
        print(f"[collect] {source}: {count}건")

    print(f"[collect] 총 후보 {len(items)}건")
    return items
