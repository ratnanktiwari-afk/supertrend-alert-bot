# Supertrend Alert Bot — GitHub Actions Setup (Free, 24x7-ish)

Yeh bot har 15 minute par GitHub Actions ke through chalta hai, naye candles
check karta hai, aur jab BUY/SELL ENTRY, TARGET HIT, TRAIL SL HIT, ya EXIT ka
signal aata hai to Telegram pe alert bhej deta hai.

---

## Step 1: GitHub par naya repository bana

1. https://github.com par jaa, login kar (account nahi hai to free bana le)
2. **New repository** par click kar
3. Naam de jaise `supertrend-alert-bot`
4. **Private** rakh (apna trading logic public nahi karna better hai)
5. Create kar de

## Step 2: Saari files upload kar

Is folder ki saari files (`main.py`, `strategy_engine.py`, `data_fetchers.py`,
`telegram_notifier.py`, `config.py`, `requirements.txt`, `state.json`, aur
`.github/workflows/bot.yml`) apne naye repo me upload kar:

- Repo page par **"uploading an existing file"** link milega (ya "Add file" → "Upload files")
- Saari files drag-drop kar de (folder structure maintain rakhna — `.github/workflows/bot.yml` apni jagah hi rehna chahiye)
- Commit kar de

## Step 3: Telegram credentials ko GitHub Secrets me daal (IMPORTANT - security)

Apna bot token aur chat_id seedhe code me kabhi mat likh — Secrets me daal:

1. Apne repo me jaa → **Settings** tab
2. Left side me **Secrets and variables** → **Actions**
3. **New repository secret** par click kar
4. Naam: `TELEGRAM_TOKEN`, Value: tera bot token (jo BotFather se mila tha)
5. Dobara **New repository secret**: Naam `TELEGRAM_CHAT_ID`, Value: tera chat_id

## Step 4: Symbols set kar

`config.py` file me `SYMBOLS` list edit kar apne symbols daalne ke liye:

```python
SYMBOLS = [
    {"type": "crypto", "symbol": "B-BTC_USDT", "display": "BTC/USDT"},
    {"type": "stock",  "symbol": "^NSEI",      "display": "NIFTY 50"},
]
```

- Crypto (CoinDCX) symbols `B-BTC_USDT` jaise format me hote hain
- Stocks (Yahoo Finance) symbols `RELIANCE.NS` jaise format me, ya index ke liye `^NSEI`

## Step 5: Manually test kar (pehli baar)

1. Repo me **Actions** tab par jaa
2. Left side "Supertrend Alert Bot" workflow select kar
3. **"Run workflow"** button dabaa (manual trigger)
4. 1-2 minute me run complete ho jaayega — green tick aana chahiye
5. Apne Telegram pe check kar — "Bot started" wala message aana chahiye (agar koi signal active hua to wo bhi)

Agar red X (fail) aaye, to us run ke logs khol ke dekh kya error aaya — mujhe bata dena, fix kar denge.

## Step 6: Automatic schedule

Ab kuch nahi karna — workflow har 15 minute pe khud chalega (`cron: "*/15 * * * *"`)
aur jab bhi koi signal/entry/exit aayega, Telegram pe message aa jaayega.

**Note:** GitHub Actions free tier ka schedule kabhi 5-10 min tak delay ho sakta hai
high-load times pe — yeh guaranteed exact-time nahi hai, lekin generally reliable hai.

## Naye symbols baad me add karne ke liye

`config.py` me `SYMBOLS` list me naya entry add kar, commit/push kar de —
agle scheduled run se naya symbol bhi track hona shuru ho jaayega.

## Troubleshooting

- **Koi Telegram message nahi aa raha:** Secrets sahi se set hue ya nahi check kar (naam exactly `TELEGRAM_TOKEN` aur `TELEGRAM_CHAT_ID` hona chahiye)
- **Workflow fail ho raha hai:** Actions tab me failed run khol, "Run bot" step ka log dekh, error message wahi bata dega
- **state.json commit nahi ho raha:** Settings → Actions → General me "Workflow permissions" check kar, "Read and write permissions" selected hona chahiye
