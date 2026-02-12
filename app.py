import streamlit as st
import feedparser
import pandas as pd
import datetime
import os
import urllib.parse

# --- 判定ロジック：公共・海外を除外 ---
def is_target_company(title, summary):
    text = (title + summary).lower()
    
    # 1. 官公庁・教育機関などの除外
    exclude_keywords = [
        "大学", "教授", "研究室", "学生", "高校", "学校",
        "市役所", "県庁", "都庁", "区役所", "役場", "省", "庁", "内閣",
        "自治体", "観光協会", "フェスティバル", "祭り", "公募", "入札",
        "機構", "財団", "連合会", "協議会", "警察", "消防"
    ]
    if any(k in text for k in exclude_keywords):
        return False
        
    # 2. 【NEW】海外企業の除外（国内企業に絞る）
    # 「現地時間」「ドル」「元」「ウォン」など海外特有の単語を除外
    foreign_keywords = [
        "現地時間", "ドル", "ユーロ", "元", "ウォン", 
        "米国", "中国", "欧州", "海外本社", "日本法人", "支社"
    ]
    # 記事タイトルに「海外」が強く出るものも避ける（海外進出ならOKだが、海外企業のニュースはNG）
    if any(k in text for k in foreign_keywords):
        return False
        
    return True

# --- ★ビジネスタンク・マッチ度判定ロジック（スタートアップ特化版）★ ---
def analyze_business_tank_fit(title, summary):
    text = (title + summary).lower()
    tags = []
    score = 0

    # 1. 【Crown】販路拡大・販売店募集（最優先）
    # ここは変わらず最強（+10点）
    crown_keywords = [
        "販路拡大", "販路開拓", "販売店募集", "販売店 募集", 
        "代理店募集", "代理店 募集", "パートナー募集"
    ]
    for k in crown_keywords:
        if k in text:
            tags.append(f"👑{k}")
            score += 10

    # 2. 【Startup】成長・スタートアップの動き（激アツ）
    # 資金調達やリリースは「これから伸びる」証拠なので高得点（+5点）
    startup_keywords = [
        "資金調達", "第三者割当", "シリーズa", "シリーズb", "j-kiss",
        "新サービス", "新商品", "プレリリース", "プレスリリース", 
        "ローンチ", "提供開始", "スタートアップ", "ベンチャー", "設立"
    ]
    for k in startup_keywords:
        if k in text:
            tags.append(f"🔥{k}")
            score += 5

    # 3. 【Partnership】提携（優先度ダウン）
    # 大手との提携は不要とのことなので、点数を控えめに（+1点）
    partner_keywords = [
        "提携", "共同研究", "共同開発", "実証実験", "協業", 
        "アライアンス", "オープンイノベーション", "OEM"
    ]
    for k in partner_keywords:
        if k in text:
            tags.append(f"🤝{k}")
            score += 1

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
    # 大手はガードが固いのでリストの下へ
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
    # 検索ワード：スタートアップ・成長企業狙い撃ち
    feeds = [
        "https://prtimes.jp/index.rdf",
        # 資金調達・スタートアップ情報を強化
        "https://news.google.com/rss/search?q=" + urllib.parse.quote("資金調達 実施 スタートアップ") + "&hl=ja&gl=JP&ceid=JP:ja",
        "https://news.google.com/rss/search?q=" + urllib.parse.quote("新サービス 開始 法人") + "&hl=ja&gl=JP&ceid=JP:ja",
        "https://news.google.com/rss/search?q=" + urllib.parse.quote("販売店募集") + "&hl=ja&gl=JP&ceid=JP:ja",
        "https://news.google.com/rss/search?q=" + urllib.parse.quote("代理店募集") + "&hl=ja&gl=JP&ceid=JP:ja",
        # 「販路拡大」そのものを狙う
        "https://news.google.com/rss/search?q=" + urllib.parse.quote("販路拡大 目指す") + "&hl=ja&gl=JP&ceid=JP:ja"
    ]
    
    now = datetime.datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    new_entries = []
    
    for url in feeds:
        feed = feedparser.parse(url)
        for entry in feed
