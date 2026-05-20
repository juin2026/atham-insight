import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date
from fetch_insights import fetch_insights
from save_to_excel import save_to_excel

st.set_page_config(page_title="엣햄 인사이트", page_icon="📊", layout="wide")

METRIC_COLS = ["plays", "reach", "likes", "comments", "saved", "shares"]
METRIC_KR = {
    "plays": "조회수",
    "reach": "도달",
    "likes": "좋아요",
    "comments": "댓글",
    "saved": "저장",
    "shares": "공유",
}


def safe_int(val):
    try:
        if pd.isna(val):
            return 0
        return int(val)
    except:
        return 0


def safe_float(val):
    try:
        if pd.isna(val):
            return 0.0
        return float(val)
    except:
        return 0.0


@st.cache_data(show_spinner="Instagram 데이터 불러오는 중...")
def load_data() -> pd.DataFrame:
    return fetch_insights()


# ── 헤더 ──────────────────────────────────────────────────────────────────────
st.title("📊 엣햄 인사이트 대시보드")
st.caption(f"오늘: {date.today().strftime('%Y년 %m월 %d일')}")

col_refresh, col_export = st.columns([1, 1])
with col_refresh:
    if st.button("🔄 데이터 새로고침"):
        st.cache_data.clear()
        st.rerun()

# ── 데이터 로드 ───────────────────────────────────────────────────────────────
df = load_data()

if df.empty:
    st.warning("릴스 데이터가 없습니다. .env 설정을 확인해주세요.")
    st.stop()

# ── 엑셀 저장 버튼 ────────────────────────────────────────────────────────────
with col_export:
    if st.button("💾 엑셀로 저장"):
        with st.spinner("저장 중..."):
            path = save_to_excel(df)
        st.success(f"저장 완료: {path}")

# ── 기간 필터 ─────────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("📅 기간 필터")

min_date = df["timestamp"].min().date()
max_date = df["timestamp"].max().date()

col_start, col_end = st.columns(2)
with col_start:
    start_date = st.date_input("시작일", value=min_date, min_value=min_date, max_value=max_date)
with col_end:
    end_date = st.date_input("종료일", value=max_date, min_value=min_date, max_value=max_date)

filtered_df = df[
    (df["timestamp"].dt.date >= start_date) &
    (df["timestamp"].dt.date <= end_date)
].copy()

if filtered_df.empty:
    st.warning("선택한 기간에 데이터가 없습니다.")
    st.stop()

st.caption(f"선택 기간 릴스: {len(filtered_df)}개")

# ── KPI 요약 카드 ─────────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("전체 합계")
kpi_cols = st.columns(len(METRIC_COLS))
for col, metric in zip(kpi_cols, METRIC_COLS):
    val = safe_int(filtered_df[metric].sum()) if filtered_df[metric].notna().any() else 0
    col.metric(METRIC_KR[metric], f"{val:,}")

# ── 평균 성과율 카드 ──────────────────────────────────────────────────────────
st.markdown("---")
st.subheader("📈 평균 성과율")
rate_cols = st.columns(3)

if "참여율" in filtered_df.columns:
    rate_cols[0].metric("참여율", f"{filtered_df['참여율'].mean():.2f}%", help="(좋아요+댓글+저장+공유) / 도달 × 100")
    rate_cols[1].metric("공유율", f"{filtered_df['공유율'].mean():.2f}%", help="공유 / 도달 × 100")
    rate_cols[2].metric("조회완료율", f"{filtered_df['조회완료율'].mean():.2f}%", help="조회수 / 도달 × 100")

# ── 조회수 상위 5개 릴스 ──────────────────────────────────────────────────────
st.markdown("---")
st.subheader("🏆 조회수 상위 5개 릴스")

plays_df = filtered_df.dropna(subset=["plays"])
top5 = plays_df.nlargest(5, "plays").reset_index(drop=True) if not plays_df.empty else filtered_df.head(5)

