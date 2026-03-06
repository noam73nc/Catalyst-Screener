import streamlit as st
import pandas as pd
import yfinance as yf
import google.generativeai as genai
import json
import os
import re
from time import sleep
from dotenv import load_dotenv
from tradingview_screener import Query, col

# ─── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Catalyst Screener", page_icon="🚀", layout="wide")

# ─── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Inter:wght@300;400;500;600&display=swap');

  html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #080d14;
    color: #c9d1d9;
  }

  .main-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.6rem;
    font-weight: 600;
    color: #e6edf3;
    letter-spacing: -0.5px;
    margin-bottom: 0.2rem;
  }

  .sub-title {
    font-size: 0.82rem;
    color: #5c6b7a;
    margin-bottom: 1.5rem;
    font-family: 'JetBrains Mono', monospace;
  }

  div.stButton > button {
    background: linear-gradient(135deg, #1a56db, #1e3a8a);
    color: #e2eaff;
    border: 1px solid #2563eb;
    border-radius: 6px;
    padding: 0.5rem 1.4rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.82rem;
    font-weight: 600;
    letter-spacing: 0.5px;
    transition: all 0.2s;
  }
  div.stButton > button:hover {
    background: linear-gradient(135deg, #2563eb, #1d4ed8);
    border-color: #60a5fa;
    color: #fff;
  }

  .scanner-table {
    width: 100%;
    border-collapse: collapse;
    font-family: 'Inter', sans-serif;
    background: #0d1117;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 4px 24px rgba(0,0,0,0.5);
    font-size: 12.5px;
  }
  .scanner-table thead tr {
    background: #161b22;
    border-bottom: 1px solid #21262d;
  }
  .scanner-table th {
    color: #484f58;
    padding: 12px 14px;
    text-align: left;
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    white-space: nowrap;
  }
  .scanner-table td {
    padding: 13px 14px;
    border-bottom: 1px solid #161b22;
    vertical-align: middle;
    color: #8b949e;
  }
  .scanner-table tbody tr:hover {
    background: #161b22;
  }
  .scanner-table tbody tr:last-child td {
    border-bottom: none;
  }

  .ticker-cell {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    text-decoration: none;
  }
  .ticker-dot {
    width: 6px; height: 6px;
    background: #1a56db;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .ticker-label {
    color: #e6edf3;
    font-family: 'JetBrains Mono', monospace;
    font-weight: 600;
    font-size: 13px;
    letter-spacing: 0.3px;
  }
  .ticker-cell:hover .ticker-label { color: #60a5fa; }

  .green  { color: #3fb950; font-weight: 600; }
  .red    { color: #f85149; font-weight: 600; }
  .muted  { color: #484f58; }

  .badge {
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 10.5px;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: 0.5px;
    display: inline-block;
    white-space: nowrap;
  }
  .b-EARNINGS  { background:#033a20; color:#3fb950; border:1px solid #238636; }
  .b-MACRO     { background:#0d2044; color:#79c0ff; border:1px solid #1f6feb; }
  .b-UPGRADE   { background:#2d1a00; color:#ffa657; border:1px solid #9e4a00; }
  .b-FDA       { background:#1e0a40; color:#d2a8ff; border:1px solid #6e40c9; }
  .b-MA        { background:#3d0025; color:#ff7eb3; border:1px solid #ad0060; }
  .b-CONTRACT  { background:#012a18; color:#56d364; border:1px solid #196c2e; }
  .b-GUIDANCE  { background:#012a18; color:#56d364; border:1px solid #196c2e; }
  .b-OTHERS    { background:#1c2128; color:#8b949e; border:1px solid #30363d; }
  .b-UNKNOWN   { background:#1c2128; color:#484f58; border:1px solid #21262d; }
  .b-ERROR     { background:#3d0000; color:#ff7b72; border:1px solid #b91c1c; }

  .reasoning {
    color: #6e7681;
    font-size: 11.5px;
    line-height: 1.55;
    max-width: 340px;
  }

  .stat-row {
    display: flex;
    gap: 2rem;
    margin-bottom: 1.2rem;
  }
  .stat-box {
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 8px;
    padding: 10px 18px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    color: #484f58;
  }
  .stat-box span {
    color: #e6edf3;
    font-weight: 600;
  }
</style>
""", unsafe_allow_html=True)

# ─── API Setup ─────────────────────────────────────────────────────────────────
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    st.error("❌ Missing GEMINI_API_KEY in .env file.")
    st.stop()

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(
    'gemini-2.5-flash',
    generation_config={"response_mime_type": "application/json"}
)

# ─── Data Functions ────────────────────────────────────────────────────────────

def get_tradingview_scan() -> pd.DataFrame:
    """
    Fetch pre-market movers using the tradingview-screener library.
    This is more stable and maintainable than raw requests.
    """
    try:
        count, df = (
            Query()
            .select(
                'name',
                'premarket_change',
                'premarket_volume',
                'relative_volume_10d_calc',
                'change',
                'industry'
            )
            .where(
                col('premarket_volume') > 50000,
                col('type').isin(['stock', 'dr', 'fund'])
            )
            .order_by('premarket_change', ascending=False)
            .limit(15)
            .get_scanner_data()
        )

        df = df.rename(columns={
            'name':                    'Ticker',
            'premarket_change':        'Premkt %',
            'premarket_volume':        'Premkt Vol',
            'relative_volume_10d_calc':'Ext RVol',
            'change':                  'Daily %',
            'industry':                'Industry',
        })

        # Strip exchange prefix (e.g. "NASDAQ:AAPL" → "AAPL")
        df['Ticker'] = df['Ticker'].str.split(':').str[-1]

        return df[['Ticker', 'Premkt %', 'Premkt Vol', 'Ext RVol', 'Daily %', 'Industry']]

    except Exception as e:
        st.error(f"TradingView scan failed: {e}")
        return pd.DataFrame()


def get_fundamentals_and_news(ticker: str):
    """
    Fetch float, short interest, and recent news headlines via yfinance.
    yfinance.news is more reliable than Google News RSS and avoids rate-limit blocks.
    """
    float_shares = 'N/A'
    short_interest = 'N/A'
    news_text = ""

    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        float_shares = info.get('floatShares', 'N/A')

        si = info.get('shortPercentOfFloat', 'N/A')
        if si != 'N/A' and si is not None:
            short_interest = round(si * 100, 2)

        # yfinance news: list of dicts with 'title', 'publisher', 'providerPublishTime'
        raw_news = stock.news or []
        items = []
        for article in raw_news[:5]:
            content = article.get('content', {})
            title = content.get('title', '') or article.get('title', '')
            provider = content.get('provider', {}).get('displayName', '') or article.get('publisher', '')
            if title:
                items.append(f"Title: {title} | Source: {provider}")

        news_text = " || ".join(items)

    except Exception:
        pass

    return float_shares, short_interest, news_text


def analyze_catalyst_with_gemini(ticker: str, news_text: str, max_retries: int = 3):
    """
    Use Gemini Flash to categorize the catalyst and produce a brief reasoning.
    Retries up to max_retries times on API errors.
    """
    if not news_text or len(news_text) < 10:
        return "UNKNOWN", "No significant news found."

    prompt = f"""
Analyze these recent news headlines for stock ticker {ticker}.
Identify the most likely catalyst for its current pre-market move.

Categorize into EXACTLY one of:
[EARNINGS, MACRO, UPGRADE, FDA, M&A, CONTRACT, GUIDANCE, UNKNOWN, OTHERS]

Provide a concise 1-2 sentence reasoning in English.

News:
{news_text}

Respond ONLY with this JSON:
{{"Category": "CATEGORY_NAME", "Reasoning": "Your reasoning here."}}
"""

    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            raw = response.text.strip()
            # Strip markdown code fences if present
            raw = re.sub(r'^```json\s*|```$', '', raw, flags=re.MULTILINE).strip()
            result = json.loads(raw)
            return result.get("Category", "UNKNOWN"), result.get("Reasoning", "Analysis failed.")
        except Exception:
            if attempt < max_retries - 1:
                sleep(8)
            else:
                return "ERROR", "Gemini API unavailable after retries."


# ─── Table Renderer ────────────────────────────────────────────────────────────

def fmt_num(n) -> str:
    try:
        n = float(n)
        if n >= 1_000_000: return f"{n / 1_000_000:.1f}M"
        if n >= 1_000:     return f"{n / 1_000:.0f}K"
        return str(int(n))
    except:
        return str(n)


def render_table(df: pd.DataFrame) -> str:
    rows = ""
    for _, row in df.iterrows():
        ticker = row['Ticker']
        tv_url = f"https://www.tradingview.com/chart/?symbol={ticker}"

        # Premkt %
        try:
            pm = float(row['Premkt %'])
            pm_str = f"+{pm:.2f}%" if pm > 0 else f"{pm:.2f}%"
            pm_cls = "green" if pm > 0 else "red"
        except:
            pm_str, pm_cls = str(row['Premkt %']), "muted"

        # Daily %
        try:
            dp = float(row['Daily %'])
            dp_str = f"+{dp:.2f}%" if dp > 0 else f"{dp:.2f}%"
            dp_cls = "green" if dp > 0 else ("red" if dp < 0 else "muted")
        except:
            dp_str, dp_cls = str(row['Daily %']), "muted"

        # RVol
        try:
            rvol = f"{float(row['Ext RVol']):.2f}x"
        except:
            rvol = "N/A"

        # Short interest
        si = row.get('Short Interest', 'N/A')
        si_str = f"{si:.2f}%" if isinstance(si, (int, float)) else "N/A"

        # Badge class
        cat = str(row.get('Category', 'UNKNOWN')).upper().replace('&', '').replace('/', '').replace(' ', '')
        badge_map = {
            'MA': 'MA', 'M&A': 'MA', 'MERGERS': 'MA',
        }
        badge_cls = badge_map.get(cat, cat)

        industry = str(row.get('Industry', ''))[:20]
        reasoning = str(row.get('Reasoning', ''))

        rows += f"""
        <tr>
          <td><a href="{tv_url}" target="_blank" class="ticker-cell">
            <span class="ticker-dot"></span>
            <span class="ticker-label">{ticker}</span>
          </a></td>
          <td class="{pm_cls}">{pm_str}</td>
          <td class="muted">{fmt_num(row['Premkt Vol'])}</td>
          <td class="muted">{rvol}</td>
          <td class="{dp_cls}">{dp_str}</td>
          <td class="muted">{si_str}</td>
          <td class="muted">{fmt_num(row['Float'])}</td>
          <td class="muted">{industry}</td>
          <td><span class="badge b-{badge_cls}">{cat}</span></td>
          <td class="reasoning">{reasoning}</td>
        </tr>"""

    return f"""
    <table class="scanner-table">
      <thead>
        <tr>
          <th>Ticker</th>
          <th>Premkt %</th>
          <th>Premkt Vol</th>
          <th>Ext RVol</th>
          <th>Daily %</th>
          <th>Short Int.</th>
          <th>Float</th>
          <th>Industry</th>
          <th>Category</th>
          <th>Reasoning</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>"""


# ─── UI ────────────────────────────────────────────────────────────────────────

st.markdown('<div class="main-title">🚀 Catalyst Screener</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">Pre-market gap scanner · TradingView + yFinance + Gemini AI</div>',
    unsafe_allow_html=True
)

if st.button("▶  Run New Scan", type="primary"):

    with st.spinner("Fetching pre-market leaders from TradingView..."):
        df = get_tradingview_scan()

    if df.empty:
        st.warning("⚠️ No data returned. Market may be closed or API is unavailable.")
        st.stop()

    total = len(df)
    st.success(f"✓ Found {total} stocks. Enriching with fundamentals & AI analysis...")

    progress = st.progress(0)
    status   = st.empty()

    floats, shorts, categories, reasonings = [], [], [], []

    for i, (_, row) in enumerate(df.iterrows()):
        ticker = row['Ticker']
        status.markdown(
            f"<span style='font-family:JetBrains Mono,monospace;font-size:12px;color:#484f58'>"
            f"Analyzing {ticker} ({i+1}/{total})...</span>",
            unsafe_allow_html=True
        )

        float_sh, short_int, news_text = get_fundamentals_and_news(ticker)
        floats.append(float_sh)
        shorts.append(short_int)

        sleep(3)  # gentle throttle — yfinance is less aggressive than Google RSS

        category, reasoning = analyze_catalyst_with_gemini(ticker, news_text)
        categories.append(category)
        reasonings.append(reasoning)

        progress.progress((i + 1) / total)

    df['Float']         = floats
    df['Short Interest'] = shorts
    df['Category']      = categories
    df['Reasoning']     = reasonings

    status.empty()
    progress.empty()

    # ── Stats row ─────────────────────────────────────────────────────────────
    earnings_n = sum(1 for c in categories if c == 'EARNINGS')
    unknown_n  = sum(1 for c in categories if c in ('UNKNOWN', 'ERROR'))
    avg_pm     = df['Premkt %'].apply(pd.to_numeric, errors='coerce').mean()

    st.markdown(f"""
    <div class="stat-row">
      <div class="stat-box">Stocks scanned <span>{total}</span></div>
      <div class="stat-box">Earnings plays <span>{earnings_n}</span></div>
      <div class="stat-box">Avg premkt move <span>+{avg_pm:.1f}%</span></div>
      <div class="stat-box">Unidentified <span>{unknown_n}</span></div>
    </div>
    """, unsafe_allow_html=True)

    # ── Table ──────────────────────────────────────────────────────────────────
    st.write(render_table(df), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download CSV",
        data=csv,
        file_name="catalyst_scan.csv",
        mime="text/csv"
    )
