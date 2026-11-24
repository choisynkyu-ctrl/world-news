"""날짜별 JSON으로 대시보드 HTML을 만든다."""
import json
from collections import Counter
from datetime import date
from html import escape

from .config import ARCHIVE_DIR, CATEGORIES, DATA_DIR, DOCS

WEEKDAYS = "월화수목금토일"

CAT_COLORS = {
    "정치/외교": "#3b6fd9",
    "분쟁/안보": "#d0453b",
    "경제/금융": "#1f9d6b",
    "기술/과학": "#7a4fd6",
    "기후/환경": "#2f9bb0",
    "보건": "#d6801f",
    "사회": "#b8478f",
    "기타": "#6b7280",
}

CSS = """
:root{--bg:#f5f6f8;--card:#fff;--text:#16181d;--muted:#606773;--line:#e3e6eb;--accent:#16181d;--chip:#eef0f3}
@media (prefers-color-scheme:dark){:root{--bg:#0f1115;--card:#181b21;--text:#eceef2;--muted:#9aa1ad;--line:#2a2e36;--accent:#eceef2;--chip:#22262e}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:Pretendard,-apple-system,"Apple SD Gothic Neo","Malgun Gothic",sans-serif;line-height:1.6;-webkit-font-smoothing:antialiased}
.wrap{max-width:1080px;margin:0 auto;padding:32px 16px 64px}
header{margin-bottom:24px}
.eyebrow{font-size:13px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
h1{font-size:30px;line-height:1.25;margin:6px 0 10px;letter-spacing:-.02em}
.lead{font-size:17px;color:var(--muted);margin:0;max-width:760px}
nav.days{display:flex;gap:8px;flex-wrap:wrap;margin-top:16px}
nav.days a{font-size:13px;color:var(--muted);text-decoration:none;border:1px solid var(--line);border-radius:999px;padding:4px 12px}
nav.days a:hover{color:var(--text);border-color:var(--muted)}
.filters{display:flex;gap:8px;flex-wrap:wrap;margin:24px 0 16px}
.filters button{font:inherit;font-size:13px;border:1px solid var(--line);background:var(--card);color:var(--text);border-radius:999px;padding:6px 14px;cursor:pointer}
.filters button[aria-pressed=true]{background:var(--accent);color:var(--bg);border-color:var(--accent)}
.filters .n{opacity:.6;margin-left:4px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px;display:flex;flex-direction:column;gap:10px}
.card.top{grid-column:1/-1}
.card.top h2{font-size:24px}
.meta{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--muted)}
.rank{font-weight:800;font-size:15px;color:var(--text);min-width:22px}
.cat{font-weight:600;padding:2px 8px;border-radius:6px;color:#fff}
h2{font-size:18px;line-height:1.4;margin:0;letter-spacing:-.01em}
.summary{margin:0;font-size:15px}
.why{margin:0;font-size:14px;color:var(--muted);border-left:3px solid var(--line);padding-left:10px}
.sources{display:flex;gap:6px;flex-wrap:wrap;margin-top:auto;padding-top:6px}
.sources a{font-size:12px;color:var(--muted);background:var(--chip);border-radius:6px;padding:3px 8px;text-decoration:none}
.sources a:hover{color:var(--text)}
footer{margin-top:40px;font-size:12px;color:var(--muted)}
@media (max-width:520px){h1{font-size:24px}.grid{grid-template-columns:1fr}.card.top h2{font-size:20px}}
"""

JS = """
const btns=document.querySelectorAll('.filters button');
btns.forEach(b=>b.addEventListener('click',()=>{
  btns.forEach(x=>x.setAttribute('aria-pressed',x===b));
  const c=b.dataset.cat;
  document.querySelectorAll('.card').forEach(el=>{el.hidden=!(c==='all'||el.dataset.cat===c)});
}));
"""


def _date_label(d: date) -> str:
    return f"{d.year}년 {d.month}월 {d.day}일 ({WEEKDAYS[d.weekday()]})"


def _card(s: dict) -> str:
    color = CAT_COLORS.get(s["category"], "#6b7280")
    sources = "".join(
        f'<a href="{escape(src["link"])}" target="_blank" rel="noopener" title="{escape(src["title"])}">{escape(src["name"])}</a>'
        for src in s.get("sources", [])
    )
    cls = "card top" if s["rank"] == 1 else "card"
    return f"""<article class="{cls}" data-cat="{escape(s['category'])}">
  <div class="meta"><span class="rank">{s['rank']:02d}</span><span class="cat" style="background:{color}">{escape(s['category'])}</span><span>{escape(s['region'])}</span></div>
  <h2>{escape(s['title'])}</h2>
  <p class="summary">{escape(s['summary'])}</p>
  <p class="why">{escape(s['why_it_matters'])}</p>
  <div class="sources">{sources}</div>
</article>"""


def render_page(data: dict, d: date, root: str, all_dates: list[date]) -> str:
    counts = Counter(s["category"] for s in data["stories"])
    filters = '<button data-cat="all" aria-pressed="true">전체<span class="n">10</span></button>' + "".join(
        f'<button data-cat="{escape(c)}" aria-pressed="false">{escape(c)}<span class="n">{counts[c]}</span></button>'
        for c in CATEGORIES if counts[c]
    )
    days = "".join(
        f'<a href="{root}archive/{x.isoformat()}.html">{x.month}/{x.day}</a>'
        for x in sorted(all_dates, reverse=True)[:14] if x != d
    )
    days_html = f'<nav class="days"><a href="{root}index.html">최신</a>{days}</nav>'
    cards = "\n".join(_card(s) for s in data["stories"])
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>세계 주요 뉴스 · {d.month}/{d.day}</title>
<meta property="og:title" content="세계 주요 뉴스 TOP 10 · {_date_label(d)}">
<meta property="og:description" content="{escape(data['headline_of_day'])}">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/pretendard@1.3.9/dist/web/static/pretendard.min.css">
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
<header>
  <div class="eyebrow">World Briefing · {_date_label(d)}</div>
  <h1>오늘의 세계 주요 뉴스 TOP 10</h1>
  <p class="lead">{escape(data['headline_of_day'])}</p>
  {days_html}
</header>
<div class="filters">{filters}</div>
<main class="grid">
{cards}
</main>
<footer>BBC, Guardian, NYT, Al Jazeera, NPR, DW, CNBC, Google News RSS를 바탕으로 AI(Google Gemini)가 선정·요약했습니다. 정확한 내용은 원문을 확인하세요.</footer>
</div>
<script>{JS}</script>
</body>
</html>"""


def save_and_render(data: dict, d: date) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    data = {**data, "date": d.isoformat()}
    (DATA_DIR / f"{d.isoformat()}.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    (DATA_DIR / "latest.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    render_all()


def render_all() -> None:
    files = sorted(p for p in DATA_DIR.glob("????-??-??.json"))
    all_dates = [date.fromisoformat(p.stem) for p in files]
    for p, d in zip(files, all_dates):
        data = json.loads(p.read_text(encoding="utf-8"))
        (ARCHIVE_DIR / f"{d.isoformat()}.html").write_text(
            render_page(data, d, "../", all_dates), encoding="utf-8")
    if files:
        latest = json.loads(files[-1].read_text(encoding="utf-8"))
        (DOCS / "index.html").write_text(
            render_page(latest, all_dates[-1], "", all_dates), encoding="utf-8")
    (DOCS / ".nojekyll").touch()
    print(f"[render] {len(files)}개 날짜 페이지 생성")
