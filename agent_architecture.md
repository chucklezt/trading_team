# Arbitrage Trading Team - Agent Architecture
## Multi-Agent System Design

---

## 1. SYSTEM OVERVIEW

### 1.1 Architecture Principles

**Decentralized Design:**
- Each agent operates independently
- Agents communicate via message queue
- No single point of failure
- Scalable agent deployment

**Resilience:**
- Agents restart automatically on failure
- State persistence across restarts
- Circuit breakers on communication
- Graceful degradation

**Observability:**
- Comprehensive logging
- Metrics collection
- Distributed tracing
- Alerting system

### 1.2 Communication Protocol

```
┌─────────────────────────────────────────────────────────────┐
│                    Message Queue (Redis/Kafka)              │
├─────────────────────────────────────────────────────────────┤
│  Scanner  │  Validator  │  RiskMgr  │  Executor  │  Reconciler│
│  (Agent)  │  (Agent)    │  (Agent)   │  (Agent)   │  (Agent)   │
└─────────────────────────────────────────────────────────────┘
```

**Message Types:**
```python
{
    "type": "opportunity",
    "source": "scanner",
    "data": {...},
    "timestamp": "2024-01-01T10:00:00Z",
    "correlation_id": "uuid"
}
```

---

## 2. AGENT SPECIFICATIONS

### 2.1 Scanner Agent

**Responsibilities:**
- Monitor all configured markets/exchanges
- Detect price discrepancies
- Filter noise and false signals
- Queue opportunities for validation

**Input:**
- Exchange WebSocket streams
- REST API price feeds
- Historical data for analysis

**Output:**
- Opportunity messages with:
  - Asset pair
  - Source exchange
  - Target exchange
  - Price difference
  - Timestamp
  - Confidence score

**Configuration:**
```yaml
scanner:
  exchanges:
    - name: binance
      symbols: ["BTC/USDT", "ETH/USDT"]
      interval: 100ms
    - name: coinbase
      symbols: ["BTC-USD", "ETH-USD"]
      interval: 100ms
  
  thresholds:
    min_spread: 0.001  # 0.1%
    max_spread: 0.05   # 5%
  
  rate_limits:
    binance: 1200/min
    coinbase: 1000/min
```

**Implementation:**
```python
class ScannerAgent(Agent):
    def __init__(self):
        self.exchanges = self.load_exchanges()
        self.message_queue = RedisQueue("scanner")
        
    async def run(self):
        for exchange in self.exchanges:
            await self.monitor_exchange(exchange)
    
    async def monitor_exchange(self, exchange):
        async with exchange.websocket() as ws:
            async for message in ws:
                prices = self.parse_prices(message)
                opportunity = self.detect_opportunity(prices)
                if opportunity and opportunity.confidence > 0.7:
                    await self.message_queue.publish(opportunity)
```

### 2.2 Validator Agent

**Responsibilities:**
- Confirm opportunity authenticity
- Check liquidity availability
- Calculate net profit after fees
- Verify settlement times
- Eliminate false positives

**Input:**
- Opportunity message from Scanner
- Real-time order book data
- Fee schedules

**Output:**
- Validated opportunity or rejection
- Net profit calculation
- Estimated execution time

**Validation Checks:**
```python
class ValidatorAgent(Agent):
    def validate_opportunity(self, opportunity):
        checks = {
            "spread_valid": self.verify_spread(opportunity),
            "liquidity_ok": self.check_liquidity(opportunity),
            "fees_covered": self.calculate_net_profit(opportunity),
            "settlement_safe": self.verify_settlement(opportunity),
            "account_balanced": self.check_account_balance()
        }
        
        return {
            "valid": all(checks.values()),
            "net_profit": self.calculate_net_profit(opportunity) if all(checks.values()) else 0,
            "details": checks
        }
    
    def calculate_net_profit(self, opportunity):
        gross_spread = opportunity.price_diff
        fees = (
            opportunity.amount * opportunity.buy_price * self.buy_fee +
            opportunity.amount * opportunity.sell_price * self.sell_fee +
            self.withdrawal_fee
        )
        return gross_spread - fees
```

