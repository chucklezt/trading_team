# Quick Start Guide - Arbitrage Trading Team

## 5-Minute Setup

### Step 1: Install Dependencies (1 min)

```bash
cd ~/trading_team
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2: Create Configuration (1 min)

```bash
mkdir config
cat > config/exchanges.yaml << 'EOF'
exchanges:
  - name: binance
    api_key: YOUR_BINANCE_API_KEY
    api_secret: YOUR_BINANCE_API_SECRET
    symbols:
      - BTC/USDT
      - ETH/USDT
    enabled: true
EOF
```

### Step 3: Get API Keys (1 min)

1. Go to [Binance](https://www.binance.com/)
2. Sign up / Log in
3. API Management → Create API Key
4. Copy key and secret to config/exchanges.yaml

### Step 4: Start Infrastructure (1 min)

```bash
docker-compose up -d redis postgres
```

### Step 5: Test (1 min)

```bash
python3 test_simple.py
```

Expected output:
```
✓ All structure tests passed!
```

## Full Deployment (10 minutes)

### Step 1: Install All Dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install redis psycopg2-binary
```

### Step 2: Configure Environment

```bash
cat > .env << 'EOF'
TRADING_CAPITAL=100000
REDIS_URL=redis://localhost:6379
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=trading_db
POSTGRES_USER=trading
POSTGRES_PASSWORD=trading_password
BINANCE_API_KEY=your_key_here
BINANCE_API_SECRET=your_secret_here
EOF
```

### Step 3: Create Database Schema

```bash
docker-compose exec postgres psql -U trading -d trading_db << 'EOF'
-- Create tables will happen automatically
-- via SQLAlchemy models on first run
EOF
```

### Step 4: Start All Services

```bash
docker-compose up -d
```

### Step 5: Run Full Test

```bash
python3 main.py
```

## Monitoring

### View Logs

```bash
# All logs
docker-compose logs -f

# Scanner agent only
docker-compose logs -f scanner-agent

# Watch for errors
docker-compose logs --tail=100 | grep -i error
```

### Check Service Status

```bash
docker-compose ps
```

## Troubleshooting

### Redis Not Running

```bash
docker-compose logs redis
# Should show: Redis server started
```

### PostgreSQL Not Running

```bash
docker-compose logs postgres
# Wait 30 seconds for initialization
```

### No Opportunities Detected

1. Check spread threshold (default 0.1%)
2. Verify exchange API keys
3. Check logs for connection errors
4. Try manual API call to test connection

### Memory Issues

```bash
# Check container memory usage
docker stats

# Increase memory limit in docker-compose.yml
# memory: 1G
```

## Next Steps

1. **Add More Exchanges**: Edit `config/exchanges.yaml`
2. **Adjust Risk Limits**: Edit `main.py` config
3. **Enable Paper Trading**: Use testnet APIs first
4. **Set Up Monitoring**: Configure alerts
5. **Review Research**: Read `Arbitrage_Opportunities_Research.md`

## Common Issues

### "ModuleNotFoundError: No module named 'redis'"

```bash
pip install redis
```

### "Connection refused to Redis"

```bash
# Check if Redis is running
docker-compose ps redis

# Restart if needed
docker-compose restart redis
```

### "Database connection failed"

```bash
# Wait for database to be ready
sleep 30
docker-compose restart postgres
```

### "Order execution failed"

1. Check API key permissions
2. Verify account has sufficient balance
3. Check exchange rate limits
4. Review error logs

## Support

- Read `README.md` for detailed documentation
- Check `IMPLEMENTATION_SUMMARY.md` for architecture
- Review agent code in `agents/` directory
- Test with `test_simple.py`

## Safety First ⚠️

1. **Start Small**: Use minimal capital initially
2. **Use Testnets**: Test with Binance Testnet first
3. **Monitor Closely**: Watch logs for first 24 hours
4. **Set Limits**: Configure daily loss limits
5. **Have Exit Plan**: Know how to stop trading

## Emergency Stop

To stop trading immediately:

```bash
# Via API
curl -X POST http://localhost:5000/emergency-stop

# Or just stop the containers
docker-compose stop
```

---

Ready to trade! 🚀
