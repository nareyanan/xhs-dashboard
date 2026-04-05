"""
메인 진입점

실행 모드:
  python main.py              → 스케줄러 + 대시보드 동시 실행
  python main.py --run-now    → 즉시 한 번 수집 후 종료
  python main.py --dash-only  → 대시보드만 실행 (수집 없음)
"""

import argparse
import asyncio
import logging
import subprocess
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def run_now():
    """즉시 한 번 수집"""
    from scraper.browser import XHSBrowser
    from scraper.collector import run_daily_collection
    from database.queries import save_daily_stats
    from database.models import init_db

    init_db()

    async def _collect():
        async with XHSBrowser(headless=True) as xhs:
            logged_in = await xhs.is_logged_in()
            if not logged_in:
                logger.error("로그인 세션 만료! 먼저 setup_login.py를 실행하세요.")
                sys.exit(1)
            collected = await run_daily_collection(xhs.page)
            save_daily_stats(collected)
            logger.info("수집 완료!")

    asyncio.run(_collect())


def run_dashboard():
    """Streamlit 대시보드 실행 (서브프로세스)"""
    port = 8501
    logger.info(f"대시보드 시작: http://0.0.0.0:{port}")
    subprocess.run(
        [
            sys.executable, "-m", "streamlit", "run",
            "dashboard/app.py",
            "--server.port", str(port),
            "--server.address", "0.0.0.0",
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false",
        ],
        check=True,
    )


def run_all():
    """스케줄러 백그라운드 + 대시보드 포어그라운드"""
    from database.models import init_db
    from scheduler.jobs import start_scheduler

    init_db()
    scheduler = start_scheduler()

    try:
        run_dashboard()  # 포어그라운드 (블로킹)
    except KeyboardInterrupt:
        logger.info("종료 중...")
    finally:
        scheduler.shutdown()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="XHS 대시보드")
    parser.add_argument("--run-now", action="store_true", help="즉시 한 번 수집")
    parser.add_argument("--dash-only", action="store_true", help="대시보드만 실행")
    args = parser.parse_args()

    if args.run_now:
        run_now()
    elif args.dash_only:
        from database.models import init_db
        init_db()
        run_dashboard()
    else:
        run_all()
