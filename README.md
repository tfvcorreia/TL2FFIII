# TrueLayer to Firefly III Integration

A self-hosted web application that automatically syncs transactions from TrueLayer (connected to your UK banks: Lloyds, AmEx, Revolut, etc.) to Firefly III personal finance manager.

## Features

- 🌐 **Web UI** - Simple interface to manage all your bank connections
- 🔄 **Auto-sync** - Scheduled background syncing (configurable interval)
- 🏦 **Multi-provider** - Support for multiple banks and credit cards
- 👥 **Multi-account** - Add your partner's accounts easily
- 🔐 **Token management** - Automatic token refresh, never expires
- 📊 **Direct API integration** - No CSV files, direct to Firefly III
- 🐳 **Docker ready** - Deploy on TrueNAS Scale via Dockge
- 💾 **SQLite database** - Lightweight, no external DB needed (PostgreSQL optional)

## Quick Start

### Prerequisites

1. **TrueLayer Account** - Sign up at [TrueLayer Console](https://console.truelayer.com/)
   - Create an application
   - Note your Client ID and Client Secret
   - Generate access tokens for each bank (see below)

2. **Firefly III** - Running instance with a Personal Access Token
   - Generate token in Firefly III under Profile → OAuth → Personal Access Tokens

3. **Docker & Dockge** - For deployment on TrueNAS Scale

### Getting TrueLayer Access Tokens

You need to authorize each bank connection and obtain tokens:

1. Go to TrueLayer Console
2. Use the "Auth Flow" tool or create your own OAuth flow
3. Authorize each provider (Lloyds, AmEx, Revolut)
4. Save the `access_token` and `refresh_token` for each

**Important:** You only need to do this once per provider. The app will automatically refresh tokens.

### Deployment on TrueNAS Scale (Dockge)

1. **Clone or download this repository**

2. **Create a `.env` file** in the project root:

```env
# TrueLayer API Configuration
TRUELAYER_CLIENT_ID=your-client-id-here
TRUELAYER_CLIENT_SECRET=your-client-secret-here

# Firefly III Configuration
FIREFLY_URL=http://your-firefly-url:8080
FIREFLY_TOKEN=your-firefly-personal-access-token

# Sync interval (in minutes)
SYNC_INTERVAL_MINUTES=60

# Security
SECRET_KEY=generate-a-random-secret-key-here

# Timezone
TIMEZONE=Europe/London
```

3. **Deploy with Dockge:**

   - In Dockge, create a new stack
   - Copy the contents of `docker-compose.yml`
   - Paste your `.env` variables
   - Click "Start"

4. **Access the Web UI:**

   Navigate to `http://your-server-ip:8000`

5. **Add Your Providers:**

   - Click "Add Provider"
   - Enter provider name (e.g., "Lloyds", "AmEx", "Revolut")
   - Select type (Bank Accounts or Credit Cards)
   - Paste your access token and refresh token
   - Click "Add Provider"

6. **Initial Sync:**

   - Click "Sync All Now" to run your first sync
   - Check "Recent Sync Logs" for results

## Usage

### Adding Providers

Use the Web UI to add each of your bank connections:

1. **Name:** Friendly name (e.g., "Lloyds Joint Account", "AmEx Platinum")
2. **Type:** 
   - "Bank Accounts" for current accounts, savings, etc.
   - "Credit Cards" for credit card accounts
3. **Access Token:** Paste from TrueLayer authorization
4. **Refresh Token:** Paste from TrueLayer authorization

### Managing Providers

- **Enable/Disable:** Toggle providers on/off without deleting
- **Sync Individual:** Sync a specific provider manually
- **Sync All:** Sync all enabled providers at once
- **Delete:** Remove a provider completely

### Automatic Syncing

The app runs automatic syncs in the background based on `SYNC_INTERVAL_MINUTES` (default: 60 minutes).

- Incremental syncs only fetch new transactions
- Duplicate prevention using transaction IDs
- Failed syncs are logged and don't stop future syncs

### Adding Your Partner's Accounts

Simply authorize their bank accounts through TrueLayer (with their permission) and add them as separate providers in the UI. Each provider can have a different name to distinguish accounts.

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TRUELAYER_CLIENT_ID` | *required* | Your TrueLayer Client ID |
| `TRUELAYER_CLIENT_SECRET` | *required* | Your TrueLayer Client Secret |
| `FIREFLY_URL` | *required* | URL to your Firefly III instance |
| `FIREFLY_TOKEN` | *required* | Firefly III Personal Access Token |
| `DATABASE_URL` | `sqlite:///./truelayer_firefly.db` | Database connection string |
| `SYNC_INTERVAL_MINUTES` | `60` | How often to sync (in minutes) |
| `SECRET_KEY` | *required* | Secret key for session security |
| `DEBUG` | `false` | Enable debug mode |
| `TIMEZONE` | `Europe/London` | Timezone for timestamps |

### Using PostgreSQL (Optional)

To use PostgreSQL instead of SQLite:

1. Update `DATABASE_URL` in `.env`:
```env
DATABASE_URL=postgresql://user:password@postgres:5432/truelayer_firefly
```

2. Add PostgreSQL to `docker-compose.yml`:
```yaml
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: truelayer_firefly
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## Architecture

```
┌─────────────────┐
│   TrueLayer     │
│   (Banks API)   │
└────────┬────────┘
         │
         │ OAuth2 + Refresh
         │
    ┌────▼─────────────┐
    │  This App        │
    │  ┌────────────┐  │
    │  │ Web UI     │  │
    │  ├────────────┤  │
    │  │ Scheduler  │  │
    │  ├────────────┤  │
    │  │ SQLite DB  │  │
    │  └────────────┘  │
    └────┬─────────────┘
         │
         │ Firefly III API
         │
    ┌────▼─────────────┐
    │  Firefly III     │
    │  (Your Finance   │
    │   Manager)       │
    └──────────────────┘
```

## Data Flow

1. **Provider Setup:** You add providers via Web UI with initial tokens
2. **Scheduled Sync:** Background job runs every X minutes
3. **Token Refresh:** App automatically refreshes expired tokens
4. **Fetch Transactions:** Incremental fetch from last sync point
5. **Transform:** Convert TrueLayer format to Firefly III format
6. **Import:** Direct API call to Firefly III
7. **Deduplication:** Firefly III prevents duplicates via external_id
8. **Update State:** Store last sync timestamp per account

## Troubleshooting

### Connection Issues

**Firefly III not connected:**
- Check `FIREFLY_URL` is correct and accessible from container
- Verify `FIREFLY_TOKEN` is valid
- Test: `curl -H "Authorization: Bearer YOUR_TOKEN" http://firefly:8080/api/v1/about`

**TrueLayer token refresh fails:**
- Check `TRUELAYER_CLIENT_ID` and `TRUELAYER_CLIENT_SECRET`
- Verify refresh tokens are still valid (they can expire after 90 days of inactivity)
- Re-authorize the provider through TrueLayer Console

### Sync Issues

**No transactions syncing:**
- Check "Recent Sync Logs" for errors
- Verify provider is enabled
- Check account has transactions in the time period
- Look at container logs: `docker logs truelayer-firefly`

**Duplicates in Firefly:**
- Should not happen (external_id prevents this)
- Check if transaction_id is present in TrueLayer data
- Report as a bug if duplicates occur

### Performance

**Slow syncs:**
- Reduce `SYNC_INTERVAL_MINUTES` to avoid large backlogs
- Consider PostgreSQL for better performance with many transactions

## API Endpoints

The app provides a REST API:

- `GET /` - Web UI dashboard
- `GET /health` - Health check
- `GET /api/providers` - List providers
- `POST /api/providers` - Add provider
- `DELETE /api/providers/{id}` - Delete provider
- `PUT /api/providers/{id}/toggle` - Enable/disable provider
- `POST /api/sync` - Sync all providers
- `POST /api/sync/{id}` - Sync specific provider
- `GET /api/sync/status` - Get sync status
- `GET /api/firefly/test` - Test Firefly connection
- `GET /api/firefly/accounts` - List Firefly accounts

## Security Considerations

- **Access Tokens:** Stored in database, encrypted at rest if using encrypted volumes
- **Network:** Run on internal network, use reverse proxy (Nginx/Traefik) for HTTPS
- **Firewall:** Only expose port 8000 if needed externally
- **Backups:** Backup `/app/data` volume regularly (contains database and tokens)

## Comparison to truelayer2firefly

This implementation improves upon [erwindouna/truelayer2firefly](https://github.com/erwindouna/truelayer2firefly):

| Feature | This App | truelayer2firefly |
|---------|----------|-------------------|
| Multiple Providers | ✅ Unlimited | ❌ One account only |
| Web UI | ✅ Full UI | ❌ CLI only |
| Token Management | ✅ Automatic refresh | ⚠️ Manual |
| Multiple Accounts | ✅ Yes | ❌ Limited |
| Background Sync | ✅ Scheduled | ❌ Manual cron |
| Direct API | ✅ Firefly API | ⚠️ CSV import |
| Partner Accounts | ✅ Easy to add | ❌ Not supported |
| Docker Deployment | ✅ Ready | ⚠️ Requires setup |

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Support

For issues, questions, or feature requests:

1. Check existing GitHub issues
2. Review troubleshooting section
3. Create a new issue with details

## License

MIT License - See LICENSE file

## Acknowledgments

- [TrueLayer](https://truelayer.com/) - Banking API
- [Firefly III](https://www.firefly-iii.org/) - Personal finance manager
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework

---

**Made with ❤️ for better personal finance tracking**
