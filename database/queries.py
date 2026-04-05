import logging
from datetime import date, timedelta
from typing import Optional

import pandas as pd

from database.models import get_connection

logger = logging.getLogger(__name__)


def save_daily_stats(collected: dict):
    """수집 결과를 DB에 저장"""
    conn = get_connection()
    today = collected["date"]
    brand = collected["brand"]

    try:
        # 키워드 검색 결과 저장
        for r in collected.get("search_results", []):
            conn.execute(
                """
                INSERT INTO daily_stats (date, brand, keyword, type, post_count, has_error, error_msg)
                VALUES (?, ?, ?, 'search', ?, ?, ?)
                ON CONFLICT(date, brand, keyword, type) DO UPDATE SET
                    post_count = excluded.post_count,
                    has_error  = excluded.has_error,
                    error_msg  = excluded.error_msg
                """,
                (
                    today, brand, r["keyword"],
                    r["post_count"],
                    1 if r.get("error") else 0,
                    r.get("error"),
                ),
            )

            # 수집된 게시물 저장
            for post in r.get("posts", []):
                conn.execute(
                    """
                    INSERT INTO posts
                        (collected_at, brand, keyword, post_id, title, likes, comments, collects, author, url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        today, brand, r["keyword"],
                        post.get("post_id", ""),
                        post.get("title", ""),
                        post.get("likes", 0),
                        post.get("comments", 0),
                        post.get("collects", 0),
                        post.get("author", ""),
                        post.get("url", ""),
                    ),
                )

        # 해시태그 결과 저장
        for r in collected.get("hashtag_results", []):
            conn.execute(
                """
                INSERT INTO daily_stats (date, brand, keyword, type, post_count, view_count, has_error, error_msg)
                VALUES (?, ?, ?, 'hashtag', ?, ?, ?, ?)
                ON CONFLICT(date, brand, keyword, type) DO UPDATE SET
                    post_count = excluded.post_count,
                    view_count = excluded.view_count,
                    has_error  = excluded.has_error,
                    error_msg  = excluded.error_msg
                """,
                (
                    today, brand, r["hashtag"],
                    r["note_count"],
                    r["view_count"],
                    1 if r.get("error") else 0,
                    r.get("error"),
                ),
            )

            for post in r.get("posts", []):
                conn.execute(
                    """
                    INSERT INTO posts
                        (collected_at, brand, keyword, post_id, title, likes, comments, collects, author, url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        today, brand, r["hashtag"],
                        post.get("post_id", ""),
                        post.get("title", ""),
                        post.get("likes", 0),
                        post.get("comments", 0),
                        post.get("collects", 0),
                        post.get("author", ""),
                        post.get("url", ""),
                    ),
                )

        conn.commit()
        logger.info(f"{today} 데이터 저장 완료")
    except Exception as e:
        conn.rollback()
        logger.error(f"DB 저장 실패: {e}")
        raise
    finally:
        conn.close()


def get_stats_trend(brand: str, days: int = 30) -> pd.DataFrame:
    """최근 N일 일별 통계 추이"""
    conn = get_connection()
    try:
        df = pd.read_sql_query(
            """
            SELECT date, keyword, type, post_count, view_count
            FROM daily_stats
            WHERE brand = ?
              AND date >= date('now', ?)
            ORDER BY date ASC, type ASC, keyword ASC
            """,
            conn,
            params=(brand, f"-{days} days"),
        )
        return df
    finally:
        conn.close()


def get_top_posts(brand: str, collected_at: Optional[str] = None, limit: int = 20) -> pd.DataFrame:
    """특정 날짜의 상위 게시물"""
    conn = get_connection()
    try:
        if collected_at is None:
            collected_at = date.today().isoformat()
        df = pd.read_sql_query(
            """
            SELECT collected_at, keyword, title, likes, comments, collects, author, url
            FROM posts
            WHERE brand = ? AND collected_at = ?
            ORDER BY likes DESC
            LIMIT ?
            """,
            conn,
            params=(brand, collected_at, limit),
        )
        return df
    finally:
        conn.close()


def get_available_dates(brand: str) -> list[str]:
    """수집된 날짜 목록"""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT DISTINCT date FROM daily_stats WHERE brand = ? ORDER BY date DESC",
            (brand,),
        ).fetchall()
        return [r["date"] for r in rows]
    finally:
        conn.close()


def get_latest_summary(brand: str) -> dict:
    """가장 최근 수집 데이터 요약"""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT type, keyword, post_count, view_count, date
            FROM daily_stats
            WHERE brand = ?
            ORDER BY date DESC
            LIMIT 10
            """,
            (brand,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