for _, row in top5.iterrows():
    with st.container(border=True):
        c1, c2, c3, c4, c5, c6, c7 = st.columns([3, 1, 1, 1, 1, 1, 1])
        caption = row["caption"] if row["caption"] else "(캡션 없음)"
        ts = row["timestamp"].strftime("%Y-%m-%d") if pd.notna(row["timestamp"]) else ""
        c1.markdown(f"**{caption}**  \n`{ts}`  \n[릴스 보기]({row['permalink']})")
        c2.metric("조회수", f"{safe_int(row['plays']):,}")
        c3.metric("도달", f"{safe_int(row['reach']):,}")
        c4.metric("참여율", f"{safe_float(row.get('참여율', 0)):.2f}%" if "참여율" in row else "N/A")
        c5.metric("공유율", f"{safe_float(row.get('공유율', 0)):.2f}%" if "공유율" in row else "N/A")
        c6.metric("조회완료율", f"{safe_float(row.get('조회완료율', 0)):.2f}%" if "조회완료율" in row else "N/A")
        c7.metric("저장", f"{safe_int(row['saved']):,}")

# ── 릴스별 지표 비교 막대 그래프 ─────────────────────────────────────────────
st.markdown("---")
st.subheader("📊 릴스별 지표 비교")

metric_options = METRIC_COLS + (["참여율", "공유율", "조회완료율"] if "참여율" in filtered_df.columns else [])
metric_labels = {**METRIC_KR, "참여율": "참여율(%)", "공유율": "공유율(%)", "조회완료율": "조회완료율(%)"}

selected_metric = st.selectbox(
    "지표 선택",
    metric_options,
    format_func=lambda x: metric_labels.get(x, x),
)

bar_df = filtered_df.copy()
bar_df["label"] = bar_df["timestamp"].dt.strftime("%m/%d") + " " + bar_df["caption"].str[:15]
bar_df = bar_df.sort_values("timestamp")

fig_bar = px.bar(
    bar_df,
    x="label",
    y=selected_metric,
    title=f"릴스별 {metric_labels.get(selected_metric, selected_metric)}",
    labels={"label": "릴스", selected_metric: metric_labels.get(selected_metric, selected_metric)},
    color=selected_metric,
    color_continuous_scale="Blues",
)
fig_bar.update_layout(xaxis_tickangle=-45, showlegend=False)
st.plotly_chart(fig_bar, use_container_width=True)

# ── 조회수/도달 추이 라인 차트 ────────────────────────────────────────────────
st.markdown("---")
st.subheader("📈 조회수 / 도달 추이")

trend_df = filtered_df.sort_values("timestamp").copy()
trend_df["label"] = trend_df["timestamp"].dt.strftime("%Y-%m-%d")

fig_line = go.Figure()
fig_line.add_trace(go.Scatter(
    x=trend_df["label"], y=trend_df["plays"],
    mode="lines+markers", name="조회수", line=dict(color="#4C9BE8", width=2),
))
fig_line.add_trace(go.Scatter(
    x=trend_df["label"], y=trend_df["reach"],
    mode="lines+markers", name="도달", line=dict(color="#F97316", width=2),
))
fig_line.update_layout(
    xaxis_title="게시일", yaxis_title="수치",
    xaxis_tickangle=-45, legend=dict(orientation="h", yanchor="bottom", y=1.02),
)
st.plotly_chart(fig_line, use_container_width=True)

# ── 원본 데이터 테이블 ────────────────────────────────────────────────────────
st.markdown("---")
with st.expander("📋 전체 데이터 보기"):
    display = filtered_df.copy()
    display["timestamp"] = display["timestamp"].dt.strftime("%Y-%m-%d %H:%M")
    display.rename(columns={**{"media_id": "ID", "timestamp": "게시일시",
                               "caption": "캡션", "permalink": "링크"},
                             **{k: v for k, v in METRIC_KR.items()}}, inplace=True)
    st.dataframe(display, use_container_width=True)