# Arbitrage Trading Team

A decentralized, multi-agent trading system designed to detect and execute price arbitrage opportunities across cryptocurrency, forex, and stock markets.

## Architecture Overview

```
┌────────────────────────────────────────────────────────────────────┐
│                    Arbitrage Trading Team                          │
├────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  ┌──────────┐  │
│  │  Scanner    │->│  Validator  │->│ Risk Manager │->│ Executor │  │
│  │  Agent      │  │  Agent      │  │ Agent        │  │ Agent    │  │
│  └─────────────┘  └─────────────┘  └──────────────┘  └─────┬────┘  │
│                                                            │       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                      Message Queue (Redis)                   │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Reconciler Agent                          │  │
│  │              (Settlement Verification & P&L)                 │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │  Exchange 1  │  │  Exchange 2  │  │  Exchange N  │              │
│  │ (Binance)    │  │ (Coinbase)   │  │  (Kraken)    │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
│                                                                    │
│  ┌──────────────┐  ┌──────────────┐                                │
│  │   PostgreSQL │  │   Redis      │                                │
│  │  (Timescale) │  │   (Pub/Sub)  │                                │
│  └──────────────┘  └──────────────┘                                │
└────────────────────────────────────────────────────────────────────┘
```

## Agents

### 1. Scanner Agent
- **Purpose**: Real-time price monitoring across exchanges
- **Responsibilities**:
  - Connect to multiple exchanges via WebSocket and REST APIs
  - Parse real-time price feeds and order books
  - Detect price discrepancies
  - Calculate opportunity metrics
  - Queue opportunities for validation
- **Key Features**:
  - Multi-exchange support (Binance, Coinbase, Kraken)
  - WebSocket streaming for low-latency updates
  - Configurable spread thresholds
  - Liquidity checking

### 2. Validator Agent
- **Purpose**: Validate arbitrage opportunities
- **Responsibilities**:
  - Check liquidity availability
  - Calculate accurate net profit after fees
  - Verify settlement feasibility
  - Detect false positives
- **Key Features**:
  - Exchange-specific fee calculations
  - Withdrawal fee estimation
  - Settlement time verification
  - Minimum volume checks

### 3. Risk Manager Agent
- **Purpose**: Assess and enforce risk limits
- **Responsibilities**:
  - Monitor total exposure
  - Enforce position limits
  - Calculate risk metrics
  - Approve or reject opportunities
  - Implement emergency stop procedures
- **Key Features**:
  - Dynamic position sizing
  - Daily loss limits
  - Exposure ratio monitoring
  - Emergency stop levels (1, 2, 3)
  - Failure rate tracking

### 4. Executor Agent
- **Purpose**: Place and monitor orders
- **Responsibilities**:
  - Place buy and sell orders
  - Monitor order status
  - Handle partial fills
  - Cancel failed orders
  - Execute settlement
- **Key Features**:
  - Retry logic with exponential backoff
  - Timeout handling
  - Order lifecycle management
  - Multi-exchange order placement

### 5. Reconciler Agent
- **Purpose**: Verify settlements and calculate P&L
- **Responsibilities**:
  - Verify transaction settlements
  - Reconcile account balances
  - Calculate actual P&L
  - Generate reports
  - Maintain audit trail
- **Key Features**:
  - Periodic reconciliation
  - Settlement verification
  - P&L tracking
  - Trade statistics

## Technology Stack

- **Language**: Python 3.11+
- **Async Framework**: asyncio
- **Message Queue**: Redis (Pub/Sub)
- **Database**: PostgreSQL with TimescaleDB
- **HTTP Client**: aiohttp
- **Logging**: structlog
- **Type Safety**: Type hints

## Installation

### Prerequisites
- Python 3.11+
- Docker and Docker Compose (for production)
- Redis (can be managed via Docker)
- PostgreSQL/TimescaleDB (can be managed via Docker)

### Quick Start with Docker

```bash
cd trading_team

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f scanner-agent

# Stop services
docker-compose down
```

### Manual Installation

```bash
# Clone the repository
git clone <repository-url>
cd trading_team

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create configuration
mkdir config
cp config_template.yaml config/exchanges.yaml

# Run the trading team
python main.py
```

## Configuration

### Environment Variables

```bash
# Trading capital (in USD)
export TRADING_CAPITAL=100000

# Redis connection
export REDIS_URL=redis://localhost:6379

# PostgreSQL connection
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=trading_db
export POSTGRES_USER=trading
export POSTGRES_PASSWORD=trading_password

# Exchange API keys (set as needed)
export BINANCE_API_KEY=your_key
export BINANCE_API_SECRET=your_secret
export COINBASE_API_KEY=your_key
export COINBASE_API_SECRET=your_secret
export COINBASE_PASSPHRASE=your_passphrase
```

