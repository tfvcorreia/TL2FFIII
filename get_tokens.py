#!/usr/bin/env python3
"""
TrueLayer Token Helper
Run this script locally to get refresh tokens for your providers.
"""

import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
import webbrowser
from urllib.parse import urlparse, parse_qs
import sys

# CONFIGURATION - Update these with your TrueLayer credentials
CLIENT_ID = "test-0f757b"  # Replace with your client ID
CLIENT_SECRET = "b8f0db76-027f-4977-ac73-e26578e2f23a"  # Replace with your client secret
REDIRECT_URI = "http://localhost:8080/callback"

# Store the authorization code
auth_code = None


class CallbackHandler(BaseHTTPRequestHandler):
    """Handle OAuth callback"""
    
    def do_GET(self):
        global auth_code
        query = parse_qs(urlparse(self.path).query)
        auth_code = query.get('code', [None])[0]
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        if auth_code:
            html = """
            <!DOCTYPE html>
            <html>
            <head><title>Authorization Complete</title></head>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1 style="color: green;">✓ Authorization Complete!</h1>
                <p>You can close this window and return to the terminal.</p>
            </body>
            </html>
            """
        else:
            html = """
            <!DOCTYPE html>
            <html>
            <head><title>Authorization Failed</title></head>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1 style="color: red;">✗ Authorization Failed</h1>
                <p>No authorization code received. Please try again.</p>
            </body>
            </html>
            """
        
        self.wfile.write(html.encode())
    
    def log_message(self, format, *args):
        """Suppress HTTP logs"""
        pass


def get_tokens(provider_name=""):
    """
    Get TrueLayer tokens through OAuth flow
    
    Args:
        provider_name: Optional name of the provider for display
    """
    global auth_code
    auth_code = None
    
    print("\n" + "="*70)
    print("TrueLayer Token Generator")
    if provider_name:
        print(f"Provider: {provider_name}")
    print("="*70)
    
    # Build authorization URL
    auth_url = (
        f"https://auth.truelayer.com/"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope=info%20accounts%20balance%20cards%20transactions%20direct_debits%20standing_orders%20offline_access"
        f"&providers=uk-ob-all"
    )
    
    print("\nStep 1: Opening browser for authorization...")
    print("         You'll be asked to select your bank and authorize access.")
    print("\n         NOTE: Make sure to select 'offline_access' for refresh tokens!")
    
    try:
        webbrowser.open(auth_url)
    except Exception as e:
        print(f"\nCouldn't open browser automatically. Please open this URL manually:")
        print(f"\n{auth_url}\n")
    
    # Start callback server
    print("\nStep 2: Waiting for authorization callback...")
    print("         (A local server is listening on port 8080)")
    
    try:
        server = HTTPServer(('localhost', 8080), CallbackHandler)
        server.handle_request()
        server.server_close()
    except OSError as e:
        print(f"\n✗ Error: Port 8080 is already in use!")
        print(f"  Please close any application using this port and try again.")
        return False
    
    if not auth_code:
        print("\n✗ Error: No authorization code received")
        print("  Please try again and make sure you complete the authorization.")
        return False
    
    # Exchange authorization code for tokens
    print("\nStep 3: Exchanging authorization code for tokens...")
    
    try:
        response = requests.post(
            "https://auth.truelayer.com/connect/token",
            data={
                "grant_type": "authorization_code",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uri": REDIRECT_URI,
                "code": auth_code
            },
            timeout=30
        )
        
        response.raise_for_status()
        tokens = response.json()
        
    except requests.exceptions.RequestException as e:
        print(f"\n✗ Error exchanging code for tokens: {e}")
        return False
    
    # Display results
    print("\n" + "="*70)
    print("✓ SUCCESS! Save these tokens in your web UI:")
    print("="*70)
    
    if 'access_token' in tokens:
        print(f"\n📋 Refresh Token (use this in the web UI):")
        print(f"   {tokens['refresh_token']}")
        print(f"\n⏱  Access Token (temporary, expires in {tokens.get('expires_in', 'unknown')}s):")
        print(f"   {tokens['access_token'][:50]}...")
    else:
        print(f"\n✗ Error in token response:")
        print(f"   {tokens}")
        return False
    
    print("\n" + "="*70)
    print("\nNext steps:")
    print("1. Copy the REFRESH TOKEN above")
    print("2. Go to your web UI (http://your-server:5000)")
    print("3. Click 'Add Provider'")
    print("4. Paste the refresh token")
    print("5. Fill in the other fields:")
    print(f"   - Client ID: {CLIENT_ID}")
    print(f"   - Client Secret: {CLIENT_SECRET}")
    if provider_name:
        print(f"   - Provider Name: {provider_name}")
    print("="*70 + "\n")
    
    return True


def main():
    """Main entry point"""
    
    print("\n" + "="*70)
    print("TrueLayer Token Helper")
    print("="*70)
    print("\nThis script will help you obtain refresh tokens for your bank accounts.")
    print("You'll need to run this once for each bank/provider you want to connect.")
    print("\nMake sure you have:")
    print("  ✓ A TrueLayer application (get one at https://console.truelayer.com/)")
    print("  ✓ Your Client ID and Client Secret")
    print("  ✓ Added 'http://localhost:8080/callback' as a redirect URI")
    
    # Check if credentials are set
    if CLIENT_ID == "your-client-id-here" or CLIENT_SECRET == "your-client-secret-here":
        print("\n✗ Error: Please edit this script and add your TrueLayer credentials!")
        print("  Update CLIENT_ID and CLIENT_SECRET at the top of the file.")
        sys.exit(1)
    
    print("\n" + "-"*70)
    
    # Get provider name
    provider_name = input("\nEnter provider name (e.g., 'Lloyds', 'AmEx', 'Revolut'): ").strip()
    
    if not provider_name:
        provider_name = "Provider"
    
    # Run OAuth flow
    success = get_tokens(provider_name)
    
    if success:
        # Ask if user wants to add another
        another = input("\nDo you want to add another provider? (y/n): ").strip().lower()
        if another == 'y':
            main()
    else:
        print("\n✗ Failed to get tokens. Please try again.\n")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✗ Cancelled by user\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}\n")
        sys.exit(1)
