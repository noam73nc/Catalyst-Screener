"""
GitHub Actions runner — מריץ סריקה ושומר תוצאות ל-results/latest_scan.csv
"""
import os
import json
import re
import pandas as pd
from time import sleep
from google import genai
import yfinance as yf
from tradingview_screener import Query, col

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
client = genai.Client(api_key=GEMINI_API_KEY)

def get_tradingview_scan():
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
        .limit(30)
        .get_scanner_data()
    )
    df = df.rename(columns={
        'name': 'Ticker', 'premarket_change': 'Premkt %',
        'premarket_volume': 'Premkt Vol', 'relative_volume_10d_calc': 'Ext RVol',
        'change': 'Daily %', 'industry': 'Industry', 'market_cap_basic': 'Mkt Cap',
    })
    df['Ticker'] = df['Ticker'].str.split(':').str[-1]
    return df[['Ticker', 'Premkt %', 'Premkt Vol', 'Ext RVol', 'Daily %', 'Industry', 'Mkt Cap']]

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
        news_text = " || ".join(items)
    except Exception:
        pass
    return float_shares, short_interest, news_text

def analyze_catalyst(ticker, news_text, max_retries=3):
    if not news_text or len(news_text) < 10:
        return "Others", "D", "No significant news found.", {}
    prompt = f"""
You are a professional stock market analyst. Analyze news headlines for stock ticker {ticker}.
Return ONLY valid JSON:
{{"Category":"...","Grade":"A","Reasoning":"...","AnalysisDetails":{{"Impact":"...","Explosiveness":"...","DataQuality":"..."}}}}
Category must be one of: ["Earnings","Upgrade/Downgrade","Macro","Themes & Narratives","New Contracts & Partnerships","FDA","M&A","Others"]
Grade: A=strong catalyst, B=solid, C=weak, D=no catalyst
News: {news_text}
"""
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash', contents=prompt,
                config=genai.types.GenerateContentConfig(response_mime_type='application/json')
            )
            raw = re.sub(r'^```json\s*|```$', '', response.text.strip(), flags=re.MULTILINE).strip()
            result = json.loads(raw)
            return (result.get("Category","Others"), result.get("Grade","C"),
                    result.get("Reasoning",""), result.get("AnalysisDetails",{}))
        except Exception as e:
            print(f"  Gemini attempt {attempt+1} failed: {e}")
            if attempt < max_retries - 1:
                sleep(8)
    return "Others", "D", "Gemini API unavailable.", {}

def main():
    print("Fetching TradingView scan...")
    df = get_tradingview_scan()
    print(f"Found {len(df)} stocks. Analyzing...")

    floats, shorts, categories, grades, reasonings, details_list = [], [], [], [], [], []
    for i, (_, row) in enumerate(df.iterrows()):
        ticker = row['Ticker']
        print(f"  [{i+1}/{len(df)}] {ticker}")
        float_sh, short_int, news_text = get_fundamentals_and_news(ticker)
        floats.append(float_sh)
        shorts.append(short_int)
        sleep(3)
        category, grade, reasoning, details = analyze_catalyst(ticker, news_text)
        categories.append(category)
        grades.append(grade)
        reasonings.append(reasoning)
        details_list.append(json.dumps(details))
        print(f"         -> {category} | Grade {grade}")

    df['Float'] = floats
    df['Short Interest'] = shorts
    df['Category'] = categories
    df['Grade'] = grades
    df['Reasoning'] = reasonings
    df['AnalysisDetails'] = details_list

    os.makedirs('results', exist_ok=True)
    df.to_csv('results/latest_scan.csv', index=False)
    print(f"Saved results/latest_scan.csv ({len(df)} rows)")

if __name__ == "__main__":
    main()
