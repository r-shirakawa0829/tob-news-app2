import streamlit as st
import feedparser
import pandas as pd
import datetime
import os
import urllib.parse

def analyze_growth_company(title, summary):
    text = (title + summary).lower()
    growth_keywords = ["採用", "募集", "移転", "増床", "新拠点", "海外展開", "新規事業", "資金調達", "提携", "導入", "開始", "ローンチ", "子会社"]
    biz_keywords = ["法人", "企業", "b2b", "saas", "dx", "ソリューション", "oem", "卸", "加盟", "fc"]
    return any(k in text for k in growth_keywords) and any(k in text for k in biz_keywords)

def fetch_all_sources():
    feeds = [
        "https://prtimes.jp/index.rdf",
        "https://news.google.com/rss/search?q=" + urllib.parse.quote("採用強化 企業") + "&hl=ja&gl=JP&ceid=JP:ja",
        "https://news.google.com/rss/search?q=" + urllib.parse.quote("新事業 開始") + "&hl=ja&gl=JP&ceid=JP:ja"
    ]
    now = datetime.datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    new_entries = []
    for url in feeds:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            if analyze_growth_company(entry.title, entry.summary):
                title_clean = entry.title.replace("【", " ").replace("】", " ").replace("「", " ").replace("」", " ")
                company = title_clean.split("が")[0].split("の")[0].strip()[:20]
                new_entries.append([today_str, now.strftime("%H:%M"), company, entry.title, entry.link])
    db_file = "news_database.csv"
    if new_entries:
        df_new = pd.DataFrame(new_entries, columns=["date", "time", "company", "title", "url"])
        if os.path.exists(db_file):
            df_old = pd.read_csv(db_file)
            df_final = pd.concat([df_new, df_old]).drop_duplicates(subset=["url"], keep="first")
        else:
            df_final = df_new
        df_final.sort_values(by=["date", "time"], ascending=False).to_csv(db_file, index=False, encoding="utf_8_sig")
    return len(new_entries)

st.set_page_config(page_title="Growth Company Hub", layout="wide")
st.title("🚀 成長企業ターゲット・リスト")

if st.button("🔄 最新情報を取得"):
    count = fetch_all_sources()
    st.success(f"{count}件更新しました")
    st.rerun()

db_file = "news_database.csv"
if os.path.exists(db_file):
    df = pd.read_csv(db_file)
    for d in df["date"].unique():
        st.markdown(f"#### 📅 {d}")
        day_df = df[df["date"] == d]
        for _, row in day_df.iterrows():
            st.markdown(f"✅ **{row['company']}** [{row['title']}]({row['url']})")