### exchanges.yaml

```yaml
exchanges:
  - name: binance
    api_key: ${BINANCE_API_KEY}
    api_secret: ${BINANCE_API_SECRET}
    symbols:
      - BTC/USDT
      - ETH/USDT
      - SOL/USDT
    enabled: true
  
  - name: coinbase
    api_key: ${COINBASE_API_KEY}
    api_secret: ${COINBASE_API_SECRET}
    passphrase: ${COINBASE_PASSPHRASE}
    symbols:
      - BTC-USD
      - ETH-USD
      - SOL-USD
    enabled: true
  
  - name: kraken
    api_key: ${KRAKEN_API_KEY}
    api_secret: ${KRAKEN_API_SECRET}
    symbols:
      - XBT/USD
      - ETH/USD
      - SOL/USD
    enabled: false
```

## Risk Management

### Position Limits

| Metric | Default | Description |
|--------|---------|-------------|
| Max Total Exposure | 50% | Maximum % of capital at risk |
| Max Single Position | 10% | Maximum % of capital per trade |
| Max Daily Loss | 2% | Maximum daily loss before stop |
| Max Concurrent Positions | 10 | Maximum open trades simultaneously |

### Emergency Stop Levels

- **Level 1**: Daily loss > 1% - Reduce trading volume by 50%
- **Level 2**: Daily loss > 2% - Stop all trading, close positions
- **Level 3**: Daily loss > 5% - Emergency shutdown, notify stakeholders

## Arbitrage Strategies Supported

### 1. Exchange Arbitrage
- Buy asset on Exchange A
- Transfer to Exchange B
- Sell on Exchange B
- Profit from price difference

### 2. Triangular Arbitrage
- Exchange A: Buy B with A
- Exchange B: Buy C with B
- Exchange C: Buy A with C
- Profit from exchange rate inefficiencies

### 3. Funding Rate Arbitrage (Crypto)
- Long spot position
- Short perpetual futures
- Profit from funding rate differential

## Monitoring

### Logs

```bash
# View all logs
docker-compose logs -f

# View specific agent
docker-compose logs -f scanner-agent

# View logs for errors only
docker-compose logs --tail=100 scanner-agent | grep ERROR
```

### Metrics

Key metrics to monitor:
- Number of opportunities detected
- Number of opportunities validated
- Risk assessment approval rate
- Order execution success rate
- Settlement success rate
- Daily P&L
- Win rate

## Development

### Adding New Agents

1. Create agent directory: `mkdir agents/new_agent`
2. Create agent module: `new_agent_agent.py`
3. Implement required interfaces:
   - `async def start(self)`
   - `async def stop(self)`
4. Register in main.py
5. Add to docker-compose.yml

### Testing

```bash
# Run unit tests
pytest tests/

# Run integration tests
docker-compose up -d
python tests/integration_test.py
docker-compose down
```

## Security Considerations

1. **API Key Management**: Never commit API keys to version control
2. **Environment Variables**: Use `.env` file for sensitive data
3. **Rate Limiting**: Implement exchange rate limit compliance
4. **Authentication**: Use API key rotation
5. **Monitoring**: Monitor for unusual activity
6. **Firewall**: Restrict network access to trading agents

## Troubleshooting

### Common Issues

1. **Redis Connection Failed**
   ```
   Error: Redis connection refused
   ```
   - Ensure Redis is running: `docker-compose ps`
   - Check Redis port: `docker-compose logs redis`

2. **PostgreSQL Connection Failed**
   ```
   Error: Could not connect to database
   ```
   - Wait for database initialization
   - Check database credentials
   - Verify network connectivity

3. **No Opportunities Detected**
   - Check spread thresholds in config
   - Verify exchange connections
   - Review logs for connection errors

4. **Order Execution Failed**
   - Check API key permissions
   - Verify account balance
   - Review exchange rate limits

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write tests
5. Submit a pull request

## License

MIT License - See LICENSE file for details.

## Disclaimer

⚠️ **WARNING**: This software is for educational and research purposes only.
Trading involves significant risk of loss. Past performance does not guarantee
future results. Do not use this software with funds you cannot afford to lose.
Consult with a financial advisor before making trading decisions.

## Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Join the community Discord
- Email: support@example.com

# PostgreSQL connection
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=trading_db
export POSTGRES_USER=trading
export POSTGRES_PASSWORD=trading_password

