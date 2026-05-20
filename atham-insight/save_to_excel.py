import pandas as pd
from datetime import date
from fetch_insights import fetch_insights

METRIC_COLS = ["plays", "reach", "likes", "comments", "saved", "shares"]


def build_summary(df: pd.DataFrame) -> pd.DataFrame:
    """지표별 합계 및 평균 요약 시트 생성."""
    numeric = df[METRIC_COLS].apply(pd.to_numeric, errors="coerce")
    summary = pd.DataFrame({
        "지표": METRIC_COLS,
        "합계": numeric.sum().values,
        "평균": numeric.mean().round(1).values,
        "최댓값": numeric.max().values,
        "최솟값": numeric.min().values,
    })
    return summary


def save_to_excel(df: pd.DataFrame | None = None) -> str:
    """릴스 데이터를 날짜_엣햄인사이트.xlsx로 저장하고 파일 경로 반환."""
    if df is None:
        df = fetch_insights()

    filename = f"{date.today().strftime('%Y%m%d')}_엣햄인사이트.xlsx"
    summary = build_summary(df)

    display_df = df.copy()
    display_df["timestamp"] = display_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M")

    col_rename = {
        "media_id": "미디어 ID",
        "timestamp": "게시 일시",
        "caption": "캡션",
        "permalink": "링크",
        "plays": "조회수",
        "reach": "도달",
        "likes": "좋아요",
        "comments": "댓글",
        "saved": "저장",
        "shares": "공유",
    }
    display_df.rename(columns=col_rename, inplace=True)

    with pd.ExcelWriter(filename, engine="openpyxl") as writer:
        display_df.to_excel(writer, sheet_name="릴스별 전체 데이터", index=False)
        summary.to_excel(writer, sheet_name="지표 요약", index=False)

        # 열 너비 자동 조정
        for sheet_name in writer.sheets:
            ws = writer.sheets[sheet_name]
            for col in ws.columns:
                max_len = max(len(str(cell.value)) if cell.value else 0 for cell in col)
                ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 60)

    print(f"저장 완료: {filename}")
    return filename


if __name__ == "__main__":
    save_to_excel()
