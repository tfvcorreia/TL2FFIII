# Deploying to TrueNAS Scale with Dockge

This guide will walk you through deploying the TrueLayer → Firefly III integration on TrueNAS Scale using Dockge.

## Prerequisites

1. TrueNAS Scale installed and running
2. Dockge installed (from TrueNAS app catalog)
3. TrueLayer application credentials (Client ID and Secret)
4. Firefly III instance running (can be on the same TrueNAS server)

## Deployment Steps

### 1. Access Dockge

1. Open your TrueNAS Scale web interface
2. Navigate to Dockge (usually at `http://your-truenas-ip:5001`)
3. Log in to Dockge

### 2. Create New Stack

1. Click **"+ Compose"** or **"New Stack"**
2. Name your stack: `truelayer-firefly`

### 3. Configure the Stack

Copy and paste this docker-compose configuration:

```yaml
version: '3.8'

services:
  truelayer-firefly:
    image: ghcr.io/yourusername/truelayer-firefly:latest
    # OR build from local directory:
    # build: .
    container_name: truelayer-firefly
    restart: unless-stopped
    
    ports:
      - "5000:5000"
    
    environment:
      # TrueLayer Configuration
      - TRUELAYER_CLIENT_ID=YOUR_CLIENT_ID_HERE
      - TRUELAYER_CLIENT_SECRET=YOUR_CLIENT_SECRET_HERE
      
      # Sync Schedule (cron format)
      - SYNC_SCHEDULE=0 */6 * * *
      
      # Flask Configuration
      - SECRET_KEY=GENERATE_RANDOM_STRING_HERE
      
    volumes:
      # Persist database - adjust path for TrueNAS
      - /mnt/your-pool/apps/truelayer-firefly/data:/app/data
```

### 4. Set Environment Variables

In the Dockge UI, replace the following values:

#### TrueLayer Credentials
- `YOUR_CLIENT_ID_HERE` → Your TrueLayer Client ID
- `YOUR_CLIENT_SECRET_HERE` → Your TrueLayer Client Secret

#### Secret Key
Generate a random secret key:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```
Replace `GENERATE_RANDOM_STRING_HERE` with the output.

#### Storage Path
- `/mnt/your-pool/apps/truelayer-firefly/data` → Adjust to your TrueNAS pool path
- Example: `/mnt/tank/apps/truelayer-firefly/data`

### 5. Create Storage Directory

Before deploying, create the data directory on TrueNAS:

1. Open TrueNAS Shell or SSH
2. Run:
```bash
mkdir -p /mnt/your-pool/apps/truelayer-firefly/data
chmod 755 /mnt/your-pool/apps/truelayer-firefly/data
```

### 6. Deploy the Stack

1. Click **"Save"** in Dockge
2. Click **"Start"** to deploy the container
3. Wait for the container to start (check logs for any errors)

### 7. Access the Web UI

1. Open your browser
2. Navigate to: `http://your-truenas-ip:5000`
3. You should see the TrueLayer → Firefly III dashboard

### 8. Initial Configuration

#### Configure Firefly III

1. Go to **Settings**
2. Enter your Firefly III URL
   - If Firefly is on the same server: `http://firefly-container-name:8080`
   - If external: `https://your-firefly-domain.com`
3. Enter your Firefly III Personal Access Token
   - Get this from Firefly III: Profile → OAuth → Personal Access Tokens
4. Click **Test Connection**
5. Click **Save Configuration**

#### Add Providers

1. Go to **Providers**
2. Click **Add Provider**
3. For each bank/card:
   - Name: e.g., "Lloyds", "AmEx", "Revolut"
   - Account Type: Bank Accounts or Cards
   - Refresh Token: Obtain from TrueLayer Console
4. Click **Add Provider**

#### Run First Sync

1. Return to **Dashboard**
2. Click **Sync Now**
3. Check Firefly III for imported transactions

## Network Configuration

### Access from Outside TrueNAS

If you want to access the UI from outside your network:

1. **Option 1: Use TrueNAS Built-in Reverse Proxy**
   - Configure in TrueNAS → Network → Reverse Proxy
   - Add entry for port 5000

2. **Option 2: Use Nginx Proxy Manager**
   - Install Nginx Proxy Manager from TrueNAS apps
   - Create proxy host for `truelayer-firefly:5000`

3. **Option 3: Use Traefik**
   - Add Traefik labels to docker-compose.yml
   - Configure SSL certificates

### Connecting to Firefly III on Same Server

If Firefly III is running in Docker on the same TrueNAS server:

1. Create a Docker network (recommended):
```yaml
networks:
  finance:
    external: true

services:
  truelayer-firefly:
    # ... other config ...
    networks:
      - finance
```

2. Or use container name directly:
   - In Settings, use: `http://firefly-container-name:8080`

## Maintenance

### Viewing Logs

In Dockge:
1. Click on your stack
2. View the **Logs** tab
3. Look for sync activity and errors

### Updating

To update to a new version:
1. Stop the container in Dockge
2. Pull new image or rebuild
3. Start the container

### Backup

Important files to backup:
```
/mnt/your-pool/apps/truelayer-firefly/data/app.db
```

Create a TrueNAS backup task:
1. System → Cloud Sync Tasks
2. Or manually copy the file regularly

### Troubleshooting

**Container won't start:**
- Check Dockge logs
- Verify environment variables are set
- Ensure data directory exists and has correct permissions

**Can't access web UI:**
- Check port 5000 is not in use
- Verify firewall settings on TrueNAS
- Check container is running in Dockge

**Firefly connection fails:**
- Verify Firefly III is accessible from the container
- Check Personal Access Token is valid
- Try using IP address instead of hostname

**Sync errors:**
- Check TrueLayer credentials are correct
- Verify refresh tokens are still valid
- Check Dockge logs for detailed error messages

## Advanced: Using with Firefly III Data Importer

If you also use Firefly III Data Importer:

1. This integration complements Data Importer
2. Use TrueLayer integration for supported banks
3. Use Data Importer for CSV imports from unsupported banks
4. Both can run simultaneously without conflicts

## Security Recommendations

1. **Change default port** if exposed to internet
2. **Use reverse proxy** with SSL/TLS
3. **Enable authentication** via reverse proxy
4. **Regular backups** of database
5. **Monitor logs** for suspicious activity
6. **Rotate secrets** periodically

## Support

If you encounter issues:

1. Check Dockge logs
2. Review README.md for troubleshooting section
3. Verify all prerequisites are met
4. Check GitHub issues for similar problems
