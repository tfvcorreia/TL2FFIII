# Dockge Setup Guide for TrueNAS Scale

This guide walks you through deploying the TrueLayer → Firefly III integration on TrueNAS Scale using Dockge.

## Prerequisites

1. TrueNAS Scale with Dockge installed
2. Firefly III already running (with URL and API token)
3. TrueLayer refresh tokens for each bank (use `get_tokens.py` to obtain them)

## Installation Steps

### Step 1: Upload Files to TrueNAS

1. **Access your TrueNAS Scale** via SSH or the file manager

2. **Navigate to your Dockge stacks directory**:
   ```bash
   cd /mnt/your-pool/dockge/stacks
   ```

3. **Create the stack directory**:
   ```bash
   mkdir truelayer-firefly
   cd truelayer-firefly
   ```

4. **Upload these files** to the directory:
   - `docker-compose.yml`
   - `Dockerfile`
   - `.dockerignore`
   
   And create the `app` subdirectory with:
   - `app/app.py`
   - `app/requirements.txt`
   - `app/templates/index.html`

   **Quick Method**: Use WinSCP, FileZilla, or TrueNAS Scale's file manager to upload the entire `truelayer-firefly-integration` folder.

### Step 2: Create Data Directory

```bash
# Create the data directory that will persist your configuration
mkdir -p /mnt/your-pool/dockge/stacks/truelayer-firefly/data

# Set proper permissions
chmod 755 /mnt/your-pool/dockge/stacks/truelayer-firefly/data
```

### Step 3: Deploy in Dockge

1. **Open Dockge** in your browser (usually `http://truenas-ip:5001`)

2. **Create New Stack**:
   - Click the "+" button or "Compose" → "New Stack"
   - Name: `truelayer-firefly`
   - Browse to the folder you created, or paste this docker-compose.yml:

```yaml
version: '3.8'

services:
  truelayer-firefly:
    build: .
    container_name: truelayer-firefly-sync
    restart: unless-stopped
    ports:
      - "5000:5000"
    volumes:
      - ./data:/data
    environment:
      - DATA_DIR=/data
      - TZ=Europe/London
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:5000/', timeout=5)"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
```

3. **Click "Deploy"** or "Start"

4. **Wait for the build** (first time may take 2-3 minutes)

5. **Check the logs** to ensure it started successfully

### Step 4: Access the Web UI

1. Open your browser and go to: `http://your-truenas-ip:5000`

2. You should see the TrueLayer → Firefly III interface

### Step 5: Configure Firefly III

1. In the web UI, scroll to **"Firefly III Configuration"**

2. Fill in:
   - **Firefly III URL**: Your Firefly III URL (e.g., `http://truenas-ip:8080` or `https://firefly.yourdomain.com`)
   - **Personal Access Token**: Get this from Firefly III (Profile → OAuth → Personal Access Tokens → Create New Token)
   - **Sync Interval**: How often to sync in seconds (3600 = 1 hour)
   - **Auto Sync**: Enable to automatically sync in the background

3. Click **"Save Configuration"**

4. Click **"Test Connection"** to verify it works

### Step 6: Add Providers

Before adding providers, you need refresh tokens. Run `get_tokens.py` **on your local computer**:

```bash
# On your local machine (not in TrueNAS)
python get_tokens.py

# Follow the prompts:
# 1. Browser will open
# 2. Select your bank (Lloyds, AmEx, Revolut, etc.)
# 3. Authorize the connection
# 4. Copy the refresh token from the terminal
```

Then in the web UI:

1. Click **"Add Provider"**

2. Fill in the form:
   - **Provider Name**: e.g., "Lloyds", "AmEx", "Partner-Lloyds"
   - **Client ID**: From your TrueLayer application
   - **Client Secret**: From your TrueLayer application
   - **Refresh Token**: Obtained from `get_tokens.py`
   - **Account Type**: Choose "accounts" or "cards"

3. Click **"Save Provider"**

4. Repeat for each bank/provider you want to add

### Step 7: Run First Sync

1. Click **"Sync All Providers"** to test everything

2. Check the results - you should see how many transactions were synced

3. Check your Firefly III to verify transactions appear

## Updating the Stack

If you need to update the application:

1. **In Dockge**:
   - Stop the stack
   - Edit the files if needed
   - Click "Rebuild" or "Deploy" again

2. **Your data is safe** - it's in the `./data` volume and persists across rebuilds

## Adding Partner Accounts

To add your partner's Lloyds account:

1. **Get their TrueLayer tokens**:
   - They need to run `get_tokens.py` and authorize their Lloyds account
   - Or you do it together on their device

2. **Add as a new provider**:
   - Provider Name: "Partner-Lloyds" (or any distinguishing name)
   - Use their refresh token
   - The system treats it as a completely separate provider

## Troubleshooting

### Container won't start

```bash
# Check logs in Dockge, or via SSH:
docker logs truelayer-firefly-sync

# Common issues:
# - Port 5000 already in use (change in docker-compose.yml)
# - Permission issues (check data directory permissions)
```

### Can't access web UI

```bash
# Check if container is running:
docker ps | grep truelayer

# Check firewall on TrueNAS:
# System Settings → Services → Make sure Docker is allowed
```

### Sync errors

1. Check that Firefly III URL is correct and accessible from TrueNAS
2. Verify the Personal Access Token is valid
3. Check TrueLayer tokens haven't expired (refresh tokens last 90 days of inactivity)

### Port conflicts

If port 5000 is used:

```yaml
# Edit docker-compose.yml in Dockge:
ports:
  - "5001:5000"  # Change 5001 to any free port

# Then rebuild the stack
```

## Security Recommendations

1. **Don't expose to internet**: Keep this internal or behind VPN
2. **Use reverse proxy**: Consider putting behind Nginx Proxy Manager with HTTPS
3. **Regular backups**: Backup the `data` directory containing your tokens
4. **Update tokens**: Refresh tokens expire after 90 days of no use

## File Structure

Your Dockge stack should look like this:

```
/mnt/your-pool/dockge/stacks/truelayer-firefly/
├── docker-compose.yml
├── Dockerfile
├── .dockerignore
├── data/                          # Persistent data (auto-created)
│   ├── providers.json            # Your provider configurations
│   ├── config.json               # Firefly III settings
│   └── sync_state.json          # Sync state tracking
└── app/
    ├── app.py
    ├── requirements.txt
    └── templates/
        └── index.html
```

## Next Steps

1. **Set up automatic sync**: Enable "Auto Sync" in the configuration
2. **Monitor regularly**: Check logs occasionally to ensure syncing works
3. **Add more providers**: As you connect more banks, just add them in the UI

## Support

- Check the main README.md for detailed API documentation
- View logs in Dockge for troubleshooting
- Verify Firefly III transactions are importing correctly

---

**Enjoy automated transaction syncing! 🚀**