**Configuration:**
```yaml
validator:
  liquidity_checks:
    min_buy_volume: 0.1  # BTC
    min_sell_volume: 0.1  # BTC
  
  fee_schedules:
    binance: {"maker": 0.001, "taker": 0.001}
    coinbase: {"maker": 0.005, "taker": 0.005}
  
  settlement_window: 24  # hours
```

### 2.3 Risk Manager Agent

**Responsibilities:**
- Monitor total exposure
- Enforce position limits
- Calculate risk metrics
- Approve/reject positions
- Emergency shutdown

**Input:**
- Opportunity details
- Current position state
- Market volatility data

**Output:**
- Risk assessment score
- Position size recommendation
- Approval/rejection decision

**Risk Metrics:**
```python
class RiskManagerAgent(Agent):
    def assess_risk(self, opportunity, current_positions):
        exposure = self.calculate_exposure(opportunity, current_positions)
        volatility = self.get_market_volatility(opportunity.asset)
        correlation = self.check_correlation(current_positions)
        
        risk_score = (
            exposure * 0.4 +
            volatility * 0.3 +
            (1 - correlation) * 0.3
        )
        
        return {
            "risk_score": risk_score,
            "max_position_size": self.calculate_max_position(risk_score),
            "approved": risk_score < self.threshold
        }
    
    def calculate_exposure(self, opportunity, positions):
        total_value = sum(p.size * p.price for p in positions)
        return total_value + opportunity.profit_potential
    
    def calculate_max_position(self, risk_score):
        if risk_score < 0.3:
            return 0.1  # 10% of capital
        elif risk_score < 0.6:
            return 0.05  # 5% of capital
        else:
            return 0.01  # 1% of capital
```

**Risk Rules:**
```yaml
risk_manager:
  max_total_exposure: 0.5  # 50% of capital
  max_single_position: 0.1  # 10% of capital
  max_daily_loss: 0.02  # 2% daily loss limit
  max_concurrent_positions: 10
  
  emergency_triggers:
    - event: "daily_loss_exceeded"
      action: "stop_all_trading"
    - event: "system_error_count"
      threshold: 10
      action: "reduce_positions_by_50%"
```

### 2.4 Executor Agent

**Responsibilities:**
- Place buy and sell orders
- Monitor order status
- Handle partial fills
- Cancel failed orders
- Execute settlement

**Input:**
- Validated opportunity from Validator
- Risk approval from Risk Manager
- Order management system state

**Output:**
- Order confirmation
- Fill reports
- Settlement status

**Execution Strategy:**
```python
class ExecutorAgent(Agent):
    def execute_opportunity(self, opportunity, risk_approval):
        if not risk_approval.approved:
            return {"status": "rejected", "reason": "risk"}
        
        # Place orders with slight price advantage
        buy_order = self.create_order(
            exchange=opportunity.buy_exchange,
            symbol=opportunity.symbol,
            side="buy",
            quantity=opportunity.quantity,
            price=opportunity.buy_price,
            order_type="limit",
            time_in_force="GTC"
        )
        
        sell_order = self.create_order(
            exchange=opportunity.sell_exchange,
            symbol=opportunity.symbol,
            side="sell",
            quantity=opportunity.quantity,
            price=opportunity.sell_price,
            order_type="limit",
            time_in_force="GTC"
        )
        
        # Monitor and update status
        return await self.monitor_orders([buy_order, sell_order])
    
    async def monitor_orders(self, orders):
        for order in orders:
            while order.status not in ["filled", "cancelled", "rejected"]:
                await self.wait_for_update(order)
                await asyncio.sleep(1)
        
        return {
            "all_filled": all(o.status == "filled" for o in orders),
            "orders": orders
        }
```

