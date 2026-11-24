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
    ("Google News", "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"),
]

CATEGORIES = ["정치/외교", "분쟁/안보", "경제/금융", "기술/과학", "기후/환경", "보건", "사회", "기타"]
