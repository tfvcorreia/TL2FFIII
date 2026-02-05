# TrueLayer → Firefly III Integration

A Docker-based web application for automatically syncing transactions from TrueLayer to Firefly III. Supports multiple providers (Lloyds, AmEx, Revolut, etc.) with a simple web UI for configuration.

## Features

✨ **Multi-Provider Support**: Add unlimited providers with separate access tokens  
🔄 **Automatic Syncing**: Background sync with configurable intervals  
🎨 **Modern Web UI**: Easy-to-use interface for managing providers and configuration  
🐳 **Docker Ready**: Fully containerized for easy deployment on TrueNAS Scale/Dockge  
📊 **Incremental Sync**: Only fetches new transactions since last sync  
🏦 **Auto Account Creation**: Automatically creates Firefly III accounts for each TrueLayer account  
🔐 **Secure**: Tokens stored locally in persistent volume  

## Prerequisites

1. **TrueLayer Account**: You need access tokens for each financial provider
   - Client ID
   - Client Secret
   - Refresh Token (obtained through TrueLayer OAuth flow)

2. **Firefly III Instance**: Running Firefly III with API access
   - URL of your Firefly III instance
   - Personal Access Token (generate in Firefly III → Profile → OAuth)

3. **Docker Environment**: TrueNAS Scale with Dockge or any Docker host

## Quick Start

### Option 1: Using Dockge (Recommended for TrueNAS Scale)

1. **Copy the project to your TrueNAS Scale**:
   ```bash
   # Upload the entire truelayer-firefly-integration folder to your Dockge stacks directory
   # Usually: /mnt/your-pool/dockge/stacks/truelayer-firefly-integration
   ```

2. **In Dockge**:
   - Click "Compose" → "New Stack"
   - Name it "truelayer-firefly-integration"
   - Paste the docker-compose.yml content or select the folder
   - Click "Deploy"

3. **Access the UI**:
   - Open `http://your-truenas-ip:5000`
   - Configure Firefly III settings
   - Add your providers

### Option 2: Using Docker Compose

```bash
# Clone or download the project
cd truelayer-firefly-integration

# Build and start the container
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the container
docker-compose down
```

### Option 3: Using Docker CLI

```bash
# Build the image
docker build -t truelayer-firefly .

# Run the container
docker run -d \
  --name truelayer-firefly-sync \
  -p 5000:5000 \
  -v $(pwd)/data:/data \
  -e TZ=Europe/London \
  --restart unless-stopped \
  truelayer-firefly
```

## Configuration

### 1. Configure Firefly III

In the web UI at `http://your-server:5000`:

1. Go to the "Firefly III Configuration" section
2. Enter your Firefly III URL (e.g., `https://firefly.example.com`)
3. Enter your Personal Access Token from Firefly III
4. Set sync interval in seconds (default: 3600 = 1 hour)
5. Enable/disable automatic syncing
6. Click "Save Configuration"
7. Click "Test Connection" to verify

### 2. Add Providers

1. Click "Add Provider"
2. Fill in the form:
   - **Provider Name**: e.g., "Lloyds", "AmEx", "Revolut"
   - **Client ID**: Your TrueLayer client ID
   - **Client Secret**: Your TrueLayer client secret
   - **Refresh Token**: The refresh token from TrueLayer OAuth
   - **Account Type**: "accounts" or "cards"
3. Click "Save Provider"

### 3. Getting TrueLayer Tokens

To get your TrueLayer tokens, you need to:

1. Create a TrueLayer application at https://console.truelayer.com/
2. Use the TrueLayer OAuth flow to authorize each bank
3. Exchange the authorization code for tokens
4. Use the refresh token in this application

**Helper Script** (run locally, not in Docker):

```python
# Save this as get_tokens.py and run locally
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
import webbrowser
from urllib.parse import urlparse, parse_qs

CLIENT_ID = "your-client-id"
CLIENT_SECRET = "your-client-secret"
REDIRECT_URI = "http://localhost:8080/callback"

# Store the code
auth_code = None

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        query = parse_qs(urlparse(self.path).query)
        auth_code = query.get('code', [None])[0]
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"Authorization complete! You can close this window.")
    
    def log_message(self, format, *args):
        pass  # Suppress logs

def get_tokens():
    # Step 1: Open browser for authorization
    auth_url = f"https://auth.truelayer.com/?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope=info%20accounts%20balance%20cards%20transactions%20direct_debits%20standing_orders%20offline_access&providers=uk-ob-all"
    
    print("Opening browser for authorization...")
    webbrowser.open(auth_url)
    
    # Step 2: Start callback server
    server = HTTPServer(('localhost', 8080), CallbackHandler)
    print("Waiting for callback...")
    server.handle_request()
    server.server_close()
    
    if not auth_code:
        print("Error: No authorization code received")
        return
    
    # Step 3: Exchange code for tokens
    response = requests.post(
        "https://auth.truelayer.com/connect/token",
        data={
            "grant_type": "authorization_code",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
            "code": auth_code
        }
    )
    
    tokens = response.json()
    
    print("\n" + "="*60)
    print("SUCCESS! Save these tokens:")
    print("="*60)
    print(f"Access Token: {tokens.get('access_token', 'ERROR')}")
    print(f"Refresh Token: {tokens.get('refresh_token', 'ERROR')}")
    print(f"Expires in: {tokens.get('expires_in', 'ERROR')} seconds")
    print("="*60)
    print("\nUse the REFRESH TOKEN in the web UI!")

if __name__ == "__main__":
    get_tokens()
```