# Exchange API keys (set as needed)
export BINANCE_API_KEY=your_key
export BINANCE_API_SECRET=your_secret
export COINBASE_API_KEY=your_key
export COINBASE_API_SECRET=your_secret
export COINBASE_PASSPHRASE=your_passphrase
```

### exchanges.yaml

```yaml
exchanges:
  - name: binance
    api_key: ${BINANCE_API_KEY}
    api_secret: ${BINANCE_API_SECRET}
    symbols:
      - BTC/USDT
      - ETH/USDT
      - SOL/USDT
    enabled: true
  
  - name: coinbase
    api_key: ${COINBASE_API_KEY}
    api_secret: ${COINBASE_API_SECRET}
    passphrase: ${COINBASE_PASSPHRASE}
    symbols:
      - BTC-USD
      - ETH-USD
      - SOL-USD
    enabled: true
  
  - name: kraken
    api_key: ${KRAKEN_API_KEY}
    api_secret: ${KRAKEN_API_SECRET}
    symbols:
      - XBT/USD
      - ETH/USD
      - SOL/USD
    enabled: false
```

## Risk Management

### Position Limits

| Metric | Default | Description |
|--------|---------|-------------|
| Max Total Exposure | 50% | Maximum % of capital at risk |
| Max Single Position | 10% | Maximum % of capital per trade |
| Max Daily Loss | 2% | Maximum daily loss before stop |
| Max Concurrent Positions | 10 | Maximum open trades simultaneously |

### Emergency Stop Levels

- **Level 1**: Daily loss > 1% - Reduce trading volume by 50%
- **Level 2**: Daily loss > 2% - Stop all trading, close positions
- **Level 3**: Daily loss > 5% - Emergency shutdown, notify stakeholders

## Arbitrage Strategies Supported

### 1. Exchange Arbitrage
- Buy asset on Exchange A
- Transfer to Exchange B
- Sell on Exchange B
- Profit from price difference

### 2. Triangular Arbitrage
- Exchange A: Buy B with A
- Exchange B: Buy C with B
- Exchange C: Buy A with C
- Profit from exchange rate inefficiencies

### 3. Funding Rate Arbitrage (Crypto)
- Long spot position
- Short perpetual futures
- Profit from funding rate differential

## Monitoring

### Logs

```bash
# View all logs
docker-compose logs -f

# View specific agent
docker-compose logs -f scanner-agent

# View logs for errors only
docker-compose logs --tail=100 scanner-agent | grep ERROR
```

### Metrics

Key metrics to monitor:
- Number of opportunities detected
- Number of opportunities validated
- Risk assessment approval rate
- Order execution success rate
- Settlement success rate
- Daily P&L
- Win rate

## Development

### Adding New Agents

1. Create agent directory: `mkdir agents/new_agent`
2. Create agent module: `new_agent_agent.py`
3. Implement required interfaces:
   - `async def start(self)`
   - `async def stop(self)`
4. Register in main.py
5. Add to docker-compose.yml

### Testing

```bash
# Run unit tests
pytest tests/

# Run integration tests
docker-compose up -d
python tests/integration_test.py
docker-compose down
```

## Security Considerations

1. **API Key Management**: Never commit API keys to version control
2. **Environment Variables**: Use `.env` file for sensitive data
3. **Rate Limiting**: Implement exchange rate limit compliance
4. **Authentication**: Use API key rotation
5. **Monitoring**: Monitor for unusual activity
6. **Firewall**: Restrict network access to trading agents

## Troubleshooting

### Common Issues

1. **Redis Connection Failed**
   ```
   Error: Redis connection refused
   ```
   - Ensure Redis is running: `docker-compose ps`
   - Check Redis port: `docker-compose logs redis`

2. **PostgreSQL Connection Failed**
   ```
   Error: Could not connect to database
   ```
   - Wait for database initialization
   - Check database credentials
   - Verify network connectivity

3. **No Opportunities Detected**
   - Check spread thresholds in config
   - Verify exchange connections
   - Review logs for connection errors

4. **Order Execution Failed**
   - Check API key permissions
   - Verify account balance
   - Review exchange rate limits

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write tests
5. Submit a pull request

## License

MIT License - See LICENSE file for details.

## Disclaimer

⚠️ **WARNING**: This software is for educational and research purposes only.
Trading involves significant risk of loss. Past performance does not guarantee
future results. Do not use this software with funds you cannot afford to lose.
Consult with a financial advisor before making trading decisions.

## Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Join the community Discord
- Email: support@example.com
