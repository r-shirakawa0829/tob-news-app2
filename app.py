import streamlit as st
import feedparser
import pandas as pd
import datetime
import os
import urllib.parse

# --- 判定ロジック：公共を除外 ---
def is_target_company(title, summary):
    text = (title + summary).lower()
    exclude_keywords = [
        "大学", "教授", "研究室", "学生", "高校", "学校",
        "市役所", "県庁", "都庁", "区役所", "役場", "省", "庁", "内閣",
        "自治体", "観光協会", "フェスティバル", "祭り", "公募", "入札",
        "機構", "財団", "連合会", "協議会", "警察", "消防"
    ]
    if any(k in text for k in exclude_keywords):
        return False
    return True

# --- ★ビジネスタンク・マッチ度判定ロジック（改良版）★ ---
def analyze_business_tank_fit(title, summary):
    text = (title + summary).lower()
    tags = []
    score = 0

    # 1. 【Crown】販路拡大・パートナー募集（ビジネスタンク直撃）
    # これがある企業は「売り先」を渇望しているため、最優先（+10点）
    crown_keywords = [
        "販路拡大", "販路開拓", "販売店募集", "販売店 募集", 
        "代理店募集", "代理店 募集", "パートナー募集"
    ]
    for k in crown_keywords:
        if k in text:
            tags.append(f"👑{k}")
            score += 10

    # 2. 【Priority】攻めの姿勢（資金・新サービス）
    # 動き出す準備が整った企業（+3点）
    priority_keywords = [
        "資金調達", "第三者割当", "新サービス", "新商品", 
        "プレリリース", "プレスリリース", "ローンチ", "発売", "提供開始"
    ]
    for k in priority_keywords:
        if k in text:
            tags.append(f"🔥{k}")
            score += 3

    # 3. 【Partnership】提携・協業（+2点）
    partner_keywords = [
        "提携", "共同研究", "共同開発", "実証実験", "協業", 
        "アライアンス", "オープンイノベーション", "OEM"
    ]
    for k in partner_keywords:
        if k in text:
            tags.append(f"🤝{k}")
            score += 2 

    # 4. 【Change】変化の予兆（+1点）
    change_keywords = [
        "新規事業", "事業拡大", "社長就任", "新体制", 
        "経営計画", "刷新", "DX", "IPO", "黒字化"
    ]
    for k in change_keywords:
        if k in text:
            tags.append(f"📈{k}")
            score += 1

    # 5. 【Penalty】大手・有名企業の減点（-10点）
    big_company_keywords = [
        "大手", "最大手", "業界トップ", "東証プライム", "老舗", 
        "有名", "ホールディングス", "グループ"
    ]
    for k in big_company_keywords:
        if k in text:
            score -= 10
            tags.append(f"🏢{k}(大手)")

    return score, list(set(tags))

def fetch_all_sources():
    # 検索ワードも「販路拡大」「資金調達」に寄せる
    feeds = [
        "https://prtimes.jp/index.rdf",
        "https://news.google.com/rss/search?q=" + urllib.parse.quote("販売店募集 法人") + "&hl=ja&gl=JP&ceid=JP:ja",
        "https://news.google.com/rss/search?q=" + urllib.parse.quote("代理店募集 法人") + "&hl=ja&gl=JP&ceid=JP:ja",
        "https://news.google.com/rss/search?q=" + urllib.parse.quote("資金調達 実施") + "&hl=ja&gl=JP&ceid=JP:ja",
        "https://news.google.com/rss/search?q=" + urllib.parse.quote("新サービス 開始 法人") + "&hl=ja&gl=JP&ceid=JP:ja",
        "https://news.google.com/rss/search?q=" + urllib.parse.quote("販路拡大 提携") + "&hl=ja&gl=JP&ceid=JP:ja"
    ]
    
    now = datetime.datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    new_entries = []
    
    for url in feeds:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            if is_target_company(entry.title, entry.summary):
                score, tags = analyze_business_tank_fit(entry.title, entry.summary)
                
                title_clean = entry.title.replace("【", " ").replace("】", " ").replace("「", " ").replace("」", " ")
                company = title_clean.split("が")[0].split("の")[0].split("、")[0].strip()[:20]
                new_entries.append([today_str, now.strftime("%H:%M"), company, entry.title, entry.link, score, ",".join(tags)])
    
    # ★ファイル名をv4に変更★
    db_file = "news_database_v4.csv"
    
    if new_entries:
        df_new = pd.DataFrame(new_entries, columns=["date", "time", "company", "title", "url", "score", "tags"])
        if os.path.exists(db_file):
            try:
                df_old = pd.read_csv(db_file)
                if "score" in df_old.columns:
                    df_final = pd.concat([df_new, df_old]).drop_duplicates(subset=["url"], keep="first")
                else:
                    df_final = df_new
            except:
                df_final = df_new
        else:
            df_final = df_new
        
        # スコア順に並び替え（販路拡大系が最上位に来る）
        df_final = df_final.sort_values(by=["date", "score", "time"], ascending=[False, False, False])
        df_final.to_csv(db_file, index=False, encoding="utf_8_sig")
    return len(new_entries)