## Usage

### Manual Sync

1. Go to the web UI
2. Click "Sync Now" for a specific provider
3. Or click "Sync All Providers" to sync everything

### Automatic Sync

1. Enable "Auto Sync" in the Firefly III Configuration
2. Set your desired sync interval
3. The application will automatically sync in the background

### Adding Partner Accounts

Simply add another provider with your partner's Lloyds credentials:

1. Get their TrueLayer tokens (they need to authorize it)
2. Click "Add Provider"
3. Name it "Partner-Lloyds" or similar
4. Add their tokens
5. The system will treat it as a separate provider

## Data Persistence

All configuration is stored in the `/data` directory:

- `providers.json`: Provider credentials (encrypted in storage)
- `config.json`: Firefly III configuration
- `sync_state.json`: Last sync timestamps for incremental updates

This directory is mounted as a Docker volume, so your configuration persists across container restarts.

## Troubleshooting

### Connection Issues

```bash
# Check container logs
docker logs truelayer-firefly-sync

# Test Firefly III connection manually
curl -H "Authorization: Bearer YOUR_TOKEN" https://your-firefly.com/api/v1/about
```

### Token Refresh Errors

If you see token refresh errors:
1. The refresh token may have expired
2. Get a new refresh token using the helper script above
3. Update the provider in the web UI

### Duplicate Transactions

The application uses Firefly III's duplicate detection:
- Each transaction has a unique `external_id` from TrueLayer
- Firefly III's `error_if_duplicate_hash` prevents duplicates
- If you see duplicates, check your Firefly III rules

### Port Conflicts

If port 5000 is already in use:

```yaml
# Edit docker-compose.yml
ports:
  - "5001:5000"  # Change 5001 to any free port
```

## Security Notes

1. **Store tokens securely**: The Docker volume contains sensitive tokens
2. **Use HTTPS**: Put this behind a reverse proxy with SSL (Nginx Proxy Manager, Traefik)
3. **Firewall**: Don't expose port 5000 to the internet
4. **Backups**: Backup the `/data` directory regularly

## Advanced Configuration

### Environment Variables

You can override settings via environment variables in docker-compose.yml:

```yaml
environment:
  - DATA_DIR=/data
  - TZ=Europe/London
  - FLASK_ENV=production
```

### Custom Port

```yaml
ports:
  - "8080:5000"  # Access on port 8080
```

### Behind Reverse Proxy

Example Nginx configuration:

```nginx
location /truelayer/ {
    proxy_pass http://localhost:5000/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

## API Endpoints

The application exposes a REST API:

- `GET /api/providers` - List all providers
- `POST /api/providers` - Add/update provider
- `DELETE /api/providers/<name>` - Delete provider
- `GET /api/config` - Get Firefly III config
- `POST /api/config` - Update Firefly III config
- `POST /api/sync` - Trigger manual sync
- `POST /api/test-firefly` - Test Firefly III connection

## Differences from erwindouna/truelayer2firefly

This implementation is better because:

1. ✅ **Multiple Providers**: Add unlimited providers (the original only supports one)
2. ✅ **Web UI**: No need to edit JSON files manually
3. ✅ **Partner Accounts**: Easy to add partner's accounts as separate providers
4. ✅ **Better Account Mapping**: Automatically creates Firefly III accounts
5. ✅ **Incremental Sync**: Only fetches new transactions
6. ✅ **Background Sync**: Automatic syncing with configurable intervals
7. ✅ **Modern Stack**: Uses Flask, better error handling
8. ✅ **Docker Native**: Designed for container deployment
9. ✅ **Persistent State**: Remembers sync state across restarts

## Support

If you encounter issues:

1. Check the container logs: `docker logs truelayer-firefly-sync`
2. Verify Firefly III is accessible
3. Test TrueLayer tokens are valid
4. Check the sync_state.json for errors

## License

MIT License - feel free to modify and distribute!

## Contributing

Improvements welcome! This is designed to be a simple, maintainable solution.

---

**Happy Syncing! 🚀**