**Order Management:**
```yaml
executor:
  order_types:
    - limit
    - market
    - stop_limit
  
  time_in_force:
    - GTC  # Good Till Cancelled
    - IOC  # Immediate Or Cancel
    - FOK  # Fill Or Kill
  
  retry_policy:
    max_attempts: 3
    retry_delay: 5  # seconds
    exponential_backoff: true
  
  cancellation:
    timeout: 60  # seconds
    auto_cancel: true
```

### 2.5 Reconciler Agent

**Responsibilities:**
- Verify transaction settlement
- Reconcile accounts across exchanges
- Calculate actual P&L
- Generate reports
- Audit trail maintenance

**Input:**
- Order execution confirmations
- Account balances
- Transaction history

**Output:**
- Settlement confirmation
- P&L calculation
- Reconciliation report

**Reconciliation Logic:**
```python
class ReconcilerAgent(Agent):
    def reconcile_position(self, opportunity, execution_data):
        expected = {
            "buy_exchange": {
                "balance_before": self.get_balance(opportunity.buy_exchange),
                "buy_amount": opportunity.quantity,
                "buy_price": opportunity.buy_price
            },
            "sell_exchange": {
                "balance_before": self.get_balance(opportunity.sell_exchange),
                "sell_amount": opportunity.quantity,
                "sell_price": opportunity.sell_price
            }
        }
        
        actual = self.fetch_actual_balances()
        
        return {
            "reconciled": self.compare(expected, actual),
            "pnl": self.calculate_pnl(execution_data),
            "discrepancies": self.find_discrepancies(expected, actual)
        }
    
    def calculate_pnl(self, execution_data):
        gross = (
            execution_data.sell_amount * execution_data.sell_price -
            execution_data.buy_amount * execution_data.buy_price
        )
        fees = execution_data.total_fees
        return gross - fees
```

**Reporting:**
```yaml
reconciler:
  report_frequency: "daily"
  report_formats:
    - json
    - csv
    - pdf
  
  audit_trail:
    enabled: true
    retention_days: 365
    immutability: true
  
  alerts:
    - condition: "reconciliation_failed"
      severity: "critical"
    - condition: "pnl_deviation > 10%"
      severity: "warning"
```

---

## 3. INFRASTRUCTURE LAYER

### 3.1 Message Queue Design

**Redis Pub/Sub:**
```python
# Publisher (Scanner, Validator)
async def publish_opportunity(opportunity):
    await redis.publish(
        "trading_opportunities",
        json.dumps(opportunity.to_dict())
    )

# Subscriber (Risk Manager, Executor)
async def subscribe_opportunities():
    pubsub = await redis.pubsub()
    await pubsub.subscribe("trading_opportunities")
    async for message in pubsub.listen():
        if message["type"] == "message":
            await handle_opportunity(json.loads(message["data"]))
```

**Message Schema:**
```json
{
    "correlation_id": "uuid-v4",
    "timestamp": "2024-01-01T10:00:00.000Z",
    "source_agent": "scanner",
    "opportunity": {
        "asset": "BTC",
        "buy_exchange": "binance",
        "buy_price": 64500.00,
        "sell_exchange": "coinbase",
        "sell_price": 64800.00,
        "quantity": 0.1,
        "net_profit": 25.00,
        "confidence": 0.95
    }
}
```

### 3.2 State Management

**Redis State Store:**
```python
# Shared state keys
STATE_KEYS = {
    "positions": "trading:positions",
    "balances": "trading:balances",
    "orders": "trading:orders",
    "opportunity_history": "trading:history",
    "risk_limits": "trading:risk:limits"
}

# Position tracking
async def update_position(position_id, update):
    await redis.hincrby(
        STATE_KEYS["positions"],
        position_id,
        json.dumps(update)
    )
```

### 3.3 Database Schema

