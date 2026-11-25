"""사용법:
  python -m src.main build    # 뉴스 수집 → Claude 선정/요약 → docs/ 대시보드 생성
  python -m src.main notify   # docs/data/latest.json 내용을 카카오톡으로 전송
  python -m src.main render   # 저장된 JSON으로 HTML만 다시 생성 (API 호출 없음)
"""
import json
import os
import sys
from datetime import date, datetime

from .config import DATA_DIR, KST


def today_kst() -> date:
    return datetime.now(KST).date()


def cmd_build() -> None:
    from .collect import collect
    from .curate import curate
    from .digest import digest
    from .render import save_and_render

    d = today_kst()
    items = collect()
    if len(items) < 20:
        raise SystemExit(f"후보 기사가 너무 적습니다 ({len(items)}건). RSS 소스를 확인하세요.")
    data = curate(items, d.isoformat())
    data["digest"] = digest(data, d)
    save_and_render(data, d)


def cmd_notify() -> None:
    from .kakao import notify

    data = json.loads((DATA_DIR / "latest.json").read_text(encoding="utf-8"))
    d = date.fromisoformat(data["date"])
    if d != today_kst():
        raise SystemExit(f"latest.json 날짜({d})가 오늘이 아닙니다. build가 실패했는지 확인하세요.")
    url = os.environ["DASHBOARD_URL"]
    notify(data, d, url)


def cmd_render() -> None:
    from .render import render_all
    render_all()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    {"build": cmd_build, "notify": cmd_notify, "render": cmd_render}[cmd]()
