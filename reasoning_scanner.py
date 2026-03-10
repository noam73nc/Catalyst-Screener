import streamlit as st
import pandas as pd
import yfinance as yf
from google import genai
import json
import os
import re
from time import sleep
from tradingview_screener import Query, col

# ─── API KEY ──────────────────────────────────────────────────────────────────
# בענן: מגיע מ-Streamlit Secrets | בלוקאל: שנה ל-string ישיר
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    GEMINI_API_KEY = "ENTER_YOUR_KEY_HERE"
# ──────────────────────────────────────────────────────────────────────────────
client = genai.Client(api_key=GEMINI_API_KEY)

st.set_page_config(page_title="Catalyst Screener", page_icon="🚀", layout="wide")

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@400;500;600;700&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; background-color: #1a1d23; color: #e2e8f0; }
  .main-title { font-family: 'JetBrains Mono', monospace; font-size: 1.7rem; font-weight: 700; color: #f1f5f9; letter-spacing: -0.5px; margin-bottom: 0.2rem; }
  .sub-title { font-size: 0.83rem; color: #94a3b8; margin-bottom: 1.5rem; font-family: 'JetBrains Mono', monospace; }
  div.stButton > button { background: linear-gradient(135deg, #2563eb, #1d4ed8); color: #fff; border: none; border-radius: 7px; padding: 0.55rem 1.6rem; font-family: 'JetBrains Mono', monospace; font-size: 0.83rem; font-weight: 700; letter-spacing: 0.5px; box-shadow: 0 2px 8px rgba(37,99,235,0.4); transition: all 0.2s; }
  div.stButton > button:hover { background: linear-gradient(135deg, #3b82f6, #2563eb); }

  /* ── Table ── */
  .sc-table { width: 100%; border-collapse: collapse; font-family: 'Inter', sans-serif; font-size: 12.5px; table-layout: fixed; }
  .sc-table thead tr { background: #1e2130; border-bottom: 2px solid #2e3340; }
  .sc-table th { color: #f1f5f9 !important; padding: 10px 10px; text-align: left; font-weight: 700; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; white-space: nowrap; overflow: hidden; }
  .sc-table tbody tr { border-bottom: 1px solid #252830; transition: background 0.1s; }
  .sc-table tbody tr:nth-child(odd)  { background: #1e2130; }
  .sc-table tbody tr:nth-child(even) { background: #222631; }
  .sc-table tbody tr:hover { background: #2a2f3e !important; }
  .sc-table td { padding: 10px 10px; vertical-align: middle; color: #cbd5e1; overflow: hidden; }
  /* ── Fixed column widths ── */
  .sc-table th:nth-child(1),  .sc-table td:nth-child(1)  { width: 70px; }   /* Ticker */
  .sc-table th:nth-child(2),  .sc-table td:nth-child(2)  { width: 85px; }   /* Premkt % */
  .sc-table th:nth-child(3),  .sc-table td:nth-child(3)  { width: 72px; }   /* Pre Vol */
  .sc-table th:nth-child(4),  .sc-table td:nth-child(4)  { width: 75px; }   /* RVol */
  .sc-table th:nth-child(5),  .sc-table td:nth-child(5)  { width: 85px; }   /* Daily % */
  .sc-table th:nth-child(6),  .sc-table td:nth-child(6)  { width: 85px; }   /* Short Int */
  .sc-table th:nth-child(7),  .sc-table td:nth-child(7)  { width: 62px; }   /* Float */
  .sc-table th:nth-child(8),  .sc-table td:nth-child(8)  { width: 130px; }  /* Industry */
  .sc-table th:nth-child(9),  .sc-table td:nth-child(9)  { width: 160px; }  /* Category */
  .sc-table th:nth-child(10), .sc-table td:nth-child(10) { width: 64px; }   /* Grade */
  .sc-table th:nth-child(11), .sc-table td:nth-child(11) { width: auto; }   /* Reasoning - fills rest */
  .sc-table th:nth-child(12), .sc-table td:nth-child(12) { width: 85px; }   /* Analysis */

  /* ── Ticker ── */
  .tk { display:inline-flex; align-items:center; gap:7px; text-decoration:none; }
  .tk-dot { width:6px; height:6px; background:#3b82f6; border-radius:50%; box-shadow:0 0 5px rgba(59,130,246,0.7); }
  .tk-name { color:#f1f5f9; font-family:'JetBrains Mono',monospace; font-weight:700; font-size:13px; }
  .tk:hover .tk-name { color:#60a5fa; }

  /* ── Numbers ── */
  .gn { color:#4ade80 !important; font-weight:700; }
  .rd { color:#f87171 !important; font-weight:700; }
  .mu { color:#94a3b8 !important; }

  /* ── Category badges ── */
  .bdg { padding:3px 9px; border-radius:14px; font-size:10px; font-weight:800; display:inline-block; white-space:nowrap; line-height:1.5; font-family:'Inter',sans-serif; }
  .bEarnings                 { background:#064e3b; color:#6ee7b7; border:1.5px solid #10b981; }
  .bUpgradeDowngrade         { background:#431407; color:#fdba74; border:1.5px solid #f97316; }
  .bMacro                    { background:#1e3a5f; color:#93c5fd; border:1.5px solid #3b82f6; }
  .bThemesNarratives         { background:#1a1040; color:#a5b4fc; border:1.5px solid #6366f1; }
  .bNewContractsPartnerships { background:#0c2340; color:#7dd3fc; border:1.5px solid #0ea5e9; }
  .bFDA                      { background:#2e1065; color:#c4b5fd; border:1.5px solid #8b5cf6; }
  .bMA                       { background:#500724; color:#fda4af; border:1.5px solid #f43f5e; }
  .bOthers                   { background:#2d3748; color:#e2e8f0; border:1.5px solid #64748b; }

  /* ── Grade circle ── */
  .gc { width:27px; height:27px; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; font-family:'JetBrains Mono',monospace; font-weight:800; font-size:12px; }
  .gA { background:#064e3b; color:#6ee7b7; border:2px solid #10b981; }
  .gB { background:#1e3a5f; color:#93c5fd; border:2px solid #3b82f6; }
  .gC { background:#431407; color:#fdba74; border:2px solid #f97316; }
  .gD { background:#450a0a; color:#fca5a5; border:2px solid #ef4444; }

  /* ── Reasoning ── */
  .rsn { color:#cbd5e1 !important; font-size:11.5px; line-height:1.6; }

  /* ── Analysis expand ── */
  .ad-wrap { font-size:11.5px; }
  details summary { cursor:pointer; color:#64748b; font-size:10.5px; font-family:'JetBrains Mono',monospace; list-style:none; display:inline-flex; align-items:center; gap:4px; padding:2px 8px; border:1px solid #3d4456; border-radius:20px; background:#252830; user-select:none; }
  details summary::-webkit-details-marker { display:none; }
  details[open] summary { color:#93c5fd; border-color:#3b82f6; background:#1e2a40; }
  .ad-box { margin-top:8px; padding:10px 12px; background:#151b2e; border-left:3px solid #3b82f6; border-radius:0 6px 6px 0; }
  .ad-sec { margin-bottom:8px; }
  .ad-sec:last-child { margin-bottom:0; }
  .ad-title { color:#e2e8f0; font-weight:700; font-size:10.5px; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:3px; }
  .ad-body  { color:#94a3b8; font-size:11px; line-height:1.65; }

  /* ── Stats ── */
  .stat-row { display:flex; gap:1rem; margin-bottom:1.2rem; flex-wrap:wrap; }
  .stat-box { background:#1e2130; border:1.5px solid #2e3340; border-radius:8px; padding:9px 18px; font-family:'JetBrains Mono',monospace; font-size:0.77rem; color:#64748b; }
  .stat-box span { color:#f1f5f9; font-weight:700; margin-left:5px; }
</style>
""", unsafe_allow_html=True)


def get_tradingview_scan() -> pd.DataFrame:
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
    except Exception as e:
        st.error(f"TradingView scan failed: {e}")
        return pd.DataFrame()


def get_fundamentals_and_news(ticker: str):
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
        raw_news = stock.news or []
        items = []
        for article in raw_news[:5]:
            c = article.get('content', {})
            title = c.get('title', '') or article.get('title', '')
            provider = c.get('provider', {}).get('displayName', '') or article.get('publisher', '')
            if title:
                items.append(f"Title: {title} | Source: {provider}")
        news_text = " || ".join(items)
    except Exception:
        pass
    return float_shares, short_interest, news_text


def analyze_catalyst_with_gemini(ticker: str, news_text: str, max_retries: int = 3):
    if not news_text or len(news_text) < 10:
        return "Others", "D", "No significant news found.", {}
    prompt = f"""
You are a professional stock market analyst. Analyze news headlines for stock ticker {ticker}.
Return ONLY valid JSON with these fields:

"Category": EXACTLY one of: ["Earnings","Upgrade/Downgrade","Macro","Themes & Narratives","New Contracts & Partnerships","FDA","M&A","Others"]
"Grade": A (strong clear catalyst), B (solid, some uncertainty), C (weak/indirect), D (no clear catalyst)
"Reasoning": 2-3 sentence summary of why the stock is moving.
"AnalysisDetails": object with:
  "Impact": financial/business impact, is it material?
  "Explosiveness": why is it moving aggressively? institutional flow, short squeeze, sector beta?
  "DataQuality": how reliable is the news? confirmed or speculative?

News: {news_text}

JSON format:
{{"Category":"...","Grade":"A","Reasoning":"...","AnalysisDetails":{{"Impact":"...","Explosiveness":"...","DataQuality":"..."}}}}
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
        except Exception:
            if attempt < max_retries - 1: sleep(8)
            else: return "Others", "D", "Gemini API unavailable.", {}


def fmt_num(n) -> str:
    try:
        n = float(n)
        if n >= 1_000_000_000: return f"{n/1_000_000_000:.1f}B"
        if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
        if n >= 1_000:     return f"{n/1_000:.0f}K"
        return str(int(n))
    except: return str(n)

def pct_str(val):
    try:
        v = float(val)
        cls = "gn" if v > 0 else ("rd" if v < 0 else "mu")
        s = f"+{v:.2f}%" if v > 0 else f"{v:.2f}%"
        return cls, s
    except: return "mu", str(val)


# ─── UI ────────────────────────────────────────────────────────────────────────
st.markdown('<div class="main-title">🚀 Catalyst Screener</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Pre-market gap scanner · TradingView + yFinance + Gemini AI</div>', unsafe_allow_html=True)

# ── טען CSV אחרון מ-GitHub Actions אם קיים ──────────────────────────────────
RESULTS_CSV = "results/latest_scan.csv"

col1, col2 = st.columns([1, 3])
with col1:
    run_btn = st.button("▶  Run New Scan", type="primary")
with col2:
    if os.path.exists(RESULTS_CSV):
        mtime = os.path.getmtime(RESULTS_CSV)
        import datetime
        ts = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')
        st.markdown(f"<span style='font-size:12px;color:#64748b;font-family:JetBrains Mono,monospace'>📂 Last auto-scan: {ts}</span>", unsafe_allow_html=True)
        if st.button("📂 Load Last Auto-Scan"):
            df_csv = pd.read_csv(RESULTS_CSV)
            df_csv['AnalysisDetails'] = df_csv['AnalysisDetails'].apply(
                lambda x: json.loads(x) if isinstance(x, str) and x.startswith('{') else {}
            )
            st.session_state['scan_df'] = df_csv
            st.rerun()

if run_btn:
    with st.spinner("Fetching pre-market leaders from TradingView..."):
        df = get_tradingview_scan()
    if df.empty:
        st.warning("⚠️ No data returned. Market may be closed or API is unavailable.")
        st.stop()

    total = len(df)
    st.success(f"✓ Found {total} stocks. Enriching with fundamentals & AI analysis...")
    progress = st.progress(0)
    status = st.empty()
    floats, shorts, categories, grades, reasonings, details_list = [], [], [], [], [], []

    for i, (_, row) in enumerate(df.iterrows()):
        ticker = row['Ticker']
        status.markdown(
            f"<span style='font-family:JetBrains Mono,monospace;font-size:12px;color:#94a3b8'>Analyzing {ticker} ({i+1}/{total})...</span>",
            unsafe_allow_html=True)
        float_sh, short_int, news_text = get_fundamentals_and_news(ticker)
        floats.append(float_sh)
        shorts.append(short_int)
        sleep(3)
        category, grade, reasoning, details = analyze_catalyst_with_gemini(ticker, news_text)
        categories.append(category)
        grades.append(grade)
        reasonings.append(reasoning)
        details_list.append(details)
        progress.progress((i + 1) / total)

    df['Float'] = floats
    df['Short Interest'] = shorts
    df['Category'] = categories
    df['Grade'] = grades
    df['Reasoning'] = reasonings
    df['AnalysisDetails'] = details_list
    status.empty()
    progress.empty()

    # שמור ב-session_state
    st.session_state['scan_df'] = df

# רנדר מ-session_state (נשמר גם אחרי לחיצת CSV)
if 'scan_df' in st.session_state:
    df = st.session_state['scan_df']
    categories = df['Category'].tolist()
    grades     = df['Grade'].tolist()

    earnings_n = sum(1 for c in categories if c == 'Earnings')
    a_grade_n  = sum(1 for g in grades if g == 'A')
    avg_pm = df['Premkt %'].apply(pd.to_numeric, errors='coerce').mean()

    st.markdown(f"""
    <div class="stat-row">
      <div class="stat-box">Stocks scanned <span>{len(df)}</span></div>
      <div class="stat-box">Earnings plays <span>{earnings_n}</span></div>
      <div class="stat-box">Grade A catalysts <span>{a_grade_n}</span></div>
      <div class="stat-box">Avg premkt move <span>+{avg_pm:.1f}%</span></div>
    </div>""", unsafe_allow_html=True)

    # ── Table header ──────────────────────────────────────────────────────────
    st.markdown("""
    <table class="sc-table">
      <thead><tr>
        <th>Ticker</th><th>Premkt %</th><th>Premkt Vol</th><th>Ext RVol</th>
        <th>Daily %</th><th>Short Int.</th><th>Float</th><th>Industry</th>
        <th>Category</th><th>Grade</th><th>Reasoning</th><th>Analysis Details</th>
      </tr></thead>
    </table>""", unsafe_allow_html=True)

    # ── One row per stock ──────────────────────────────────────────────────────
    for i, (_, row) in enumerate(df.iterrows()):
        ticker  = row['Ticker']
        tv_url  = f"https://www.tradingview.com/chart/?symbol={ticker}"
        cat     = str(row.get('Category', 'Others'))
        grade   = str(row.get('Grade', 'C'))
        reasoning = str(row.get('Reasoning', ''))
        details = row.get('AnalysisDetails', {})
        if not isinstance(details, dict):
            try: details = json.loads(str(details))
            except: details = {}

        badge_cls = "b" + cat.replace('&','').replace('/','').replace(' ','').replace('-','').replace(',','').replace('_','')
        grade_cls = f"g{grade}" if grade in ['A','B','C','D'] else "gC"
        pm_cls, pm_s = pct_str(row['Premkt %'])
        dp_cls, dp_s = pct_str(row['Daily %'])
        si = row.get('Short Interest','N/A')
        si_s = f"{si:.2f}%" if isinstance(si,(int,float)) else "N/A"
        try: rvol_s = f"{float(row['Ext RVol']):.2f}x"
        except: rvol_s = "N/A"

        impact        = details.get('Impact','') if isinstance(details,dict) else ''
        explosiveness = details.get('Explosiveness','') if isinstance(details,dict) else ''
        data_quality  = details.get('DataQuality','') if isinstance(details,dict) else ''
        has_details   = any([impact, explosiveness, data_quality])

        row_html = f"""
        <table class="sc-table"><tbody><tr>
          <td><a href="{tv_url}" target="_blank" class="tk"><span class="tk-dot"></span><span class="tk-name">{ticker}</span></a></td>
          <td class="{pm_cls}">{pm_s}</td>
          <td class="mu">{fmt_num(row['Premkt Vol'])}</td>
          <td class="mu">{rvol_s}</td>
          <td class="{dp_cls}">{dp_s}</td>
          <td class="mu">{si_s}</td>
          <td class="mu">{fmt_num(row.get('Float',''))}</td>
          <td class="mu" style="font-size:11px">{str(row.get('Industry',''))[:20]}</td>
          <td><span class="bdg {badge_cls}">{cat}</span></td>
          <td><span class="gc {grade_cls}">{grade}</span></td>
          <td class="rsn">{reasoning}</td>
          <td class="mu" style="font-size:11px">{"▼ see below" if has_details else ""}</td>
        </tr></tbody></table>"""
        st.markdown(row_html, unsafe_allow_html=True)

        if has_details:
            with st.expander("📊 Analysis Details", expanded=False):
                if impact:
                    st.markdown("**• Impact**")
                    st.markdown(impact)
                if explosiveness:
                    st.markdown("**• Explosiveness**")
                    st.markdown(explosiveness)
                if data_quality:
                    st.markdown("**• Data Quality**")
                    st.markdown(data_quality)

    st.markdown("<br>", unsafe_allow_html=True)
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(label="📥 Download CSV", data=csv, file_name="catalyst_scan.csv", mime="text/csv")
