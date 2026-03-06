# 🚀 Catalyst Screener

A pre-market gap scanner for US stocks, built with Streamlit.  
Identifies the **catalyst** behind each gap using AI (Gemini Flash).

---

## What it does

1. **Scans TradingView** for top pre-market movers (>50K volume)
2. **Enriches** each stock with float & short interest via yFinance
3. **Fetches news** via yFinance and classifies the catalyst with Gemini AI
4. **Displays** a dark-themed table with category badges and reasoning

### Catalyst categories
`EARNINGS` · `MACRO` · `UPGRADE` · `FDA` · `M&A` · `CONTRACT` · `GUIDANCE` · `OTHERS` · `UNKNOWN`

---

## Setup

### 1. Clone
```bash
git clone https://github.com/YOUR_USERNAME/catalyst-screener.git
cd catalyst-screener
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure API key
Create a `.env` file:
```
GEMINI_API_KEY=your_gemini_api_key_here
```
Get a free Gemini API key at [aistudio.google.com](https://aistudio.google.com)

### 4. Run
```bash
streamlit run reasoning_scanner.py
```

---

## Dependencies

| Package | Purpose |
|---|---|
| `streamlit` | UI framework |
| `tradingview-screener` | TradingView API wrapper |
| `yfinance` | Fundamentals + news |
| `google-generativeai` | Gemini AI catalyst analysis |
| `python-dotenv` | Environment variables |

---

## Notes

- Best run **pre-market (4:00–9:30 AM ET)** when pre-market data is live
- Scan takes ~60–90 seconds for 15 stocks
- TradingView data is delayed 15 min without authentication
