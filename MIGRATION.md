# Migration Guide: From Simple Script to Docker App

If you're currently using the simple `pull_transactions.py` script with a `tokens.json` file, this guide will help you migrate to the new Docker-based application.

## What's Different?

### Old Setup (pull_transactions.py)
- Manual execution required
- Tokens stored in `Personal/tokens.json`
- CSV output only
- No web interface
- Single-run operation

### New Setup (Docker App)
- Automatic scheduled syncing
- Web UI for management
- Direct Firefly III integration
- Multiple providers support
- Database storage
- Token auto-renewal

## Migration Steps

### 1. Backup Your Existing Data

Before starting, backup:
```bash
cp Personal/tokens.json Personal/tokens.json.backup
cp Personal/sync_state.json Personal/sync_state.json.backup
```

### 2. Extract Your Refresh Tokens

Your existing `tokens.json` file looks like this:
```json
{
    "lloyds": {
        "refresh_token": "abc123...",
        "type": "accounts"
    },
    "amex": {
        "refresh_token": "xyz789...",
        "type": "cards"
    }
}
```

Extract the refresh tokens - you'll need them for the new app.

### 3. Deploy the New Application

Follow the deployment guide (README.md or DOCKGE_DEPLOYMENT.md) to:
1. Set up Docker/Dockge
2. Configure environment variables
3. Start the application

### 4. Add Your Providers via Web UI

For each entry in your old `tokens.json`:

1. Open `http://localhost:5000`
2. Go to **Providers**
3. Click **Add Provider**
4. Fill in:
   - **Name**: Same as your JSON key (e.g., "lloyds")
   - **Account Type**: 
     - `"type": "accounts"` → Select "Bank Accounts"
     - `"type": "cards"` → Select "Credit/Debit Cards"
   - **Refresh Token**: Copy from your `tokens.json`
5. Click **Add Provider**

Repeat for each provider.

### 5. Sync State Migration (Optional)

The new app tracks sync state automatically. You have two options:

#### Option A: Fresh Start (Recommended)
Just run the first sync. The app will fetch all transactions and Firefly III will handle duplicates.

#### Option B: Import Sync State
If you want to preserve sync timestamps:

1. Stop the Docker container
2. Access the SQLite database:
```bash
sqlite3 data/app.db
```

3. For each account in your old `sync_state.json`, insert:
```sql
INSERT INTO sync_state (provider_id, account_id, last_timestamp, last_sync)
VALUES (
    1,  -- Replace with provider ID from providers table
    'account_id_from_old_file',
    'last_timestamp_from_old_file',
    CURRENT_TIMESTAMP
);
```

4. Exit SQLite and restart the container

### 6. Verify Migration

1. Go to **Dashboard**
2. Click **Sync Now**
3. Check that:
   - Providers show in the list
   - Sync completes without errors
   - Transactions appear in Firefly III

## Comparison: Before and After

### Before: Manual Script

```bash
# Every time you want to sync:
cd /path/to/script
python3 pull_transactions.py

# Then manually import CSV to Firefly III
# Or use separate import tool
```

### After: Automated Integration

```bash
# One-time setup:
docker-compose up -d

# That's it! The app:
# - Syncs automatically every 6 hours
# - Renews tokens automatically
# - Sends directly to Firefly III
# - Tracks all state
```

## Features You Gain

✅ **Web UI**: No more editing JSON files manually  
✅ **Auto-sync**: Set it and forget it  
✅ **Direct Integration**: No CSV export/import needed  
✅ **Multi-user**: Add partner's accounts easily  
✅ **Monitoring**: Dashboard shows sync status  
✅ **Token Management**: Automatic refresh token renewal  
✅ **Error Handling**: Better error messages and logging  
✅ **Duplicate Prevention**: Built-in duplicate detection  

## Updating Your Workflow

### Old Workflow
1. Run script manually
2. Check CSV output
3. Import CSV to Firefly III
4. Manually track which transactions were imported
5. Update sync_state.json manually if needed

### New Workflow
1. *(Nothing - it runs automatically)*
2. Check Dashboard occasionally
3. Add new providers as needed via UI

## Troubleshooting Migration

### "Invalid refresh token" error

Your tokens may have expired. Get fresh ones:
1. Go to TrueLayer Console
2. Re-authenticate for each provider
3. Copy new refresh tokens
4. Update in the web UI (or add as new providers)

### Transactions appear duplicated

- First sync after migration may show duplicates
- Firefly III's duplicate detection should catch them
- Future syncs will use proper state tracking

### Can't access old CSV files

The new app doesn't export CSV by default (it goes straight to Firefly).

To export CSV for backup:
```python
# Add this endpoint to app.py if needed:
@app.route('/api/export/csv')
def export_csv():
    # Implementation to export transactions to CSV
    pass
```

### Want to keep both systems running

You can run both temporarily:
- Old script for backup/CSV
- New app for Firefly sync

Just don't run them at the exact same time to avoid token conflicts.

## Cleanup (After Successful Migration)

Once you're happy with the new system:

```bash
# Archive old files
mkdir -p archive
mv Personal/ archive/
mv pull_transactions.py archive/

# Optional: Remove archived files after confirming everything works
# rm -rf archive/
```

## Going Back (If Needed)

If you need to revert:

1. Stop the Docker container
2. Restore your backed-up `tokens.json`
3. Run the old script as before

Your old tokens should still work (unless they expired during migration).

## Getting Help

If you encounter issues:

1. Check Docker logs: `docker logs truelayer-firefly`
2. Review the README.md
3. Check GitHub issues
4. The old `pull_transactions.py` can still be used in parallel as a backup

## Next Steps After Migration

1. **Set up partner's accounts**: Add their providers in the UI
2. **Adjust sync schedule**: Change in `docker-compose.yml` if needed
3. **Configure account mapping**: Map TrueLayer accounts to specific Firefly III accounts
4. **Set up monitoring**: Check Dashboard regularly for sync status
5. **Enable backups**: Back up the SQLite database regularly

## Why Migrate?

The new system offers:
- **90% less manual work**: Automatic syncing vs manual runs
- **Better reliability**: Automatic token renewal
- **Easier management**: Web UI vs JSON editing
- **More features**: Multi-provider, partner accounts, monitoring
- **Future-proof**: Active development and updates

Migration takes ~15 minutes, but saves hours of manual work every month!
