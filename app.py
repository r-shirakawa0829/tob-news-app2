import streamlit as st
import feedparser
import pandas as pd
import datetime
import os
import urllib.parse

# --- 判定ロジック：公共・大学を除外し、純粋な民間BtoBを抽出 ---
def analyze_growth_company(title, summary):
    text = (title + summary).lower()
    title_lower = title.lower()
    
    # 1. 【除外リスト】ここに当てはまる言葉が「タイトル」にあったら即捨てる
    exclude_keywords = [
        "大学", "教授", "研究室", "学生", "高校", "学校", # 教育機関
        "市役所", "県庁", "都庁", "区役所", "役場", "省", "庁", "内閣", # 官公庁
        "自治体", "観光協会", "フェスティバル", "祭り", "公募", "入札", # 公共・イベント
        "機構", "財団", "連合会", "協議会", "警察", "消防" # 公的団体
    ]
    # 「省エネ」などで誤爆しないよう、単語によっては慎重に判定する必要がありますが、
    # まずは上記リストで官公庁系を弾きます。
    if any(k in title_lower for k in exclude_keywords):
        return False

    # 2. 【成長ワード】企業の「動き」があるか
    growth_keywords = [
        "採用", "募集", "移転", "増床", "新拠点", "開設", "設立",
        "海外", "進出", "新規事業", "資金調達", "出資", "提携", 
        "m&a", "買収", "子会社", "ローンチ", "開始", "導入"
    ]
    
    # 3. 【BtoBビジネスワード】企業間取引の匂いがするか
    biz_keywords = [
        "法人", "b2b", "企業向け", "業務", "ソリューション", 
        "saas", "dx", "プラットフォーム", "クラウド", "ai", 
        "システム", "開発", "oem", "卸", "コンサル", "支援"
    ]

    # 判定：除外ワードがなく、かつ「成長」と「ビジネス」の要素があるもの
    has_growth = any(k in text for k in growth_keywords)
    has_biz = any(k in text for k in biz_keywords)
    
    return has_growth and has_biz

def fetch_all_sources():
    # 検索ワードも「ビジネス寄り」に厳選
    feeds = [
        "https://prtimes.jp/index.rdf",
        "https://news.google.com/rss/search?q=" + urllib.parse.quote("法人向け 新規事業") + "&hl=ja&gl=JP&ceid=JP:ja",
        "https://news.google.com/rss/search?q=" + urllib.parse.quote("BtoB 提携") + "&hl=ja&gl=JP&ceid=JP:ja",
        "https://news.google.com/rss/search?q=" + urllib.parse.quote("DX 導入 事例") + "&hl=ja&gl=JP&ceid=JP:ja"
    ]
    
    now = datetime.datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    new_entries = []
    
    for url in feeds:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            if analyze_growth_company(entry.title, entry.summary):
                # 会社名をきれいに抜き出す処理
                title_clean = entry.title.replace("【", " ").replace("】", " ").replace("「", " ").replace("」", " ")
                # 「〜が」「〜の」で区切って会社名っぽく見せる
                company = title_clean.split("が")[0].split("の")[0].split("、")[0].strip()[:20]
                
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

# --- 画面表示 ---
st.set_page_config(page_title="BtoB Growth Radar", layout="wide")

# CSSで見やすく整形
st.markdown("""
    <style>
    .stCard { background: white; border: 1px solid #ddd; padding: 15px; border-radius: 8px; margin-bottom: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    .new-label { background: #d9534f; color: white; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; margin-right: 8px; }
    .tag { background: #f0f0f0; color: #555; padding: 2px 6px; border-radius: 4px; font-size: 11px; margin-right: 4px; border: 1px solid #ccc; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏢 民間BtoB企業・成長ニュース")

# サイドバー設定
with st.sidebar:
    st.header("カレンダー")
    selected_date = st.date_input("日付を選択", datetime.date.today())
    st.divider()
    if st.button("🔄 最新情報を取得"):
        with st.spinner("官公庁・大学を除外してスキャン中..."):
            count = fetch_all_sources()
            st.success(f"{count}件の民間ビジネスニュースを追加しました")
            st.rerun()

db_file = "news_database.csv"
target_str = selected_date.strftime("%Y-%m-%d")

if os.path.exists(db_file):
    df = pd.read_csv(db_file)
    display_df = df[df["date"] == target_str]
    
    st.subheader(f"📅 {target_str} のニュース")
    
    if not display_df.empty:
        for _, row in display_df.iterrows():
            # NEWラベル判定
            past_data = df[df["date"] < target_str]
            is_new = row['company'] not in past_data['company'].values if not past_data.empty else True
            
            new_badge = '<span class="new-label">NEW</span>' if is_new else ""
            
            # タグ付け
            tags = []
            title_text = str(row['title'])
            if "採用" in title_text: tags.append("🔥採用")
            if "資金" in title_text or "調達" in title_text: tags.append("💰資金")
            if "提携" in title_text: tags.append("🤝提携")
            if "DX" in title_text or "AI" in title_text: tags.append("💻Tech")
            
            tag_html = "".join([f'<span class="tag">{t}</span>' for t in tags])

            st.markdown(f"""
            <div class="stCard">
                <div style="color:#888; font-size:12px;">{row['time']} | {row['company']}</div>
                <div style="margin-top:4px;">
                    {new_badge}
                    <a href="{row['url']}" target="_blank" style="text-decoration:none; color:#0366d6; font-weight:bold; font-size:16px;">{row['title']}</a>
                </div>
                <div style="margin-top:6px;">{tag_html}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("この日のBtoBニュースはありません。")
else:
    st.warning("データがまだありません。サイドバーのボタンで取得してください。")
