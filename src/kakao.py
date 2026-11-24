"""카카오톡 '나에게 보내기'로 TOP 10을 보낸다."""
import json
import os
from datetime import date

import requests

TOKEN_URL = "https://kauth.kakao.com/oauth/token"
MEMO_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
TEXT_LIMIT = 200  # 텍스트 템플릿 최대 글자 수


def refresh_access_token() -> str:
    """refresh token으로 access token을 새로 받는다.
    refresh token이 갱신되어 돌아오면 NEW_REFRESH_TOKEN_FILE에 저장해 워크플로가 Secret을 업데이트하게 한다."""
    payload = {
        "grant_type": "refresh_token",
        "client_id": os.environ["KAKAO_REST_API_KEY"],
        "refresh_token": os.environ["KAKAO_REFRESH_TOKEN"],
    }
    if os.environ.get("KAKAO_CLIENT_SECRET"):
        payload["client_secret"] = os.environ["KAKAO_CLIENT_SECRET"]
    resp = requests.post(TOKEN_URL, data=payload, timeout=20)
    if resp.status_code != 200:
        raise RuntimeError(f"카카오 토큰 갱신 실패 {resp.status_code}: {resp.text}")
    tok = resp.json()

    new_refresh = tok.get("refresh_token")
    out = os.environ.get("NEW_REFRESH_TOKEN_FILE")
    if new_refresh and out:
        with open(out, "w", encoding="utf-8") as f:
            f.write(new_refresh)
        print("[kakao] refresh token이 갱신되었습니다 (Secret 업데이트 예정)")
    return tok["access_token"]


def _send(access_token: str, template: dict) -> None:
    resp = requests.post(
        MEMO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        data={"template_object": json.dumps(template, ensure_ascii=False)},
        timeout=20,
    )
    if resp.status_code != 200 or resp.json().get("result_code") != 0:
        raise RuntimeError(f"카카오 메시지 전송 실패 {resp.status_code}: {resp.text}")


def _text_template(text: str, url: str) -> dict:
    if len(text) > TEXT_LIMIT:
        text = text[: TEXT_LIMIT - 1] + "…"
    return {
        "object_type": "text",
        "text": text,
        "link": {"web_url": url, "mobile_web_url": url},
        "button_title": "대시보드 열기",
    }


def build_messages(data: dict, d: date) -> list[str]:
    stories = data["stories"]
    head = f"🌍 {d.month}/{d.day} 세계 주요 뉴스 TOP 10"
    lines1 = [head, ""] + [f"{s['rank']}. {s['short_title']}" for s in stories[:5]]
    lines2 = [f"{s['rank']}. {s['short_title']}" for s in stories[5:10]]
    return ["\n".join(lines1), "\n".join(lines2)]


def notify(data: dict, d: date, dashboard_url: str) -> None:
    token = refresh_access_token()
    for text in build_messages(data, d):
        _send(token, _text_template(text, dashboard_url))
    print("[kakao] 전송 완료")
