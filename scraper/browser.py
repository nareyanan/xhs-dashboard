import asyncio
import json
import logging
import os
from pathlib import Path

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright

from config import COOKIES_FILE, DATA_DIR

logger = logging.getLogger(__name__)


class XHSBrowser:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self._playwright: Playwright = None
        self._browser: Browser = None
        self._context: BrowserContext = None
        self.page: Page = None

    async def start(self):
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--window-size=1280,800",
            ],
        )
        self._context = await self._browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            extra_http_headers={
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
        )

        # 자동화 감지 우회
        await self._context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
            window.chrome = { runtime: {} };
        """)

        # 저장된 쿠키 로드
        if Path(COOKIES_FILE).exists():
            try:
                with open(COOKIES_FILE, "r") as f:
                    cookies = json.load(f)
                await self._context.add_cookies(cookies)
                logger.info("저장된 쿠키 로드 완료")
            except Exception as e:
                logger.warning(f"쿠키 로드 실패: {e}")

        self.page = await self._context.new_page()
        logger.info("브라우저 시작 완료")

    async def save_cookies(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        cookies = await self._context.cookies()
        with open(COOKIES_FILE, "w") as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
        logger.info(f"쿠키 저장 완료: {COOKIES_FILE}")

    async def is_logged_in(self) -> bool:
        try:
            await self.page.goto("https://www.xiaohongshu.com/", timeout=20000)
            await self.page.wait_for_load_state("networkidle", timeout=15000)
            await asyncio.sleep(2)

            # 로그인 버튼이 없으면 로그인된 상태
            login_selectors = [
                'text="登录"',
                '[class*="login-btn"]',
                'a[href*="/login"]',
            ]
            for sel in login_selectors:
                el = await self.page.query_selector(sel)
                if el:
                    return False
            return True
        except Exception as e:
            logger.warning(f"로그인 상태 확인 실패: {e}")
            return False

    async def close(self):
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("브라우저 종료")

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *args):
        await self.close()
