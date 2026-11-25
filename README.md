# 🌍 매일 아침 세계 주요 뉴스 TOP 10

매일 오전 7시 무렵, 해외 주요 언론 RSS(BBC · Guardian · NYT · Al Jazeera · NPR · DW · CNBC · Google News 종합/World/Business)에서
최근 30시간 기사를 모아 **Google Gemini(무료 등급)** 가 중요 이슈 15개를 고르고 한국어로 요약한 뒤,
**Gemini 중요도 60% + 보도한 언론사 수 40%** 점수로 TOP 10을 정합니다.
대시보드 상단에는 일간(오늘) · 주간(최근 7일) · 월간(최근 30일) 흐름 요약이 함께 표시됩니다.
(주간은 2일치, 월간은 8일치 이상 데이터가 쌓이면 나타납니다.)
결과는 **GitHub Pages 대시보드**에 올라가고, **카카오톡 '나와의 채팅'** 으로 헤드라인과 대시보드 링크가 옵니다.

```
GitHub Actions (06:45 KST)
  ├─ RSS 수집 (src/collect.py)
  ├─ Gemini 선정·요약 (src/curate.py)  → docs/data/YYYY-MM-DD.json
  ├─ 대시보드 생성 (src/render.py)      → docs/index.html, docs/archive/
  ├─ git push → GitHub Pages 반영
  └─ 카카오톡 전송 (src/kakao.py)       → 제목 한 줄 + 대시보드 버튼
```

**비용: 0원.** GitHub Actions·Pages(공개 저장소), Gemini API 무료 등급, 카카오 메시지 API 모두 무료입니다.
(Gemini 무료 등급은 입력 내용이 Google 제품 개선에 쓰일 수 있지만, 공개 뉴스 기사만 보내므로 문제없습니다.)

## 필요한 키

| GitHub Secret | 어디서 |
|---|---|
| `GEMINI_API_KEY` | [aistudio.google.com](https://aistudio.google.com) → Get API key (Google 계정으로 무료 발급) |
| `KAKAO_REST_API_KEY` | Kakao Developers 앱 → 앱 키 |
| `KAKAO_CLIENT_SECRET` | (선택) Kakao 앱 → 보안 → Client Secret |
| `KAKAO_REFRESH_TOKEN` | `scripts/setup_secrets.ps1` 실행 시 자동 발급 |
| `GH_PAT` | (선택) 카카오 토큰 2개월 자동 갱신용. 스크립트가 자동 등록 |

모든 Secret은 아래 스크립트 한 번으로 등록됩니다 (GitHub CLI 로그인 필요):
```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_secrets.ps1
```

## 카카오 앱 설정
1. [developers.kakao.com](https://developers.kakao.com) → 내 애플리케이션 → 애플리케이션 추가
2. 카카오 로그인 활성화 ON, Redirect URI `https://localhost:5000`
3. 동의항목 → `카카오톡 메시지 전송(talk_message)` 선택 동의
4. 플랫폼 → Web 사이트 도메인 `https://<GitHub아이디>.github.io`

## 수동 실행 · 수정
- 지금 바로 실행: 저장소 **Actions → Daily World News → Run workflow**
- 소스 변경: `src/config.py`의 `FEEDS`
- 선정 기준·문체: `src/curate.py`의 `PROMPT`
- 보도량 반영 비중: `src/config.py`의 `COVERAGE_WEIGHT`(기본 0.4), `COVERAGE_CAP`(6곳이면 만점), `CANDIDATE_ISSUES`(Gemini 1차 후보 15개)
- 모델: `src/config.py`의 `MODELS` (앞에서부터 시도)
- 도착 시각: 06:45 시작 예약. GitHub 스케줄은 수십 분 늦어질 수 있어 보통 7시 전후 도착
