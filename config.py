import os
from dotenv import load_dotenv

load_dotenv()

# 브랜드 설정
BRAND_NAME = "archivepke"
SEARCH_KEYWORDS = ["archivepke"]
HASHTAG_KEYWORDS = ["archivepke"]  # # 붙여서 검색

# 샤오훙슈 계정
XHS_PHONE = os.getenv("XHS_PHONE", "")
XHS_PASSWORD = os.getenv("XHS_PASSWORD", "")

# 경로
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
COOKIES_FILE = os.path.join(DATA_DIR, "cookies.json")
DB_FILE = os.path.join(DATA_DIR, "xhs_stats.db")

# 스케줄 (매일 오전 9시, 한국 시간)
SCHEDULE_HOUR = 9
SCHEDULE_MINUTE = 0
SCHEDULE_TIMEZONE = "Asia/Seoul"

# 스크레이퍼 설정
REQUEST_DELAY_MIN = 2.0  # 요청 간 최소 대기 (초)
REQUEST_DELAY_MAX = 5.0  # 요청 간 최대 대기 (초)
MAX_POSTS_PER_SEARCH = 20  # 검색당 수집할 최대 게시물 수

# URL
XHS_BASE_URL = "https://www.xiaohongshu.com"
XHS_LOGIN_URL = "https://www.xiaohongshu.com/login"
XHS_SEARCH_URL = "https://www.xiaohongshu.com/search_result"
