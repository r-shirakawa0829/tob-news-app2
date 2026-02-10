import streamlit as st
import feedparser
import pandas as pd
import datetime
import os
import urllib.parse

# --- 判定ロジック：成長意欲・toB判定 ---
def analyze_growth_company(title, summary):
    text = (title + summary).lower()
    growth_keywords = ["採用", "募集", "移転", "増床", "新拠点", "海外展開", "新規事業", "資金調達", "提携", "導入", "開始", "ローンチ"]
    biz_keywords = ["法人", "企業", "b2b", "saas", "dx", "ソリューション", "oem", "卸", "加盟", "fc"]
    return any(k in text for k in growth_keywords) and any(k in text for k in biz_keywords)

def fetch_all_sources():
    feeds = [
        "https://prtimes.jp/index.rdf",
        "https://news.google.com/rss/search?q=" + urllib.parse.quote("採用強化 企業") + "&hl=ja&gl=JP&ceid=JP:ja",
        "https://news.google.com/rss/search?q=" + urllib.parse.quote("新規事業 開始") + "&hl=ja&gl=JP&ceid=JP:ja"
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

# --- 画面デザイン ---
st.set_page_config(page_title="Growth Calendar", layout="wide")

st.markdown("""
    <style>
    .stCard { border: 1px solid #dee2e6; padding: 15px; border-radius: 10px; background: white; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .new-label { background: #ff4b4b; color: white; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; margin-right: 10px; }
    .tag { background: #e9ecef; color: #495057; padding: 2px 8px; border-radius: 4px; font-size: 11px; margin-right: 5px; }
    </style>
    """, unsafe_allow_html=True)

st.title("📅 成長企業ニュース・カレンダー")

# サイドバーにカレンダーを配置
with st.sidebar:
    st.header("日付選択")
    selected_date = st.date_input("確認したい日を選択", datetime.date.today())
    st.divider()
    if st.button("🔄 最新ニュースを取得"):
        with st.spinner("スキャン中..."):
            fetch_all_sources()
            st.rerun()

db_file = "news_database.csv"
target_str = selected_date.strftime("%Y-%m-%d")

if os.path.exists(db_file):
    df = pd.read_csv(db_file)
    # NEWラベル判定用に会社名リストを作成
    display_df = df[df["date"] == target_str]
    
    st.subheader(f"🔍 {target_str} の検索結果")
    
    if not display_df.empty:
        for _, row in display_df.iterrows():
            # NEW判定（その日より前に同じ会社名がないか）
            past_data = df[df["date"] < target_str]
            is_new = row['company'] not in past_data['company'].values if not past_data.empty else True
            
            new_badge = '<span class="new-label">NEW</span>' if is_new else ""
            
            # 簡易タグ
            tags = []
            if "採用" in str(row['title']): tags.append("🔥採用")
            if "資金" in str(row['title']): tags.append("💰資金")
            tag_html = "".join([f'<span class="tag">{t}</span>' for t in tags])

            st.markdown(f"""
            <div class="stCard">
                <small>{row['time']} | {row['company']}</small><br>
                {new_badge}<strong><a href="{row['url']}" target="_blank" style="text-decoration:none; color:#1f77b4;">{row['title']}</a></strong>
                <div style="margin-top:5px;">{tag_html}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info(f"{target_str} のデータはありません。")
else:
    st.warning("データがありません。最新ニュースを取得してください。")
