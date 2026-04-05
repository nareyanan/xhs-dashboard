import asyncio
import logging
import random
import re
from datetime import date
from typing import Optional
from urllib.parse import quote

from playwright.async_api import Page, Response

from config import (
    BRAND_NAME,
    HASHTAG_KEYWORDS,
    MAX_POSTS_PER_SEARCH,
    REQUEST_DELAY_MAX,
    REQUEST_DELAY_MIN,
    SEARCH_KEYWORDS,
    XHS_SEARCH_URL,
)

logger = logging.getLogger(__name__)


async def _random_delay():
    delay = random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)
    await asyncio.sleep(delay)


def _parse_count_text(text: str) -> Optional[int]:
    """'1.2万' → 12000, '1234' → 1234 등 변환"""
    if not text:
        return None
    text = text.strip().replace(",", "")
    match = re.search(r"([\d.]+)\s*([万千kKwW]?)", text)
    if not match:
        return None
    num = float(match.group(1))
    unit = match.group(2).lower()
    if unit in ("万", "w"):
        num *= 10000
    elif unit in ("千", "k"):
        num *= 1000
    return int(num)


async def collect_search_stats(page: Page, keyword: str) -> dict:
    """키워드 검색 결과 수집"""
    result = {
        "keyword": keyword,
        "post_count": 0,
        "posts": [],
        "error": None,
    }

    api_responses = []

    async def intercept_response(response: Response):
        url = response.url
        if any(p in url for p in ["/api/sns/web/v1/search/notes", "/api/sns/web/v1/feed"]):
            try:
                data = await response.json()
                api_responses.append(data)
            except Exception:
                pass

    page.on("response", intercept_response)

    try:
        search_url = (
            f"{XHS_SEARCH_URL}?keyword={quote(keyword)}"
            f"&source=web_search_result_notes&type=51"
        )
        logger.info(f"검색 중: {keyword}")
        await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(4)

        # API 인터셉트 데이터 파싱
        posts = []
        for api_data in api_responses:
            data = api_data.get("data", {})
            items = data.get("items", [])
            if not items:
                continue
            for item in items[:MAX_POSTS_PER_SEARCH]:
                card = item.get("note_card", {})
                interact = card.get("interact_info", {})
                posts.append({
                    "post_id": item.get("id", ""),
                    "title": card.get("display_title", card.get("title", "")),
                    "likes": _parse_count_text(interact.get("liked_count", "0")) or 0,
                    "comments": _parse_count_text(interact.get("comment_count", "0")) or 0,
                    "collects": _parse_count_text(interact.get("collected_count", "0")) or 0,
                    "author": card.get("user", {}).get("nickname", ""),
                    "url": f"https://www.xiaohongshu.com/explore/{item.get('id', '')}",
                })
            result["post_count"] = len(posts)
            break

        # API 실패 시 DOM 파싱 폴백
        if not posts:
            posts, count = await _parse_dom_search(page)
            result["post_count"] = count

        result["posts"] = posts
        logger.info(f"'{keyword}' 검색 결과: {result['post_count']}개 게시물 수집")

    except Exception as e:
        result["error"] = str(e)
        logger.error(f"검색 수집 실패 ({keyword}): {e}")
    finally:
        page.remove_listener("response", intercept_response)

    await _random_delay()
    return result


