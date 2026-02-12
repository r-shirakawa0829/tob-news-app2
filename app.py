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

# --- ★ビジネスタンク・マッチ度判定ロジック★ ---
def analyze_business_tank_fit(title, summary):
    text = (title + summary).lower()
    tags = []
    score = 0

    # 1. 【User指定】成長・変化の意思（基本ターゲット）
    # 「上場」は大手すぎる可能性があるため削除。「IPO」は残す。
    growth_keywords = [
        "販路拡大", "資金調達", "採用強化", "吸収合併", "新規事業", 
        "新サービス", "社内体制の一新", "プレリリース", "事業拡大",
        "IPO", "黒字化"
    ]
    for k in growth_keywords:
        if k in text:
            tags.append(f"📈{k}")
            score += 1

    # 2. 【Analysis】パートナー不足・販路課題（ビジネスタンクが最も刺さる）
    partner_keywords = [
        "提携", "共同研究", "共同開発", "実証実験", "協業", 
        "アライアンス", "オープンイノベーション", "OEM", "代理店募集",
        "パートナー募集", "販路開拓"
    ]
    for k in partner_keywords:
        if k in text:
            tags.append(f"🤝{k}")
            score += 2 

    # 3. 【Analysis】トップの決断・変革期
    change_keywords = [
        "社長就任", "代表変更", "新体制", "経営計画", "刷新",
        "DX推進", "生産性向上", "コスト削減"
    ]
    for k in change_keywords:
        if k in text:
            tags.append(f"⚡{k}")
            score += 1

    # 4. 【NEW】大手・有名企業の減点（ペナルティ）
    # 大手はトップアプローチが難しいため、優先度を下げる
    big_company_keywords = [
        "大手", "最大手", "業界トップ", "東証プライム", "老舗", 
        "有名", "ホールディングス", "グループ"
    ]
    for k in big_company_keywords:
        if k in text:
            score -= 10 # 大きく減点してリストの下に送る
            tags.append(f"🏢{k}(大手)")

    return score, list(set(tags))

def fetch_all_sources():
    feeds = [
        "https://prtimes.jp/index.rdf",
        "https://news.google.com/rss/search?q=" + urllib.parse.quote("新規事業 開始") + "&hl=ja&gl=JP&ceid=JP:ja",
        "https://news.google.com/rss/search?q=" + urllib.parse.quote("資金調達 実施") + "&hl=ja&gl=JP&ceid=JP:ja",
        "https://news.google.com/rss/search?q=" + urllib.parse.quote("業務提携") + "&hl=ja&gl=JP&ceid=JP:ja",
        "https://news.google.com/rss/search?q=" + urllib.parse.quote("販売代理店 募集") + "&hl=ja&gl=JP&ceid=JP:ja"
    ]
    
    now = datetime.datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    new_entries = []
    
    for url in feeds:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            if is_target_company(entry.title, entry.summary):
                score, tags = analyze_business_tank_fit(entry.title, entry.summary)
                # スコアがマイナス（大手）でも一応リストには残すが、表示順は下になる
                # まったく表示したくない場合はここで `if score > 0:` に戻してください
                title_clean = entry.title.replace("【", " ").replace("】", " ").replace("「", " ").replace("」", " ")
                company = title_clean.split("が")[0].split("の")[0].split("、")[0].strip()[:20]
                new_entries.append([today_str, now.strftime("%H:%M"), company, entry.title, entry.link, score, ",".join(tags)])
    
    # ★ファイル名をv3に変更してリセット★
    db_file = "news_database_v3.csv"
    
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
        
        # スコアが高い順（＝アツい企業順）に並び替え。大手はスコアが低いので下に行く。
        df_final = df_final.sort_values(by=["date", "score", "time"], ascending=[False, False, False])
        df_final.to_csv(db_file, index=False, encoding="utf_8_sig")
    return len(new_entries)

st.set_page_config(page_title="Business Tank Radar", layout="wide")

st.markdown("""
    <style>
    .stCard { background: white; border-left: 5px solid #ddd; padding: 15px; border-radius: 4px; margin-bottom: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .score-s { border-left-color: #ff4b4b !important; background-color: #fff5f5; }
    .score-a { border-left-color: #ffa500 !important; }
    .tag { display: inline-block; background: #e9ecef; color: #444; padding: 2px 8px; border-radius: 12px; font-size: 11px; margin-right: 5px; margin-bottom: 4px; }
    .hot-tag { background: #ffe8e8; color: #d00; font-weight: bold; border: 1px solid #ffb3b3; }
    .big-tag { background: #ddd; color: #888; text-decoration: line-through; } /* 大手タグは目立たなくする */
    </style>
    """, unsafe_allow_html=True)

st.title("🎯 ビジネスタンク・見込み客レーダー")

with st.sidebar:
    st.header("設定")
    selected_date = st.date_input("日付選択", datetime.date.today())
    st.divider()
    if st.button("🔄 最新見込み客をスキャン"):
        with st.spinner("大手を除外し、有望企業を分析中..."):
            count = fetch_all_sources()
            st.success(f"{count}件の企業を抽出しました")
            st.rerun()

db_file = "news_database_v3.csv"
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
            
            # スコア基準
            if score >= 3:
                card_class += " score-s"
                rank_label = "🔥 <span style='color:#d00;font-weight:bold'>Sランク（最優先）</span>"
            elif score >= 2:
                card_class += " score-a"
                rank_label = "✨ <span style='color:#e69500;font-weight:bold'>Aランク（狙い目）</span>"
            elif score < 0:
                rank_label = "<span style='color:#999;font-size:10px;'>※大手・対象外の可能性</span>"
            
            tags_list = str(row['tags']).split(",")
            tag_html = ""
            for t in tags_list:
                if t and t != "nan":
                    # 大手タグはグレーアウト
                    if "大手" in t or "プライム" in t:
                        style = "big-tag"
                    elif any(w in t for w in ["販路", "資金", "採用", "新規", "提携"]):
                        style = "hot-tag"
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