**PostgreSQL + TimescaleDB:**
```sql
-- Opportunities table
CREATE TABLE opportunities (
    id UUID PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    source_agent TEXT NOT NULL,
    asset TEXT NOT NULL,
    buy_exchange TEXT NOT NULL,
    buy_price DECIMAL(18,8) NOT NULL,
    sell_exchange TEXT NOT NULL,
    sell_price DECIMAL(18,8) NOT NULL,
    quantity DECIMAL(18,8) NOT NULL,
    net_profit DECIMAL(18,2),
    confidence DECIMAL(5,4),
    status TEXT DEFAULT 'pending',
    validated_at TIMESTAMPTZ,
    risk_score DECIMAL(5,4),
    executed_at TIMESTAMPTZ,
    settled_at TIMESTAMPTZ
);

-- Indexes for performance
CREATE INDEX idx_opportunities_timestamp ON opportunities(timestamp DESC);
CREATE INDEX idx_opportunities_asset ON opportunities(asset);
CREATE INDEX idx_opportunities_status ON opportunities(status);

-- Aggregated metrics (TimescaleDB)
CREATE HYPERTABLE metrics (
    time TIMESTAMPTZ,
    metric_type TEXT,
    value DOUBLE PRECISION,
    exchange TEXT
);
```

---

## 4. DEPLOYMENT ARCHITECTURE

### 4.1 Container Configuration

**Docker Compose:**
```yaml
version: '3.8'

services:
  scanner-agent:
    build: ./agents/scanner
    environment:
      - REDIS_HOST=redis
      - EXCHANGE_BINANCE_API_KEY=${BINANCE_API_KEY}
      - EXCHANGE_COINBASE_API_KEY=${COINBASE_API_KEY}
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M

  validator-agent:
    build: ./agents/validator
    environment:
      - REDIS_HOST=redis
      - FEE_SCHEDULES_FILE=/config/fees.json
    depends_on:
      - redis

  risk-manager-agent:
    build: ./agents/risk
    environment:
      - REDIS_HOST=redis
      - CAPITAL_LIMIT=${CAPITAL_LIMIT}
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 256M

  executor-agent:
    build: ./agents/executor
    environment:
      - REDIS_HOST=redis
      - EXCHANGE_API_KEYS_FILE=/config/api_keys.json
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M

  reconciler-agent:
    build: ./agents/reconciler
    environment:
      - REDIS_HOST=redis
      - POSTGRES_HOST=postgres
    depends_on:
      - postgres

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data

  postgres:
    image: timescale/timescaledb:latest-pg15
    environment:
      - POSTGRES_DB=trading_db
    volumes:
      - postgres-data:/var/lib/postgresql/data

volumes:
  redis-data:
  postgres-data:
```

### 4.2 Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: scanner-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: scanner-agent
  template:
    metadata:
      labels:
        app: scanner-agent
    spec:
      containers:
      - name: scanner
        image: trading-team/scanner:latest
        resources:
          requests:
            cpu: 250m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
```

---

## 5. MONITORING & ALERTING

### 5.1 Metrics Collection

**Prometheus Metrics:**
```python
# Metrics to track
METRICS = {
    "opportunities_detected": Counter,
    "opportunities_validated": Counter,
    "positions_opened": Counter,
    "positions_closed": Counter,
    "total_pnl": Gauge,
    "position_exposure": Gauge,
    "execution_latency": Histogram,
    "order_fill_rate": Histogram,
    "api_rate_limit_remaining": Gauge,
    "system_uptime": Gauge
}
```

**Grafana Dashboard:**
- Real-time P&L
- Active positions
- Opportunity flow
- Execution latency
- API usage
- System health

### 5.2 Alerting Rules

```yaml
# Prometheus alerting rules
groups:
  - name: trading-alerts
    rules:
      - alert: HighPositionExposure
        expr: position_exposure > 0.5
        for: 5m
        annotations:
          summary: "Position exposure exceeds 50% of capital"
      
      - alert: DailyLossExceeded
        expr: daily_pnl < -0.02
        for: 15m
        annotations:
          summary: "Daily loss exceeds 2% limit"
      
      - alert: APIRateLimitWarning
        expr: api_rate_limit_remaining < 100
        annotations:
          summary: "Approaching API rate limit"
      
      - alert: ReconciliationFailed
        expr: reconciliation_status == "failed"
        annotations:
          summary: "Position reconciliation failed"
```

### 5.3 Logging Strategy

**Structured Logging:**
```python
import logging
import json

