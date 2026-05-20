import os
import requests
import pandas as pd
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

try:
    import streamlit as st
    ACCESS_TOKEN = st.secrets.get("ACCESS_TOKEN") or os.getenv("ACCESS_TOKEN")
    INSTAGRAM_USER_ID = st.secrets.get("INSTAGRAM_USER_ID") or os.getenv("INSTAGRAM_USER_ID") or "17841435661697302"
except Exception:
    ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
    INSTAGRAM_USER_ID = os.getenv("INSTAGRAM_USER_ID") or "17841435661697302"

API_VERSION = "v21.0"
BASE_URL = f"https://graph.instagram.com/{API_VERSION}"

SAFE_METRICS = ["reach", "likes", "comments", "saved", "shares"]
PLAYS_METRICS = ["views", "plays", "video_views"]


def get_all_reels() -> list[dict]:
    url = f"{BASE_URL}/{INSTAGRAM_USER_ID}/media"
    params = {
        "fields": "id,caption,timestamp,media_type,permalink",
        "access_token": ACCESS_TOKEN,
        "limit": 50,
    }
    reels = []
    while url:
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        for item in data.get("data", []):
            if item.get("media_type") in ("REELS", "VIDEO"):
                reels.append(item)
        paging = data.get("paging", {})
        url = paging.get("next")
        params = {}
    return reels


def get_plays(media_id: str) -> int:
    for metric in PLAYS_METRICS:
        try:
            r = requests.get(
                f"{BASE_URL}/{media_id}/insights",
                params={"metric": metric, "access_token": ACCESS_TOKEN},
            )
            data = r.json().get("data", [])
            if data:
                return data[0]["values"][0]["value"]
        except Exception:
            continue
    return 0


def get_reel_insights(media_id: str) -> dict:
    params = {
        "metric": ",".join(SAFE_METRICS),
        "access_token": ACCESS_TOKEN,
    }
    resp = requests.get(f"{BASE_URL}/{media_id}/insights", params=params)
    resp.raise_for_status()
    data = resp.json()
    result = {}
    for item in data.get("data", []):
        result[item["name"]] = item["values"][0]["value"] if item.get("values") else item.get("value", 0)
    return result


def fetch_insights() -> pd.DataFrame:
    if not ACCESS_TOKEN or not INSTAGRAM_USER_ID:
        raise ValueError(".env 파일에 ACCESS_TOKEN과 INSTAGRAM_USER_ID를 설정해주세요.")

    print("릴스 목록 수집 중...")
    reels = get_all_reels()
    print(f"총 {len(reels)}개 릴스 발견")

    rows = []
    for i, reel in enumerate(reels, 1):
        print(f"  [{i}/{len(reels)}] {reel['id']} 인사이트 수집 중...")
        try:
            insights = get_reel_insights(reel["id"])
        except requests.HTTPError as e:
            print(f"    경고: 인사이트 수집 실패 - {e}")
            insights = {m: None for m in SAFE_METRICS}

        plays = get_plays(reel["id"])
        caption = reel.get("caption", "")
        rows.append({
            "media_id": reel["id"],
            "timestamp": reel.get("timestamp", ""),
            "caption": caption[:80] + "..." if len(caption) > 80 else caption,
            "permalink": reel.get("permalink", ""),
            "plays": plays,
            "reach": insights.get("reach"),
            "likes": insights.get("likes"),
            "comments": insights.get("comments"),
            "saved": insights.get("saved"),
            "shares": insights.get("shares"),
        })

    df = pd.DataFrame(rows)
    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        for m in ["plays", "reach", "likes", "comments", "saved", "shares"]:
            df[m] = pd.to_numeric(df[m], errors="coerce")
        df.sort_values("timestamp", ascending=False, inplace=True)
        df.reset_index(drop=True, inplace=True)
    return df


if __name__ == "__main__":
    df = fetch_insights()
    print(df.to_string())