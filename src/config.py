"""설정값: 뉴스 소스, 모델, 경로."""
from pathlib import Path
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"              # GitHub Pages 루트
DATA_DIR = DOCS / "data"          # 날짜별 JSON
ARCHIVE_DIR = DOCS / "archive"    # 날짜별 HTML

# Gemini 무료 등급 모델. 앞에서부터 시도하고, 없어지거나 실패하면 다음 모델 사용
MODELS = ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-flash-latest", "gemini-2.5-flash"]

# 최근 몇 시간 이내 기사만 후보로 사용
LOOKBACK_HOURS = 30
# 소스당 최대 후보 수
MAX_PER_FEED = 25

# 해외 주요 언론 RSS (공개 피드)
FEEDS = [
    ("BBC", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("BBC Business", "https://feeds.bbci.co.uk/news/business/rss.xml"),
    ("The Guardian", "https://www.theguardian.com/world/rss"),
    ("NYT", "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"),
    ("NYT Business", "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml"),
    ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
    ("NPR", "https://feeds.npr.org/1004/rss.xml"),
    ("DW", "https://rss.dw.com/rdf/rss-en-world"),
    ("CNBC", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100727362"),
    # Google News: 여러 매체 기사를 모은 피드. 원래 언론사가 주요 언론(TRUSTED_OUTLETS)이면 보도량에 센다
    ("Google News", "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"),
    ("Google News World", "https://news.google.com/rss/headlines/section/topic/WORLD?hl=en-US&gl=US&ceid=US:en"),
    ("Google News Business", "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-US&gl=US&ceid=US:en"),
]

# 같은 언론사로 볼 이름들 (보도 건수는 언론사 단위로 센다)
OUTLET_ALIASES = {
    "BBC Business": "BBC", "BBC News": "BBC",
    "NYT Business": "NYT", "The New York Times": "NYT",
    "Al Jazeera English": "Al Jazeera", "POLITICO.eu": "Politico", "POLITICO": "Politico",
    "AP News": "AP", "Associated Press": "AP", "The Associated Press": "AP",
    "The Wall Street Journal": "WSJ", "Financial Times": "FT", "The Washington Post": "Washington Post",
    "Bloomberg.com": "Bloomberg", "The Economist": "Economist", "Nikkei Asia": "Nikkei",
    "South China Morning Post": "SCMP", "The Japan Times": "Japan Times",
}

# 보도량 점수에 세는 언론사. FEEDS로 직접 받는 언론사(Google News 제외)는 자동 포함되고,
# Google News로 들어온 기사는 아래 목록에 있는 언론사일 때만 센다 (후보 기사로는 모두 Gemini에 전달).
TRUSTED_OUTLETS = {
    # 통신사
    "Reuters", "AP", "AFP", "Bloomberg",
    # 주요 일간지·경제지
    "WSJ", "FT", "Washington Post", "Economist", "Le Monde", "Nikkei", "SCMP", "Japan Times",
    # 방송·정치 전문
    "ABC News", "CBS News", "NBC News", "PBS", "Politico", "Axios",
}

# TOP 10 점수 = (1 - COVERAGE_WEIGHT) × Gemini 중요도 + COVERAGE_WEIGHT × 보도 언론사 수
CANDIDATE_ISSUES = 15     # Gemini가 먼저 고르는 후보 이슈 수 (여기서 점수로 10개를 남김)
COVERAGE_WEIGHT = 0.4     # 보도 언론사 수의 비중 (0이면 Gemini 순위 그대로)
COVERAGE_CAP = 6          # 이 수 이상의 언론사가 다루면 만점

CATEGORIES = ["정치/외교", "분쟁/안보", "경제/금융", "기술/과학", "기후/환경", "보건", "사회", "기타"]