logger = logging.getLogger("scanner-agent")

def log_opportunity(opportunity):
    logger.info(
        "opportunity_detected",
        extra={
            "asset": opportunity.asset,
            "buy_exchange": opportunity.buy_exchange,
            "sell_exchange": opportunity.sell_exchange,
            "spread": opportunity.price_diff,
            "confidence": opportunity.confidence
        }
    )
```

**Log Aggregation:**
- ELK Stack (Elasticsearch, Logstash, Kibana) or
- Loki + Grafana

---

## 6. SECURITY CONSIDERATIONS

### 6.1 API Key Management

**Environment Variables:**
```bash
# .env file (never commit)
BINANCE_API_KEY=sk_live_...
BINANCE_API_SECRET=sk_live_...
COINBASE_API_KEY=...
COINBASE_API_SECRET=...
COINBASE_API_PASSPHRASE=...
```

**Docker Secrets:**
```yaml
secrets:
  binance_keys:
    file: ./secrets/binance.env
```

### 6.2 Access Control

**Agent Authentication:**
```python
# Each agent authenticates with Redis
async def authenticate_agent(agent_id):
    token = await redis.get(f"agent:{agent_id}:token")
    if not token:
        raise AuthenticationError("Agent not authenticated")
    return token
```

### 6.3 Rate Limiting

```python
# Per-agent rate limiting
async def check_rate_limit(exchange, endpoint):
    key = f"rate_limit:{exchange}:{endpoint}"
    current = await redis.incr(key)
    if current == 1:
        await redis.expire(key, 60)  # 1 minute window
    
    if current > 1200:  # Binance limit
        raise RateLimitError("Exchange rate limit exceeded")
```

---

## 7. TESTING STRATEGY

### 7.1 Unit Tests

```python
# Test individual agent components
def test_validator_calculates_net_profit():
    opportunity = create_test_opportunity()
    result = validator.validate_opportunity(opportunity)
    assert result["net_profit"] > 0
    
def test_risk_manager_enforces_limits():
    risk_manager = RiskManagerAgent(capital=10000)
    risk_assessment = risk_manager.assess_risk(
        opportunity=create_test_opportunity(),
        current_positions=[]
    )
    assert risk_assessment["max_position_size"] <= 1000
```

### 7.2 Integration Tests

```python
# Test agent communication
async def test_scanner_to_validator():
    scanner = ScannerAgent()
    validator = ValidatorAgent()
    
    opportunity = await scanner.detect_opportunity()
    validation = await validator.validate(opportunity)
    assert validation["valid"] == True
```

### 7.3 Paper Trading

```python
# Simulated execution environment
class Simulator:
    def __init__(self):
        self.balances = {}
        self.orders = []
    
    async def simulate_order(self, order):
        # Simulate order execution without real money
        self.orders.append(order)
        self.update_balances(order)
        return {"status": "filled", "simulated": True}
```

---

## 8. NEXT STEPS

1. **Setup Development Environment**
   - Install dependencies
   - Configure Redis and PostgreSQL
   - Set up Docker Compose

2. **Build Scanner Agent**
   - Implement exchange connectors
   - Add price detection logic
   - Create opportunity messages

3. **Implement Validator Agent**
   - Add fee calculations
   - Implement liquidity checks
   - Create validation pipeline

4. **Build Risk Manager**
   - Define risk parameters
   - Implement position limits
   - Add emergency stop logic

5. **Create Executor Agent**
   - Implement order placement
   - Add order monitoring
   - Handle edge cases

6. **Build Reconciler Agent**
   - Implement settlement verification
   - Create reporting system
   - Add audit trail

7. **Setup Monitoring**
   - Configure Prometheus
   - Create Grafana dashboards
   - Set up alerting

8. **Testing & Paper Trading**
   - Unit tests for all agents
   - Integration tests
   - Paper trading simulation

9. **Live Deployment**
   - Start with small capital
   - Monitor closely
   - Scale gradually

---

*Agent architecture specification complete*
