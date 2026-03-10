# 🚀 Catalyst Screener

Pre-market gap scanner powered by TradingView, yFinance, and Gemini AI.

## What it does

Scans the top pre-market movers on NYSE and NASDAQ every morning, enriches each stock with float and short interest data, and uses Gemini AI to classify the catalyst and assign a quality grade.

## Filters

- Exchange: NYSE and NASDAQ only (no OTC)
- Pre-market volume > 100,000
- Market cap > $300M
- Stock type only (no ETFs, funds, or DRs)

## Output columns

| Column | Description |
|---|---|
| Ticker | Stock symbol, links to TradingView chart |
| Premkt % | Pre-market price change |
| Premkt Vol | Pre-market volume |
| Ext RVol | Relative volume vs 10-day average |
| Daily % | Regular session change |
| Short Int. | Short interest as % of float |
| Float | Float shares |
| Industry | Sector/industry |
| Category | AI-classified catalyst type |
| Grade | Catalyst quality (A–D) |
| Reasoning | AI summary of why the stock is moving |
| Analysis Details | Deep dive: Impact, Explosiveness, Data Quality |

## Catalyst categories

- Earnings
- Upgrade / Downgrade
- Macro
- Themes & Narratives
- New Contracts & Partnerships
- FDA
- M&A
- Others

## Grades

- **A** — Strong, clear fundamental catalyst
- **B** — Solid catalyst with some uncertainty
- **C** — Weak or indirect catalyst
- **D** — No clear catalyst, speculative

## Setup

### Local

1. Clone the repo
2. Create a virtual environment and install dependencies:
```
pip install -r requirements.txt
```
3. Open `reasoning_scanner.py` and replace `ENTER_YOUR_KEY_HERE` with your Gemini API key
4. Run:
```
streamlit run reasoning_scanner.py
```

### Streamlit Cloud

1. Fork or push this repo to your GitHub account
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect the repo
3. In **Settings → Secrets**, add:
```toml
GEMINI_API_KEY = "your-key-here"
```
4. Deploy

### GitHub Actions (auto-scan)

The workflow in `.github/workflows/scan.yml` runs automatically on weekdays at 08:00, 10:00, and 12:00 UTC (11:00, 13:00, 15:00 Israel time in summer).

To enable it, add your Gemini API key as a repository secret:
GitHub repo → **Settings → Secrets and variables → Actions → New repository secret**
- Name: `GEMINI_API_KEY`
- Value: your key

Results are saved automatically to `results/latest_scan.csv` and can be loaded directly from the app.

## Requirements

```
streamlit>=1.35.0
pandas>=2.0.0
yfinance>=0.2.40
google-genai>=1.0.0
tradingview-screener>=3.1.0
```

## Cost

Gemini 2.5 Flash pricing is extremely low. Scanning 30 stocks costs roughly $0.002 per run — under $0.40/month even at 10 scans per trading day.
