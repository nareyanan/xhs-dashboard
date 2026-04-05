"""
최초 1회 실행: 샤오훙슈 로그인 후 쿠키 저장
반드시 로컬 Mac에서 실행 (headed 브라우저 필요)

사용법:
  pip install playwright
  playwright install chromium
  python setup_login.py
"""

import asyncio
import json
import os
import sys

from playwright.async_api import async_playwright

COOKIES_FILE = "data/cookies.json"


async def manual_login():
    print("=" * 50)
    print("샤오훙슈 로그인 설정")
    print("=" * 50)
    print("브라우저가 열립니다. 직접 로그인해 주세요.")
    print("로그인 완료 후 Enter를 누르면 쿠키가 저장됩니다.")
    print()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # 화면에 보이게
            args=["--window-size=1280,800"],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            locale="zh-CN",
        )
        page = await context.new_page()

        print("샤오훙슈 로그인 페이지로 이동 중...")
        await page.goto("https://www.xiaohongshu.com/login", timeout=30000)

        print()
        print(">> 브라우저에서 로그인을 완료하세요.")
        print(">> 로그인 후 메인 피드가 보이면 아래에서 Enter를 누르세요.")
        print()
        input("로그인 완료 후 Enter 입력: ")

        # 로그인 확인
        current_url = page.url
        print(f"현재 URL: {current_url}")

        cookies = await context.cookies()
        if not cookies:
            print("쿠키를 가져올 수 없습니다. 로그인을 다시 확인하세요.")
            await browser.close()
            return

        os.makedirs("data", exist_ok=True)
        with open(COOKIES_FILE, "w") as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)

        print(f"\n쿠키 저장 완료! ({len(cookies)}개)")
        print(f"저장 위치: {os.path.abspath(COOKIES_FILE)}")
        print()
        print("다음 단계:")
        print("  1. data/cookies.json 파일을 서버에 복사하세요")
        print("  2. 서버에서 docker compose up -d 실행")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(manual_login())
