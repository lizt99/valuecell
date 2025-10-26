# Quick Start Guide - TradingView Polling Service

## 🚀 5-Minute Setup

### Step 1: Install Dependencies

```bash
cd python
pip install httpx apscheduler
```

Or if using uv:
```bash
uv pip install httpx apscheduler
```

### Step 2: Set Environment Variables

```bash
# Required credentials
export SVIX_API_TOKEN="sk_poll_yHiqZ0QyAqCWsR5BfIkrI7He3xUPbe8z.us"
export SVIX_CONSUMER_ID="MY_CONSUMER_ID"
```

Or create a `.env` file:
```bash
echo 'SVIX_API_TOKEN="sk_poll_yHiqZ0QyAqCWsR5BfIkrI7He3xUPbe8z.us"' > .env
echo 'SVIX_CONSUMER_ID="MY_CONSUMER_ID"' >> .env
```

### Step 3: Test with Mock Data

```bash
cd python
python -m valuecell.agents.tradingview_signal_agent.test_polling
# Choose option 1 (Test with mock data)
```

Expected output:
```
✅ Saved mock data with row_id=1
✅ Retrieved data:
   Symbol: BTCUSDT
   Timestamp: 2025-10-26 15:00:00+00:00
   Price: $67,500.50
   RSI: 65.5
```

### Step 4: Start Polling Service

```bash
./scripts/start_tradingview_polling.sh
```

Or directly:
```bash
cd python
python -m valuecell.agents.tradingview_signal_agent.polling_service
```

Expected output:
```
✅ Polling service started - running every 3 minutes at :00
```

### Step 5: Verify Data Collection

Wait 3 minutes, then check the database:

```bash
cd python
sqlite3 tradingview_indicators.db "SELECT symbol, timestamp FROM indicator_data ORDER BY timestamp DESC LIMIT 5;"
```

---

## ✅ Verification Checklist

- [ ] Dependencies installed (httpx, apscheduler)
- [ ] Environment variables set (SVIX_API_TOKEN, SVIX_CONSUMER_ID)
- [ ] Mock data test passed
- [ ] Polling service started without errors
- [ ] Data appearing in database every 3 minutes

---

## 🎯 Next Steps

1. **Run the Agent**: The TradingView Signal Agent will automatically use the polling data
2. **Monitor Logs**: Check `logs/` directory for service logs
3. **Customize**: Edit `constants.py` to change polling interval or symbols

---

## 🐛 Common Issues

### "No module named 'httpx'"
```bash
pip install httpx
```

### "No module named 'apscheduler'"
```bash
pip install apscheduler
```

### "Authentication failed"
- Check SVIX_API_TOKEN is correct
- Verify token hasn't expired
- Ensure no extra spaces in token

### "No data in database"
- Wait at least 3 minutes after starting
- Check service logs for errors
- Test with mock data first
- Verify API URL is correct

---

## 📞 Support

- Full documentation: [POLLING_SERVICE_SETUP.md](POLLING_SERVICE_SETUP.md)
- Troubleshooting: See "Troubleshooting" section in setup guide
- Test suite: Run `test_polling.py` with mock data

---

**Ready to go!** 🎉

The polling service will now:
- Fetch data every 3 minutes
- Store in `tradingview_indicators.db`
- Provide data to TradingView Signal Agent
- Run continuously in background

