# Quick Reference Guide

## 🚀 Quick Start (5 Minutes)

```bash
# 1. Setup environment
cp .env.example .env
# Edit .env with your credentials

# 2. Start the app
docker-compose up -d

# 3. Access web UI
# Open: http://localhost:5000
```

## 🔑 Required Credentials

### TrueLayer (from https://console.truelayer.com/)
- Client ID
- Client Secret
- Refresh tokens (one per bank/card)

### Firefly III (from your Firefly instance)
- Instance URL
- Personal Access Token

## 📋 Common Tasks

### Add a New Bank Account
1. Get refresh token from TrueLayer Console
2. Web UI → Providers → Add Provider
3. Enter name, type, and token
4. Done!

### Manual Sync
Dashboard → Sync Now

### View Logs
```bash
docker logs truelayer-firefly
```

### Change Sync Schedule
Edit `docker-compose.yml`:
```yaml
- SYNC_SCHEDULE=0 */6 * * *  # Every 6 hours
```
Restart container.

### Backup Database
```bash
cp data/app.db data/app.db.backup
```

## 🔧 Troubleshooting Quick Fixes

### Can't connect to Firefly
- Check URL has `https://` or `http://`
- Verify token in Firefly: Profile → OAuth → Tokens
- Test connection in Settings page

### Token expired
- Get new refresh token from TrueLayer Console
- Update provider in web UI
- Or delete and re-add provider

### Sync not running automatically
- Check logs for errors
- Verify `SYNC_SCHEDULE` env var
- Restart container

### Duplicate transactions
- Normal for first sync
- Firefly III prevents actual duplicates
- Will not happen in subsequent syncs

## 📊 API Endpoints

```
GET  /                      - Dashboard
GET  /providers             - Manage providers
GET  /settings              - Configuration
POST /api/sync/manual       - Trigger sync
GET  /api/sync/status       - Get sync status
POST /api/providers         - Add provider
DELETE /api/providers/:id   - Remove provider
POST /api/firefly/config    - Configure Firefly
```

## 🌐 Access URLs

| Service | URL | Notes |
|---------|-----|-------|
| Web UI | http://localhost:5000 | Main interface |
| Firefly III | Your instance | Set in Settings |
| TrueLayer Console | https://console.truelayer.com | Get tokens |

## 🔒 Security Checklist

- [ ] Use strong `SECRET_KEY` in .env
- [ ] Keep `.env` file secret
- [ ] Regular database backups
- [ ] Use HTTPS in production
- [ ] Consider reverse proxy authentication
- [ ] Monitor access logs

## 📈 Monitoring

### Check Sync Status
Dashboard shows:
- Active providers
- Firefly III connection
- Last sync time
- Transaction count

### View Detailed Logs
```bash
docker logs -f truelayer-firefly
```

### Database Stats
```bash
sqlite3 data/app.db "SELECT COUNT(*) FROM providers;"
sqlite3 data/app.db "SELECT name, last_sync FROM providers;"
```

## 🔄 Update Process

```bash
# Pull latest changes
git pull

# Rebuild container
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## 💾 Backup & Restore

### Backup
```bash
# Backup database
cp data/app.db backups/app-$(date +%Y%m%d).db

# Backup entire data directory
tar -czf backups/data-$(date +%Y%m%d).tar.gz data/
```

### Restore
```bash
# Stop container
docker-compose down

# Restore database
cp backups/app-20240115.db data/app.db

# Start container
docker-compose up -d
```

## 🎯 Best Practices

1. **Regular Backups**: Daily or weekly backups of `data/app.db`
2. **Monitor Logs**: Check logs weekly for errors
3. **Token Refresh**: Tokens auto-refresh during sync
4. **Sync Frequency**: Default 6 hours is good for most users
5. **Test Changes**: Use "Sync Now" to test after adding providers

## 📞 Support Resources

| Resource | Link |
|----------|------|
| Main README | README.md |
| Dockge Guide | DOCKGE_DEPLOYMENT.md |
| Migration Guide | MIGRATION.md |
| TrueLayer Docs | https://docs.truelayer.com |
| Firefly III Docs | https://docs.firefly-iii.org |

## 🎨 Customization

### Change Port
In `docker-compose.yml`:
```yaml
ports:
  - "8080:5000"  # Use port 8080 instead
```

### Change Data Location
In `docker-compose.yml`:
```yaml
volumes:
  - /your/custom/path:/app/data
```

### Adjust Logging Level
Add to `docker-compose.yml`:
```yaml
environment:
  - LOG_LEVEL=DEBUG  # or INFO, WARNING, ERROR
```

## 🚨 Emergency Recovery

### Complete Reset
```bash
docker-compose down
rm -rf data/
docker-compose up -d
# Reconfigure everything in web UI
```

### Restore from CSV (if needed)
If you have old CSV exports:
1. Import manually to Firefly III
2. Set up new providers in web UI
3. Future syncs will be automatic

## 🎓 Learn More

- Read the full README.md for comprehensive documentation
- Check TrueLayer API docs for advanced features  
- Explore Firefly III rules for automatic categorization
- Join Firefly III community for tips and tricks

---

**Remember**: This integration is set-and-forget. After initial setup, it runs automatically!
