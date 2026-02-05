# 🏦 TrueLayer to Firefly III Integration - Quick Start

## What You've Got

A complete, production-ready integration that:

✅ **Supports ALL your accounts** - Lloyds, AmEx, Revolut, partner accounts, unlimited providers
✅ **Web UI** - Easy token management, no command line needed
✅ **Auto-syncs** - Scheduled background jobs with automatic token refresh
✅ **Direct to Firefly** - No CSV files, direct API integration
✅ **Docker ready** - Deploys on TrueNAS Scale via Dockge
✅ **Smart deduplication** - Never imports the same transaction twice
✅ **Self-maintaining** - Refreshes tokens automatically, never expires

## Files You Have

```
truelayer-firefly/
├── 📄 README.md                    # Complete documentation
├── 📄 TRUENAS_DEPLOYMENT.md        # TrueNAS Scale guide
├── 📄 DEVELOPMENT.md               # Developer guide
├── 🐳 Dockerfile                   # Docker image definition
├── 🐳 docker-compose.yml           # Docker Compose config
├── ⚙️  .env.example                # Environment template
├── 🔧 setup.sh                     # Interactive setup script
├── ▶️  run.sh                      # Quick run for local dev
├── 📦 requirements.txt             # Python dependencies
└── app/                           # Application code
    ├── main.py                    # FastAPI routes & scheduler
    ├── config.py                  # Configuration
    ├── database.py                # Database setup
    ├── models.py                  # Data models
    ├── services/
    │   ├── truelayer.py          # TrueLayer integration
    │   └── firefly.py            # Firefly III integration
    └── templates/
        └── index.html            # Web UI
```

## Three Ways to Deploy

### Option 1: TrueNAS Scale (Recommended for You)

**Read:** `TRUENAS_DEPLOYMENT.md`

Quick version:
1. Open Dockge in TrueNAS
2. Create new stack named "truelayer-firefly"
3. Paste `docker-compose.yml` content
4. Fill in environment variables (TrueLayer & Firefly credentials)
5. Update volume path to your pool
6. Deploy
7. Access at `http://your-truenas-ip:8000`
8. Add providers via UI

### Option 2: Any Docker Host

```bash
# 1. Configure
./setup.sh

# 2. Deploy
docker-compose up -d

# 3. Access
http://localhost:8000
```

### Option 3: Local Development

```bash
# 1. Configure
./setup.sh

# 2. Run
./run.sh

# 3. Access
http://localhost:8000
```

## Before You Start

### 1. Get TrueLayer Credentials

- Go to [TrueLayer Console](https://console.truelayer.com/)
- Create an app (if you haven't)
- Note your **Client ID** and **Client Secret**

### 2. Get Access Tokens for Each Bank

For each account you want to sync:

1. In TrueLayer Console, use "Auth Flow" tool
2. Select provider (Lloyds, AmEx, Revolut)
3. Complete bank authorization
4. **Save the access_token and refresh_token** somewhere safe

You'll paste these into the web UI after deployment.

### 3. Get Firefly III Token

- Open Firefly III
- Go to Profile → OAuth → Personal Access Tokens
- Create new token
- Copy it

## First Run Checklist

After deploying:

- [ ] Access web UI at `http://your-server:8000`
- [ ] Check Firefly III connection status (green dot)
- [ ] Click "Add Provider"
- [ ] Add Lloyds with your Lloyds tokens
- [ ] Add AmEx with your AmEx tokens
- [ ] Add Revolut with your Revolut tokens
- [ ] Add partner's Lloyds (authorize their account first)
- [ ] Click "Sync All Now"
- [ ] Check "Recent Sync Logs" for success
- [ ] Verify transactions in Firefly III

## What Happens Next

### Automatic Syncing

- App syncs every 60 minutes (configurable)
- Only fetches NEW transactions (incremental sync)
- Automatically refreshes tokens before they expire
- Creates accounts in Firefly III if they don't exist
- Prevents duplicates using transaction IDs

### Token Management

- You NEVER need to refresh tokens manually
- App detects expiring tokens and refreshes them
- Refresh tokens are valid for 90 days
- As long as app syncs within 90 days, tokens never expire

### Adding New Providers

- Click "Add Provider" anytime
- Paste new tokens
- Sync automatically includes new provider
- Easy to add partner accounts or new banks

## Troubleshooting

### "Firefly III: Disconnected"

- Check `FIREFLY_URL` in environment variables
- Test: `curl http://firefly:8080/api/v1/about`
- Verify `FIREFLY_TOKEN` is valid

### "Token refresh failed"

- Check `TRUELAYER_CLIENT_ID` and `CLIENT_SECRET`
- Verify credentials in TrueLayer Console
- Re-authorize provider if needed

### No transactions syncing

- Check provider is "Enabled"
- Look at "Recent Sync Logs" for errors
- Verify account has transactions in date range
- Check container logs: `docker logs truelayer-firefly`

### Provider already exists

- Use unique names for each provider
- Example: "Lloyds-Joint", "Lloyds-Savings", "Lloyds-Partner"

## Advanced Features

### Custom Sync Interval

Edit environment variable:
```env
SYNC_INTERVAL_MINUTES=30  # Sync every 30 minutes
```

### Manual Sync

- Click "Sync All Now" button in UI
- Or specific provider "Sync" button

### Enable/Disable Providers

- Toggle providers on/off without deleting
- Disabled providers skip automatic syncs

### PostgreSQL (Optional)

For heavy usage, switch from SQLite:

1. Add PostgreSQL to docker-compose
2. Update `DATABASE_URL`
3. Restart

See `README.md` for details.

## Security Best Practices

✅ **Run on internal network** - Don't expose to internet
✅ **Use HTTPS** - Put behind Nginx Proxy Manager
✅ **Backup database** - Contains tokens and sync state
✅ **Keep updated** - Watch for security updates
✅ **Secure .env** - Never commit to git

## Getting Help

1. **Read the docs**
   - `README.md` - Full documentation
   - `TRUENAS_DEPLOYMENT.md` - TrueNAS specific
   - `DEVELOPMENT.md` - Developer guide

2. **Check logs**
   ```bash
   docker logs truelayer-firefly
   ```

3. **Test connections**
   - UI shows Firefly status
   - Sync logs show errors

4. **Common issues**
   - All in README.md troubleshooting section

## What Makes This Better Than truelayer2firefly?

| Feature | This Integration | truelayer2firefly |
|---------|------------------|-------------------|
| Multiple providers | ✅ Unlimited | ❌ One only |
| Web UI | ✅ Full interface | ❌ None |
| Token management | ✅ Automatic | ⚠️ Manual |
| Partner accounts | ✅ Easy to add | ❌ Not supported |
| Background sync | ✅ Scheduled | ❌ Manual cron |
| Direct API | ✅ Firefly API | ⚠️ CSV files |
| Easy deployment | ✅ Docker ready | ⚠️ Complex setup |

## Next Steps

1. **Deploy** using your preferred method
2. **Add providers** via web UI
3. **Test sync** with "Sync All Now"
4. **Verify** transactions appear in Firefly III
5. **Relax** - it's now automatic! ☕

## Support

Having issues? Create a GitHub issue with:
- What you tried
- Error messages from logs
- Environment (TrueNAS version, Docker version, etc.)
- Redact all tokens/secrets!

---

**Happy syncing! 🎉**

Your transactions will now flow automatically from TrueLayer → This App → Firefly III

Set it and forget it! 🚀
