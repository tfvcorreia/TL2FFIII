# Architecture Overview

## System Design

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Browser                             │
│                    (http://server:5000)                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ HTTP
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Flask Web Application                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Web UI Layer (HTML/JavaScript/CSS)                      │   │
│  │  - Provider Management                                   │   │
│  │  - Configuration Interface                               │   │
│  │  - Manual Sync Triggers                                  │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  API Layer (Flask Routes)                                │   │
│  │  - /api/providers                                        │   │
│  │  - /api/config                                           │   │
│  │  - /api/sync                                             │   │
│  │  - /api/test-firefly                                     │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Business Logic Layer                                    │   │
│  │  - Token Management & Refresh                            │   │
│  │  - TrueLayer API Integration                             │   │
│  │  - Firefly III API Integration                           │   │
│  │  - Transaction Transformation                            │   │
│  │  - Sync State Management                                 │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Background Sync Thread                                  │   │
│  │  - Periodic automatic syncing                            │   │
│  │  - Configurable interval                                 │   │
│  └──────────────────────────────────────────────────────────┘   │
└───────────┬──────────────────────────────┬──────────────────────┘
            │                              │
            │                              │
            ▼                              ▼
┌────────────────────────┐    ┌────────────────────────────┐
│   TrueLayer API        │    │   Firefly III API          │
│                        │    │                            │
│ - Token Refresh        │    │ - Account Creation         │
│ - Account Listing      │    │ - Transaction Creation     │
│ - Transaction Fetch    │    │ - Duplicate Detection      │
└────────────────────────┘    └────────────────────────────┘
            │                              │
            │                              │
            ▼                              ▼
┌────────────────────────┐    ┌────────────────────────────┐
│   Bank Accounts        │    │   Firefly III Database     │
│                        │    │                            │
│ - Lloyds               │    │ - Accounts                 │
│ - AmEx                 │    │ - Transactions             │
│ - Revolut              │    │ - Rules                    │
│ - Partner Accounts     │    │                            │
└────────────────────────┘    └────────────────────────────┘
```

## Data Flow

### Sync Process

1. **Trigger**: User clicks "Sync" or automatic interval fires
2. **Token Refresh**: Application refreshes TrueLayer access token using stored refresh token
3. **Account Discovery**: Fetch all accounts/cards from TrueLayer for each provider
4. **Firefly Account Creation**: Create corresponding accounts in Firefly III (if not exists)
5. **Transaction Fetch**: Get transactions since last sync (incremental)
6. **Transformation**: Convert TrueLayer format to Firefly III format
7. **Import**: Create transactions in Firefly III
8. **State Update**: Save last sync timestamp for each account
9. **Token Update**: Save new refresh token if changed

### Data Transformation

```python
# TrueLayer Transaction Format
{
    "transaction_id": "abc123",
    "timestamp": "2026-02-04T10:30:00Z",
    "description": "TESCO STORES",
    "amount": -45.23,
    "currency": "GBP",
    "transaction_type": "debit",
    "transaction_category": "shopping"
}

# ↓ Transformation ↓

# Firefly III Transaction Format
{
    "type": "withdrawal",
    "date": "2026-02-04T10:30:00Z",
    "amount": "45.23",
    "description": "TESCO STORES",
    "source_id": "123",  # Firefly account ID
    "destination_name": "TESCO STORES",
    "currency_code": "GBP",
    "category_name": "shopping",
    "external_id": "abc123",  # For duplicate detection
    "notes": "Provider: Lloyds\nAccount: Main Account"
}
```

## Components

### 1. Flask Application (`app.py`)

**Responsibilities**:
- HTTP server and routing
- API endpoint handling
- Background sync thread management
- Business logic orchestration

**Key Functions**:
- `load_providers()` / `save_providers()`: Manage provider configurations
- `load_config()` / `save_config()`: Manage Firefly III settings
- `refresh_access_token()`: Keep TrueLayer tokens fresh
- `sync_provider()`: Core sync logic for a single provider
- `transform_to_firefly_transaction()`: Data transformation

### 2. Web UI (`templates/index.html`)

**Responsibilities**:
- User interface for configuration
- Provider management forms
- Manual sync triggers
- Status display

**Features**:
- Responsive design
- Real-time updates via JavaScript
- Form validation
- Error handling and display

### 3. Data Persistence (`/data` volume)

**Files**:
- `providers.json`: Provider credentials and metadata
- `config.json`: Firefly III configuration and sync settings
- `sync_state.json`: Last sync timestamps per account

**Format Example**:

```json
// providers.json
{
  "Lloyds": {
    "client_id": "test-abc123",
    "client_secret": "secret-xyz",
    "refresh_token": "refresh-token-here",
    "type": "accounts"
  },
  "AmEx": {
    "client_id": "test-def456",
    "client_secret": "secret-uvw",
    "refresh_token": "refresh-token-here",
    "type": "cards"
  }
}

// config.json
{
  "firefly_url": "https://firefly.example.com",
  "firefly_token": "eyJ0eXAiOiJKV1QiLCJh...",
  "sync_interval": 3600,
  "auto_sync": true
}

// sync_state.json
{
  "Lloyds_account_123": "2026-02-04T10:30:00Z",
  "AmEx_card_456": "2026-02-04T09:15:00Z"
}
```

## Docker Architecture

```
┌──────────────────────────────────────────────────┐
│              Docker Container                     │
│  ┌────────────────────────────────────────────┐  │
│  │  Gunicorn (WSGI Server)                    │  │
│  │  ├── Worker 1 (Flask App)                  │  │
│  │  └── Worker 2 (Flask App)                  │  │
│  └────────────────────────────────────────────┘  │
│                                                   │
│  Port 5000 exposed → Host Port 5000              │
│                                                   │
│  Volume Mount: ./data → /data                    │
│  (Persistent storage for configs)                │
└──────────────────────────────────────────────────┘
```

## Security Considerations

### Token Storage
- Refresh tokens stored in JSON files on persistent volume
- Volume should be secured at filesystem level
- No encryption at rest (consider adding if needed)

### API Access
- No authentication on web UI (runs on trusted network)
- Firefly III API requires bearer token
- TrueLayer API requires OAuth flow

### Recommendations
1. Run behind reverse proxy with HTTPS
2. Use strong Firefly III tokens
3. Rotate TrueLayer tokens regularly
4. Backup `/data` directory encrypted
5. Restrict network access to trusted IPs

## Scalability

### Current Limitations
- Single instance design (no load balancing needed)
- Background sync thread is single-threaded
- Suitable for personal/small business use

### Performance Characteristics
- **Sync Time**: ~2-5 seconds per account per provider
- **Memory**: ~100-200MB container
- **CPU**: Minimal, spikes during sync
- **Network**: API calls only during sync

### Scaling Considerations
If managing 100+ accounts:
1. Increase sync interval to reduce API load
2. Consider job queue (Celery/RQ) for parallel processing
3. Split providers across multiple instances
4. Add caching layer for API responses

## API Rate Limits

### TrueLayer
- **Token Refresh**: No documented limit
- **Account Listing**: ~10 req/min per provider
- **Transactions**: ~10 req/min per account
- **Strategy**: Sequential processing with delays if needed

### Firefly III
- Depends on your instance
- Generally no strict limits for self-hosted
- Use `error_if_duplicate_hash` to prevent duplicates

## Error Handling

### Token Expiry
- TrueLayer refresh tokens expire after 90 days of inactivity
- Application attempts refresh on every sync
- User notified if manual re-authorization needed

### API Failures
- Transient errors: Logged, sync continues
- Authentication errors: Halt sync, notify user
- Validation errors: Skip transaction, log for review

### Duplicate Prevention
- Use `external_id` for unique transaction identification
- Firefly III's `error_if_duplicate_hash` prevents duplicates
- Sync state tracks last processed timestamp

## Future Enhancements

Potential improvements:
1. **Encryption**: Encrypt tokens at rest
2. **Authentication**: Add login to web UI
3. **Multi-user**: Support multiple Firefly III instances
4. **Webhooks**: Real-time sync via TrueLayer webhooks
5. **Rules Engine**: Custom transaction categorization
6. **Reporting**: Dashboard with sync statistics
7. **Notifications**: Email/Slack alerts on sync completion
8. **Categories Mapping**: Auto-map TrueLayer categories to Firefly III
9. **Split Transactions**: Support for split transactions
10. **Currency Conversion**: Handle multi-currency accounts

## Testing Locally

```bash
# Without Docker
cd app
pip install -r requirements.txt
export DATA_DIR=./test_data
python app.py

# Access at http://localhost:5000

# With Docker
docker build -t truelayer-firefly .
docker run -p 5000:5000 -v $(pwd)/data:/data truelayer-firefly
```

## Monitoring

### Health Check
- HTTP GET `http://container:5000/` should return 200 OK
- Docker healthcheck runs every 30 seconds
- Restart policy: `unless-stopped`

### Logs
```bash
# View logs
docker logs -f truelayer-firefly-sync

# Log levels
- INFO: Sync operations, token refreshes
- WARNING: Missing accounts, empty transactions
- ERROR: API failures, configuration issues
```

### Metrics to Monitor
- Sync success/failure rate
- Number of transactions imported per sync
- API response times
- Token refresh frequency
- Disk usage of `/data` volume

## Troubleshooting Flow

```
User reports sync not working
         │
         ▼
Is Firefly III accessible? ──No──► Check URL, network, firewall
         │ Yes
         ▼
Test Firefly III token ──Invalid──► Regenerate token in Firefly III
         │ Valid
         ▼
Check TrueLayer tokens ──Expired──► Re-authorize via OAuth flow
         │ Valid
         ▼
Check sync logs ──API errors──► Check rate limits, retry
         │ No errors
         ▼
Check transaction IDs ──Duplicates──► Already imported successfully!
```

---

This architecture is designed for:
- ✅ Simplicity over complexity
- ✅ Reliability over features
- ✅ Maintainability over performance
- ✅ Privacy over cloud convenience
