import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta

from config import BRAND_NAME
from database.models import init_db
from database.queries import (
    get_available_dates,
    get_latest_summary,
    get_stats_trend,
    get_top_posts,
)

# ─── 페이지 설정 ──────────────────────────────────────────────
st.set_page_config(
    page_title=f"{BRAND_NAME} | 샤오훙슈 대시보드",
    page_icon="📊",
    layout="wide",
)

init_db()

# ─── 헤더 ─────────────────────────────────────────────────────
st.title(f"📊 {BRAND_NAME} 샤오훙슈 대시보드")

available_dates = get_available_dates(BRAND_NAME)
if not available_dates:
    st.warning("아직 수집된 데이터가 없습니다. 오전 9시 스케줄러가 실행되면 데이터가 쌓입니다.")
    st.info("수동으로 바로 수집하려면: `docker exec xhs-app python main.py --run-now`")
    st.stop()

latest_date = available_dates[0]
st.caption(f"마지막 업데이트: **{latest_date}** (매일 오전 9시 자동 수집)")

# ─── 사이드바: 날짜 범위 ───────────────────────────────────────
with st.sidebar:
    st.header("설정")
    trend_days = st.selectbox("추이 기간", [7, 14, 30, 60, 90], index=2)
    selected_date = st.selectbox("게시물 조회 날짜", available_dates)

# ─── 최신 핵심 지표 ────────────────────────────────────────────
st.subheader("핵심 지표 (최신)")

summary = get_latest_summary(BRAND_NAME)
latest_summary = [s for s in summary if s["date"] == latest_date]

search_stats = [s for s in latest_summary if s["type"] == "search"]
hashtag_stats = [s for s in latest_summary if s["type"] == "hashtag"]

col1, col2, col3, col4 = st.columns(4)

# 검색 결과 게시물 수 (archivepke 검색)
search_count = sum(s["post_count"] for s in search_stats)
# 해시태그 게시물 수 (#archivepke)
hashtag_count = sum(s["post_count"] for s in hashtag_stats)
# 해시태그 조회 수
view_count = sum(s["view_count"] for s in hashtag_stats)

# 전일 대비 변화율 계산
def get_delta(metric_type: str, metric_field: str) -> str:
    if len(available_dates) < 2:
        return None
    prev_date = available_dates[1]
    prev = get_latest_summary(BRAND_NAME)
    prev_sum = [s for s in prev if s["date"] == prev_date and s["type"] == metric_type]
    prev_val = sum(s[metric_field] for s in prev_sum)
    curr_val = sum(s[metric_field] for s in latest_summary if s["type"] == metric_type)
    if prev_val == 0:
        return None
    delta = curr_val - prev_val
    pct = (delta / prev_val) * 100
    return f"{'+' if delta >= 0 else ''}{delta:,} ({pct:+.1f}%)"

with col1:
    st.metric(
        label="검색 결과 게시물",
        value=f"{search_count:,}",
        delta=get_delta("search", "post_count"),
        help="'archivepke' 키워드 검색 노출 게시물 수",
    )
with col2:
    st.metric(
        label="#archivepke 태그 게시물",
        value=f"{hashtag_count:,}",
        delta=get_delta("hashtag", "post_count"),
        help="#archivepke 해시태그 게시물 수",
    )
with col3:
    st.metric(
        label="해시태그 조회 수",
        value=f"{view_count:,}",
        delta=get_delta("hashtag", "view_count"),
        help="#archivepke 해시태그 누적 조회 수",
    )
with col4:
    # 오늘 수집된 상위 게시물 평균 좋아요
    top_posts_today = get_top_posts(BRAND_NAME, latest_date, 20)
    avg_likes = int(top_posts_today["likes"].mean()) if not top_posts_today.empty else 0
    st.metric(
        label="상위 게시물 평균 좋아요",
        value=f"{avg_likes:,}",
        help="오늘 수집된 상위 20개 게시물의 평균 좋아요 수",
    )

st.divider()

# ─── 추이 그래프 ───────────────────────────────────────────────
st.subheader(f"최근 {trend_days}일 추이")

trend_df = get_stats_trend(BRAND_NAME, trend_days)

if not trend_df.empty:
    tab1, tab2 = st.tabs(["게시물 수 추이", "조회 수 추이"])

    with tab1:
        search_trend = trend_df[trend_df["type"] == "search"].copy()
        hashtag_trend = trend_df[trend_df["type"] == "hashtag"].copy()

        fig = go.Figure()
        if not search_trend.empty:
            fig.add_trace(go.Scatter(
                x=search_trend["date"],
                y=search_trend["post_count"],
                name="검색 결과 게시물",
                mode="lines+markers",
                line=dict(color="#FF2442", width=2),
                marker=dict(size=6),
            ))
        if not hashtag_trend.empty:
            fig.add_trace(go.Scatter(
                x=hashtag_trend["date"],
                y=hashtag_trend["post_count"],
                name="#archivepke 태그 게시물",
                mode="lines+markers",
                line=dict(color="#FF8FAB", width=2),
                marker=dict(size=6),
            ))
        fig.update_layout(
            xaxis_title="날짜",
            yaxis_title="게시물 수",
            hovermode="x unified",
            height=350,
            margin=dict(l=0, r=0, t=20, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        hashtag_trend = trend_df[trend_df["type"] == "hashtag"].copy()
        if not hashtag_trend.empty and hashtag_trend["view_count"].sum() > 0:
            fig2 = px.area(
                hashtag_trend,
                x="date",
                y="view_count",
                title="",
                color_discrete_sequence=["#FF2442"],
            )
            fig2.update_layout(height=350, margin=dict(l=0, r=0, t=20, b=0))
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("조회 수 데이터가 아직 없습니다.")
else:
    st.info("추이 데이터가 아직 충분하지 않습니다.")

st.divider()

# ─── 상위 게시물 테이블 ────────────────────────────────────────
st.subheader(f"상위 게시물 TOP 20 ({selected_date})")

posts_df = get_top_posts(BRAND_NAME, selected_date, 20)

if not posts_df.empty:
    # URL을 클릭 가능한 링크로 변환
    posts_df["링크"] = posts_df["url"].apply(
        lambda u: f'<a href="{u}" target="_blank">보기</a>' if u else "-"
    )
    display_df = posts_df[["keyword", "title", "likes", "comments", "collects", "author", "링크"]].copy()
    display_df.columns = ["키워드", "제목", "좋아요", "댓글", "저장", "작성자", "링크"]
    display_df["제목"] = display_df["제목"].str[:50]  # 제목 길이 제한

    st.write(
        display_df.to_html(escape=False, index=False),
        unsafe_allow_html=True,
    )

    # 좋아요 기준 바 차트
    if not posts_df.empty:
        fig3 = px.bar(
            posts_df.head(10),
            x="likes",
            y="title",
            orientation="h",
            color="likes",
            color_continuous_scale="Reds",
            labels={"likes": "좋아요", "title": "제목"},
        )
        fig3.update_layout(
            height=350,
            margin=dict(l=0, r=0, t=20, b=0),
            yaxis=dict(autorange="reversed"),
            coloraxis_showscale=False,
        )
        fig3.update_traces(texttemplate="%{x:,}", textposition="outside")
        st.plotly_chart(fig3, use_container_width=True)
else:
    st.info(f"{selected_date}에 수집된 게시물이 없습니다.")

# ─── 수집 상태 ─────────────────────────────────────────────────
with st.expander("수집 상태 로그"):
    st.json(summary)
