# TradingView Webhook Configuration

## Webhook URL
```
http://YOUR_SERVER_IP:8000/webhook
```

## Alert Message Format (JSON)

### Basic Format
```json
{
  "symbol": "{{ticker}}",
  "price": {{close}},
  "volume": {{volume}},
  "timestamp": "{{time}}"
}
```

### Full Format (Recommended)
```json
{
  "symbol": "{{ticker}}",
  "price": {{close}},
  "volume": {{volume}},
  "timestamp": "{{time}}",
  "source": "tradingview",
  "interval": "{{interval}}",
  "exchange": "{{exchange}}"
}
```

## TradingView Alert Setup

1. **Create Alert**: On chart, click "Alert" button
2. **Condition**: Choose your trigger (e.g., "Crossing", "Greater Than")
3. **Alert Name**: "False Breakout - {{ticker}}"
4. **Webhook URL**: Enter your ingest service URL
5. **Message**: Paste the JSON format above

## Sample Payloads

### NIFTY Future
```json
{
  "symbol": "NIFTY_FUT",
  "price": 19500.50,
  "volume": 125000,
  "timestamp": "2024-12-05T10:30:00Z",
  "source": "tradingview"
}
```

### BANKNIFTY Future
```json
{
  "symbol": "BANKNIFTY_FUT",
  "price": 44250.75,
  "volume": 85000,
  "timestamp": "2024-12-05T10:31:00Z",
  "source": "tradingview"
}
```

### BTCUSDT
```json
{
  "symbol": "BTCUSDT",
  "price": 42350.25,
  "volume": 1250.5,
  "timestamp": "2024-12-05T10:32:00Z",
  "source": "tradingview"
}
```

## Testing Webhook

### Using curl
```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "NIFTY_FUT",
    "price": 19500.50,
    "volume": 125000,
    "timestamp": "2024-12-05T10:30:00Z",
    "source": "tradingview"
  }'
```

### Using Postman
1. Method: POST
2. URL: `http://localhost:8000/webhook`
3. Headers: `Content-Type: application/json`
4. Body: Paste sample JSON

### Expected Response
```json
{
  "status": "success",
  "s3_path": "s3://data/ticks/NIFTY_FUT/2024/12/05/NIFTY_FUT_103000123456.json"
}
```

## Troubleshooting

### "Kafka producer not available"
- This is normal if not using the existing main.py
- The ingest_service.py uses Redis Streams, not Kafka

### Timestamp Format Issues
- TradingView sends: `2024-12-05T10:30:00Z`
- System expects: ISO 8601 format
- Fallback: Server time if parse fails

### Symbol Mapping
Ensure TradingView ticker matches config symbols:
- `config.py` → `SYMBOLS = ["NIFTY_FUT", "BANKNIFTY_FUT", "BTCUSDT"]`
- Alert ticker must match exactly
