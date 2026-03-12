"""
GitHub Actions runner — מריץ סריקה בשיטת Batch ושומר תוצאות ל-results/latest_scan.csv
"""
import os
import json
import re
import pandas as pd
import urllib.request
from time import sleep
from google import genai
import yfinance as yf
from tradingview_screener import Query, col

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
client = genai.Client(api_key=GEMINI_API_KEY)

def get_tradingview_scan():
    print("Fetching pre-market leaders from TradingView...")
    try:
        count, df = (
            Query()
            .select('name', 'premarket_change', 'premarket_volume', 'relative_volume_10d_calc', 'change', 'industry', 'market_cap_basic')
            .where(
                col('premarket_volume') > 100000,
                col('type').isin(['stock']),
                col('exchange').isin(['NASDAQ', 'NYSE']),
                col('market_cap_basic') > 300000000
            )
            .order_by('premarket_change', ascending=False)
            .limit(30) # סורק עד 30 מניות
            .get_scanner_data()
        )
        df = df.rename(columns={
            'name': 'Ticker', 'premarket_change': 'Premkt %',
            'premarket_volume': 'Premkt Vol', 'relative_volume_10d_calc': 'Ext RVol',
            'change': 'Daily %', 'industry': 'Industry', 'market_cap_basic': 'Mkt Cap',
        })
        df['Ticker'] = df['Ticker'].str.split(':').str[-1]
        return df[['Ticker', 'Premkt %', 'Premkt Vol', 'Ext RVol', 'Daily %', 'Industry', 'Mkt Cap']]
    except Exception as e:
        print(f"TradingView scan failed: {e}")
        return pd.DataFrame()

def get_google_news(ticker: str, company_name: str = "") -> str:
    try:
        query = f"{ticker} stock" if not company_name else f"{ticker} {company_name}"
        query_enc = query.replace(' ', '+')
        url = f"https://news.google.com/rss/search?q={query_enc}&hl=en-US&gl=US&ceid=US:en"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = resp.read().decode('utf-8', errors='ignore')
        titles = re.findall(r'<title>(.*?)</title>', raw)
        titles = [t for t in titles if 'Google News' not in t and len(t) > 10][:6]
        if titles:
            return " || ".join(f"Title: {t}" for t in titles)
    except Exception:
        pass
    return ""

def get_fundamentals_and_news(ticker):
    float_shares, short_interest, news_text = 'N/A', 'N/A', ""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        float_shares = info.get('floatShares', 'N/A')
        si = info.get('shortPercentOfFloat', 'N/A')
        if si not in ('N/A', None):
            short_interest = round(si * 100, 2)
            
        items = []
        for article in (stock.news or [])[:5]:
            content = article.get('content', {})
            title = content.get('title', '') or article.get('title', '')
            provider = content.get('provider', {}).get('displayName', '') or article.get('publisher', '')
            if title:
                items.append(f"Title: {title} | Source: {provider}")
        yf_news = " || ".join(items)
        company_name = info.get('shortName', '')
    except Exception:
        yf_news = ""
        company_name = ""

    google_news = get_google_news(ticker, company_name)
    combined = []
    if google_news: combined.append(f"[Google News] {google_news}")
    if yf_news: combined.append(f"[Yahoo Finance] {yf_news}")
    news_text = " ||| ".join(combined) if combined else ""

    return float_shares, short_interest, news_text

def analyze_all_stocks_batch(stocks_data: list, max_retries: int = 3) -> list:
    if not stocks_data: return []

    stocks_input = ""
    for s in stocks_data:
        stocks_input += f"Ticker: {s['Ticker']} | Move: {s['pm_pct']}% | News: {s['news_text']}\n---\n"

    prompt = f"""
אתה אנליסט שוק מקצועי. נתח את רשימת המניות הבאה.
לכל מניה, זהה את הקטליזטור הספציפי לתנועת הפרה-מרקט שלה.
החזר JSON תקין במבנה של מערך (Array) של אובייקטים. הטקסטים חייבים להיות בעברית.

"Category" חייב להיות אחד מאלה: ["Earnings","Upgrade/Downgrade","Macro","Themes & Narratives","New Contracts & Partnerships","FDA","M&A","Stock Offering/Dilution","Others"]
"Grade" חייב להיות אחד מאלה: A, B, C, D
"Direction" חייב להיות: "bullish", "bearish", או "neutral"

רשימת המניות והחדשות:
{stocks_input}

מבנה ה-JSON:
[
  {{
    "Ticker": "AAPL",
    "Category": "...",
    "Grade": "...",
    "Direction": "...",
    "Reasoning": "סיכום בעברית...",
    "Impact": "...",
    "Explosiveness": "...",
    "DataQuality": "..."
  }}
]
"""
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash', contents=prompt,
                config=genai.types.GenerateContentConfig(response_mime_type='application/json')
            )
            raw = re.sub(r'^```json\s*|```$', '', response.text.strip(), flags=re.MULTILINE).strip()
            return json.loads(raw)
        except Exception as e:
            print(f"  Gemini batch attempt {attempt+1} failed: {e}")
            if attempt < max_retries - 1: sleep(8)
    return []

def main():
    df = get_tradingview_scan()
    if df.empty:
        print("No stocks found or scan failed.")
        return

    total = len(df)
    print(f"Found {total} stocks. Gathering fundamentals & news...")

    floats, shorts, stocks_for_api = [], [], []
    for i, (_, row) in enumerate(df.iterrows()):
        ticker = row['Ticker']
        print(f"  [{i+1}/{total}] Gathering data for {ticker}...")
        float_sh, short_int, news_text = get_fundamentals_and_news(ticker)
        floats.append(float_sh)
        shorts.append(short_int)
        
        try: pm_pct = float(row['Premkt %'])
        except: pm_pct = 0
            
        stocks_for_api.append({"Ticker": ticker, "pm_pct": pm_pct, "news_text": news_text})
        sleep(0.5)

    df['Float'] = floats
    df['Short Interest'] = shorts

    print(f"Sending batch request to Gemini API for {total} stocks...")
    batch_results = analyze_all_stocks_batch(stocks_for_api)
    results_dict = {item.get("Ticker"): item for item in batch_results if isinstance(item, dict)}
    
    categories, grades, directions, reasonings, details_list = [], [], [], [], []
    for ticker in df['Ticker']:
        res = results_dict.get(ticker, {})
        categories.append(res.get("Category", "Others"))
        grades.append(res.get("Grade", "C"))
        directions.append(res.get("Direction", "neutral"))
        reasonings.append(res.get("Reasoning", "לא התקבל ניתוח מהמודל."))
        details_list.append(json.dumps({
            "Impact": res.get("Impact", ""),
            "Explosiveness": res.get("Explosiveness", ""),
            "DataQuality": res.get("DataQuality", "")
        }))

    df['Category'] = categories
    df['Grade'] = grades
    df['Direction'] = directions
    df['Reasoning'] = reasonings
    df['AnalysisDetails'] = details_list

    os.makedirs('results', exist_ok=True)
    df.to_csv('results/latest_scan.csv', index=False)
    print(f"Saved results/latest_scan.csv ({len(df)} rows)")

if __name__ == "__main__":
    main()