st.set_page_config(page_title="Business Tank Radar", layout="wide")

st.markdown("""
    <style>
    .stCard { background: white; border-left: 5px solid #ddd; padding: 15px; border-radius: 4px; margin-bottom: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    
    /* ランクごとの色設定 */
    .score-crown { border-left-color: #ff00ff !important; background-color: #fff0ff; } /* 販路拡大（紫） */
    .score-s { border-left-color: #ff4b4b !important; background-color: #fff5f5; } /* 資金調達など（赤） */
    .score-a { border-left-color: #ffa500 !important; } /* その他（オレンジ） */
    
    .tag { display: inline-block; background: #e9ecef; color: #444; padding: 2px 8px; border-radius: 12px; font-size: 11px; margin-right: 5px; margin-bottom: 4px; }
    .crown-tag { background: #fce4ff; color: #a0f; font-weight: bold; border: 1px solid #e0b0ff; }
    .hot-tag { background: #ffe8e8; color: #d00; font-weight: bold; border: 1px solid #ffb3b3; }
    .big-tag { background: #ddd; color: #888; text-decoration: line-through; }
    </style>
    """, unsafe_allow_html=True)

st.title("🎯 ビジネスタンク・見込み客レーダー")

with st.sidebar:
    st.header("設定")
    selected_date = st.date_input("日付選択", datetime.date.today())
    st.divider()
    if st.button("🔄 最新見込み客をスキャン"):
        with st.spinner("「販路拡大」「資金調達」企業を優先スキャン中..."):
            count = fetch_all_sources()
            st.success(f"{count}件の企業を抽出しました")
            st.rerun()

db_file = "news_database_v4.csv"
target_str = selected_date.strftime("%Y-%m-%d")

if os.path.exists(db_file):
    df = pd.read_csv(db_file)
    if "score" in df.columns:
        df = df.sort_values(by=["score", "time"], ascending=[False, False])
        
    display_df = df[df["date"] == target_str]
    st.subheader(f"📅 {target_str} のアプローチ推奨リスト")
    
    if not display_df.empty:
        for _, row in display_df.iterrows():
            score = row.get('score', 0)
            card_class = "stCard"
            rank_label = ""
            
            # ランク判定
            if score >= 10: # 販路拡大・販売店募集
                card_class += " score-crown"
                rank_label = "👑 <span style='color:#c0f;font-weight:bold'>販路拡大ニーズ（激アツ）</span>"
            elif score >= 3: # 資金調達・新サービス
                card_class += " score-s"
                rank_label = "🔥 <span style='color:#d00;font-weight:bold'>攻めの姿勢あり</span>"
            elif score >= 1: # その他
                card_class += " score-a"
                rank_label = "✨ <span style='color:#e69500;font-weight:bold'>変化の予兆</span>"
            elif score < 0:
                rank_label = "<span style='color:#999;font-size:10px;'>※大手・対象外の可能性</span>"
            
            tags_list = str(row['tags']).split(",")
            tag_html = ""
            for t in tags_list:
                if t and t != "nan":
                    if "👑" in t:
                        style = "crown-tag"
                    elif "🔥" in t or "🤝" in t:
                        style = "hot-tag"
                    elif "大手" in t or "プライム" in t:
                        style = "big-tag"
                    else:
                        style = "tag"
                    tag_html += f'<span class="tag {style}">{t}</span>'

            st.markdown(f"""
            <div class="{card_class}">
                <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                    <small style="color:#666;">{row['time']} | {row['company']}</small>
                    <small>{rank_label}</small>
                </div>
                <a href="{row['url']}" target="_blank" style="text-decoration:none; color:#1f77b4; font-weight:bold; font-size:16px; display:block; margin-bottom:8px;">
                    {row['title']}
                </a>
                <div>{tag_html}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("条件に合致する企業は見つかりませんでした。")
else:
    st.warning("データがありません。サイドバーからスキャンを実行してください。")
