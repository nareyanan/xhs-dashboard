import asyncio
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from config import BRAND_NAME, SCHEDULE_HOUR, SCHEDULE_MINUTE, SCHEDULE_TIMEZONE

logger = logging.getLogger(__name__)


def _run_collection():
    """APScheduler에서 호출되는 동기 래퍼"""
    from scraper.browser import XHSBrowser
    from scraper.collector import run_daily_collection
    from database.queries import save_daily_stats

    async def _async_collect():
        async with XHSBrowser(headless=True) as xhs:
            logged_in = await xhs.is_logged_in()
            if not logged_in:
                logger.error("로그인 세션 만료! 쿠키를 갱신하세요: python setup_login.py")
                return

            collected = await run_daily_collection(xhs.page)
            save_daily_stats(collected)
            logger.info(f"{BRAND_NAME} 데이터 수집 및 저장 완료")

    asyncio.run(_async_collect())


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone=SCHEDULE_TIMEZONE)
    scheduler.add_job(
        _run_collection,
        trigger=CronTrigger(
            hour=SCHEDULE_HOUR,
            minute=SCHEDULE_MINUTE,
            timezone=SCHEDULE_TIMEZONE,
        ),
        id="daily_collection",
        name=f"{BRAND_NAME} 일일 수집",
        replace_existing=True,
        misfire_grace_time=3600,  # 1시간 내 실패 시 재실행
    )
    scheduler.start()
    logger.info(
        f"스케줄러 시작: 매일 {SCHEDULE_HOUR:02d}:{SCHEDULE_MINUTE:02d} ({SCHEDULE_TIMEZONE})"
    )
    return scheduler