async def collect_hashtag_stats(page: Page, keyword: str) -> dict:
    """해시태그 페이지 통계 수집"""
    result = {
        "hashtag": f"#{keyword}",
        "note_count": 0,
        "view_count": 0,
        "posts": [],
        "error": None,
    }

    api_responses = []

    async def intercept_response(response: Response):
        url = response.url
        if any(p in url for p in ["/api/sns/web/v1/search", "/api/sns/web/v1/topic"]):
            try:
                data = await response.json()
                api_responses.append(data)
            except Exception:
                pass

    page.on("response", intercept_response)

    try:
        # 해시태그 검색 (type=54 = 话题/토픽)
        hashtag_url = (
            f"{XHS_SEARCH_URL}?keyword={quote('#' + keyword)}"
            f"&source=web_search_result_notes&type=54"
        )
        logger.info(f"해시태그 수집 중: #{keyword}")
        await page.goto(hashtag_url, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(4)

        # 토픽 통계 DOM 파싱
        note_count, view_count = await _parse_hashtag_stats(page)
        result["note_count"] = note_count
        result["view_count"] = view_count

        # 게시물도 수집 (일반 검색과 동일한 방식)
        posts, _ = await _parse_dom_search(page)
        result["posts"] = posts

        logger.info(f"#{keyword}: 게시물 {note_count}개, 조회 {view_count}회")

    except Exception as e:
        result["error"] = str(e)
        logger.error(f"해시태그 수집 실패 (#{keyword}): {e}")
    finally:
        page.remove_listener("response", intercept_response)

    await _random_delay()
    return result


async def _parse_hashtag_stats(page: Page) -> tuple[int, int]:
    """해시태그 페이지에서 게시물 수, 조회 수 파싱"""
    note_count = 0
    view_count = 0

    try:
        # 토픽 헤더에서 통계 추출 (예: "123篇笔记" or "1.2万次浏览")
        content = await page.content()

        # 笔记 수 (게시물 수)
        match = re.search(r"([\d.]+\s*[万千]?)\s*篇笔记", content)
        if match:
            note_count = _parse_count_text(match.group(1)) or 0

        # 浏览 수 (조회 수)
        match = re.search(r"([\d.]+\s*[万千]?)\s*次浏览", content)
        if match:
            view_count = _parse_count_text(match.group(1)) or 0

        # 대안: 셀렉터로 파싱
        if note_count == 0:
            stat_els = await page.query_selector_all('[class*="topic"] [class*="count"], [class*="stat"]')
            for el in stat_els:
                text = await el.inner_text()
                if "笔记" in text or "note" in text.lower():
                    note_count = _parse_count_text(text) or 0
                elif "浏览" in text or "view" in text.lower():
                    view_count = _parse_count_text(text) or 0

    except Exception as e:
        logger.warning(f"해시태그 통계 파싱 실패: {e}")

    return note_count, view_count


async def _parse_dom_search(page: Page) -> tuple[list, int]:
    """DOM에서 검색 결과 게시물 파싱 (API 인터셉트 실패 시 폴백)"""
    posts = []

    try:
        # XHS 게시물 카드 선택자 (여러 패턴 시도)
        card_selectors = [
            "section.note-item",
            '[class*="note-item"]',
            '[class*="search-item"]',
            "div.feeds-container > div > div",
        ]

        cards = []
        for sel in card_selectors:
            cards = await page.query_selector_all(sel)
            if cards:
                break

        for card in cards[:MAX_POSTS_PER_SEARCH]:
            try:
                title_el = await card.query_selector(
                    '[class*="title"], [class*="desc"], a > span'
                )
                title = (await title_el.inner_text()).strip() if title_el else ""

                like_el = await card.query_selector('[class*="like"], [class*="count"]')
                likes_text = (await like_el.inner_text()).strip() if like_el else "0"
                likes = _parse_count_text(likes_text) or 0

                link_el = await card.query_selector("a[href]")
                href = await link_el.get_attribute("href") if link_el else ""
                url = f"https://www.xiaohongshu.com{href}" if href.startswith("/") else href

                posts.append({
                    "post_id": href.split("/")[-1] if href else "",
                    "title": title,
                    "likes": likes,
                    "comments": 0,
                    "collects": 0,
                    "author": "",
                    "url": url,
                })
            except Exception:
                continue

    except Exception as e:
        logger.warning(f"DOM 파싱 실패: {e}")

    return posts, len(posts)


async def run_daily_collection(page: Page) -> dict:
    """매일 오전 9시 실행되는 전체 데이터 수집"""
    today = date.today().isoformat()
    logger.info(f"=== {today} 일일 데이터 수집 시작 ===")

    collected = {
        "date": today,
        "brand": BRAND_NAME,
        "search_results": [],
        "hashtag_results": [],
    }

    # 키워드 검색
    for keyword in SEARCH_KEYWORDS:
        result = await collect_search_stats(page, keyword)
        collected["search_results"].append(result)

    # 해시태그 수집
    for tag in HASHTAG_KEYWORDS:
        result = await collect_hashtag_stats(page, tag)
        collected["hashtag_results"].append(result)

    logger.info(f"=== {today} 수집 완료 ===")
    return collected
