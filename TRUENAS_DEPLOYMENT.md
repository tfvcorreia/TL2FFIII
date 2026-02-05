# TrueNAS Scale Deployment Guide

Quick guide for deploying TrueLayer to Firefly III integration on TrueNAS Scale using Dockge.

## Prerequisites

- TrueNAS Scale installed and running
- Dockge installed (from TrueNAS Apps or manually)
- Firefly III already running (optional, can be on different server)
- TrueLayer API credentials

## Step-by-Step Deployment

### 1. Prepare Your Credentials

Before starting, gather:

- ✅ TrueLayer Client ID
- ✅ TrueLayer Client Secret
- ✅ TrueLayer access tokens for each bank (see below)
- ✅ Firefly III URL
- ✅ Firefly III Personal Access Token

### 2. Get TrueLayer Access Tokens

For each bank/card you want to connect:

1. Go to [TrueLayer Console](https://console.truelayer.com/)
2. Navigate to your application
3. Use "Test Data Provider" or "Auth Flow" tool
4. Select your bank (Lloyds, AmEx, Revolut, etc.)
5. Complete authorization
6. Copy the `access_token` and `refresh_token`
7. Save these somewhere safe (you'll paste them in the UI later)

**Note:** You only need to do this once per bank. The app will handle token refreshes automatically.

### 3. Access Dockge

1. Open TrueNAS Scale web interface
2. Navigate to Applications
3. Find and open Dockge
4. Click "Compose" → "Create Stack"

### 4. Create Stack in Dockge

**Stack Name:** `truelayer-firefly`

**Compose Configuration:**

```yaml
version: '3.8'

services:
  truelayer-firefly:
    image: ghcr.io/yourusername/truelayer-firefly:latest  # Or build locally
    container_name: truelayer-firefly
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      # TrueLayer Configuration
      - TRUELAYER_CLIENT_ID=your-client-id-here
      - TRUELAYER_CLIENT_SECRET=your-client-secret-here
      
      # Firefly III Configuration
      - FIREFLY_URL=http://firefly-service:8080
      - FIREFLY_TOKEN=your-firefly-pat-here
      
      # Database
      - DATABASE_URL=sqlite:////app/data/truelayer_firefly.db
      
      # Application Settings
      - SYNC_INTERVAL_MINUTES=60
      - SECRET_KEY=change-this-to-random-string
      - DEBUG=false
      - TIMEZONE=Europe/London
    
    volumes:
      - /mnt/tank/apps/truelayer-firefly/data:/app/data
    
    networks:
      - firefly-network

networks:
  firefly-network:
    external: true  # If Firefly is on same network
    # OR
    # driver: bridge  # If standalone
```

### 5. Configure Environment Variables

Replace the following in the compose file:

| Variable | Where to Get It |
|----------|----------------|
| `TRUELAYER_CLIENT_ID` | TrueLayer Console → Your App |
| `TRUELAYER_CLIENT_SECRET` | TrueLayer Console → Your App |
| `FIREFLY_URL` | Your Firefly III URL (check other containers) |
| `FIREFLY_TOKEN` | Firefly III → Profile → OAuth → Create Token |
| `SECRET_KEY` | Generate: `openssl rand -hex 32` |

### 6. Configure Storage Path

Update the volume path to match your TrueNAS pool:

```yaml
volumes:
  - /mnt/YOUR-POOL/apps/truelayer-firefly/data:/app/data
```

Create this directory:
```bash
# SSH into TrueNAS or use Shell
mkdir -p /mnt/YOUR-POOL/apps/truelayer-firefly/data
chmod 755 /mnt/YOUR-POOL/apps/truelayer-firefly/data
```

### 7. Network Configuration

**Option A: Same Network as Firefly III**
```yaml
networks:
  firefly-network:
    external: true
```

**Option B: Standalone**
```yaml
networks:
  truelayer-net:
    driver: bridge
```

**Option C: Access Firefly on Another Server**
```yaml
# No network needed, just use full URL
environment:
  - FIREFLY_URL=http://192.168.1.100:8080
```

### 8. Deploy the Stack

1. Click "Deploy" in Dockge
2. Wait for container to start
3. Check logs for any errors

### 9. Access the Web UI

Open in browser:
```
http://your-truenas-ip:8000
```

### 10. Add Your Providers

In the web UI:

1. Click "Add Provider"
2. Fill in details:
   - **Name:** "Lloyds" (or whatever you want)
   - **Type:** "Bank Accounts" or "Credit Cards"
   - **Access Token:** Paste from TrueLayer
   - **Refresh Token:** Paste from TrueLayer
3. Click "Add Provider"
4. Repeat for each bank/card

### 11. Initial Sync

1. Click "Sync All Now"
2. Check "Recent Sync Logs" for results
3. Verify transactions appear in Firefly III

## Networking Tips

### Finding Firefly III Service Name

If Firefly is running in TrueNAS:

```bash
# SSH into TrueNAS
docker ps | grep firefly

# Note the container name, use it in FIREFLY_URL
# Example: http://firefly-app:8080
```

### Using Custom Network

If both are on same custom network:

```bash
# Create network (if needed)
docker network create firefly-network

# Add to both services
docker network connect firefly-network firefly-app
docker network connect firefly-network truelayer-firefly
```

## Storage Management

### Backup Database

```bash
# From TrueNAS shell
cp /mnt/YOUR-POOL/apps/truelayer-firefly/data/truelayer_firefly.db \
   /mnt/YOUR-POOL/backups/truelayer-firefly-$(date +%Y%m%d).db
```

### Restore Database

```bash
cp /mnt/YOUR-POOL/backups/truelayer-firefly-YYYYMMDD.db \
   /mnt/YOUR-POOL/apps/truelayer-firefly/data/truelayer_firefly.db

# Restart container
docker restart truelayer-firefly
```

### View Database

```bash
# Install sqlite3 if needed
apt-get install sqlite3

# Open database
sqlite3 /mnt/YOUR-POOL/apps/truelayer-firefly/data/truelayer_firefly.db

# View providers
SELECT * FROM providers;

# View sync state
SELECT * FROM sync_state;

# Exit
.quit
```

## Monitoring

### View Logs

In Dockge:
1. Click on your stack
2. Click "Logs" tab
3. Watch real-time logs

Or via CLI:
```bash
docker logs -f truelayer-firefly
```

### Check Status

```bash
# Container status
docker ps | grep truelayer

# Health check
curl http://localhost:8000/health
```

## Troubleshooting

### Container Won't Start

1. Check logs in Dockge
2. Verify all environment variables are set
3. Check storage path exists and has permissions
4. Ensure port 8000 is not in use

### Can't Connect to Firefly

1. Test from container:
```bash
docker exec truelayer-firefly curl http://firefly-app:8080/api/v1/about
```

2. Check network connectivity
3. Verify Firefly token is valid

### Database Permission Error

```bash
# Fix permissions
chown -R 1000:1000 /mnt/YOUR-POOL/apps/truelayer-firefly/data
chmod -R 755 /mnt/YOUR-POOL/apps/truelayer-firefly/data
```

### Token Refresh Fails

1. Verify CLIENT_ID and CLIENT_SECRET are correct
2. Check TrueLayer Console for app status
3. Re-authorize provider if needed

## Updating the App

### Pull New Version

If using pre-built image:

1. In Dockge, edit stack
2. Update image tag to latest
3. Click "Update"

### Build from Source

If building locally:

1. SSH into TrueNAS
2. Pull new code:
```bash
cd /path/to/truelayer-firefly
git pull
```

3. Rebuild in Dockge or:
```bash
docker-compose build
docker-compose up -d
```

## Security Recommendations

1. **Use HTTPS:** Put behind reverse proxy (Nginx Proxy Manager)
2. **Firewall:** Only expose port 8000 to local network
3. **Backups:** Regular database backups
4. **Tokens:** Keep .env secure, never commit to git
5. **Updates:** Keep TrueNAS and Docker updated

## Performance Tuning

For many transactions:

```yaml
environment:
  # Sync less frequently
  - SYNC_INTERVAL_MINUTES=120
  
  # Use PostgreSQL instead of SQLite
  - DATABASE_URL=postgresql://user:pass@postgres:5432/db
```

## Integration with Other Apps

### Notifications (Optional)

Add ntfy or other notification service:

```yaml
# Add to docker-compose.yml
- NTFY_URL=http://ntfy:8080/truelayer-sync
```

Then modify `app/main.py` to send notifications on sync completion.

### Dashboard (Optional)

- Access metrics at `/api/sync/status`
- Integrate with Homer, Dashy, or similar

---

**Need Help?**

- Check logs first: `docker logs truelayer-firefly`
- Review README.md troubleshooting section
- Open GitHub issue with logs and config (redact tokens!)
