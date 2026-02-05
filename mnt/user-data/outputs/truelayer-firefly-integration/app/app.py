from flask import Flask, render_template, request, jsonify, redirect, url_for
import requests
import json
import os
from datetime import datetime, timedelta
import logging
from threading import Thread
import time

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
DATA_DIR = os.getenv('DATA_DIR', '/data')
PROVIDERS_FILE = os.path.join(DATA_DIR, 'providers.json')
CONFIG_FILE = os.path.join(DATA_DIR, 'config.json')
SYNC_STATE_FILE = os.path.join(DATA_DIR, 'sync_state.json')

# TrueLayer API
TOKEN_URL = "https://auth.truelayer.com/connect/token"
DATA_API_BASE = "https://api.truelayer.com/data/v1"


# ===================================================================
# DATA PERSISTENCE
# ===================================================================

def load_json(filepath, default=None):
    """Load JSON file with fallback to default"""
    if default is None:
        default = {}
    if not os.path.exists(filepath):
        return default
    try:
        with open(filepath, 'r') as f:
            content = f.read().strip()
            return json.loads(content) if content else default
    except Exception as e:
        logger.error(f"Error loading {filepath}: {e}")
        return default


def save_json(filepath, data):
    """Save data to JSON file"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)


def load_providers():
    """Load provider configurations"""
    return load_json(PROVIDERS_FILE, {})


def save_providers(providers):
    """Save provider configurations"""
    save_json(PROVIDERS_FILE, providers)


def load_config():
    """Load Firefly III configuration"""
    return load_json(CONFIG_FILE, {
        'firefly_url': '',
        'firefly_token': '',
        'sync_interval': 3600,  # 1 hour default
        'auto_sync': False
    })


def save_config(config):
    """Save Firefly III configuration"""
    save_json(CONFIG_FILE, config)


def load_sync_state():
    """Load sync state for incremental updates"""
    return load_json(SYNC_STATE_FILE, {})


def save_sync_state(state):
    """Save sync state"""
    save_json(SYNC_STATE_FILE, state)


# ===================================================================
# TRUELAYER API FUNCTIONS
# ===================================================================

def refresh_access_token(client_id, client_secret, refresh_token):
    """Refresh TrueLayer access token"""
    try:
        response = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token
            },
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        if "access_token" not in data:
            raise Exception(f"Token refresh failed: {data}")
        
        return data["access_token"], data.get("refresh_token", refresh_token)
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise


def get_truelayer_accounts(access_token, account_type="accounts"):
    """Fetch accounts or cards from TrueLayer"""
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(
            f"{DATA_API_BASE}/{account_type}",
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        return data.get("results", [])
    except Exception as e:
        logger.error(f"Error fetching accounts: {e}")
        return []


def get_truelayer_transactions(access_token, account_type, account_id, from_date=None):
    """Fetch transactions from TrueLayer"""
    try:
        headers = {"Authorization": f"Bearer {access_token}"}
        url = f"{DATA_API_BASE}/{account_type}/{account_id}/transactions"
        
        if from_date:
            url += f"?from={from_date}"
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data.get("results", [])
    except Exception as e:
        logger.error(f"Error fetching transactions: {e}")
        return []


# ===================================================================
# FIREFLY III API FUNCTIONS
# ===================================================================

def create_firefly_account(firefly_url, firefly_token, account_data):
    """Create or get Firefly III account"""
    headers = {
        "Authorization": f"Bearer {firefly_token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # Check if account exists
    try:
        search_url = f"{firefly_url}/api/v1/search/accounts"
        params = {"query": account_data["name"]}
        response = requests.get(search_url, headers=headers, params=params, timeout=30)
        
        if response.status_code == 200:
            results = response.json().get("data", [])
            for result in results:
                if result.get("attributes", {}).get("name") == account_data["name"]:
                    return result["id"]
    except Exception as e:
        logger.warning(f"Error searching for account: {e}")
    
    # Create new account
    try:
        url = f"{firefly_url}/api/v1/accounts"
        payload = {
            "name": account_data["name"],
            "type": account_data.get("type", "asset"),
            "account_role": account_data.get("account_role", "defaultAsset"),
            "currency_code": account_data.get("currency", "GBP"),
            "active": True,
            "notes": account_data.get("notes", "")
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()["data"]["id"]
    except Exception as e:
        logger.error(f"Error creating Firefly account: {e}")
        return None


def create_firefly_transaction(firefly_url, firefly_token, transaction_data):
    """Create transaction in Firefly III"""
    headers = {
        "Authorization": f"Bearer {firefly_token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    try:
        url = f"{firefly_url}/api/v1/transactions"
        response = requests.post(url, headers=headers, json=transaction_data, timeout=30)
        response.raise_for_status()
        return response.json()["data"]["id"]
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 422:
            # Transaction might already exist
            logger.warning(f"Transaction already exists or validation error: {e.response.text}")
            return None
        logger.error(f"Error creating transaction: {e.response.text}")
        return None
    except Exception as e:
        logger.error(f"Error creating transaction: {e}")
        return None


def transform_to_firefly_transaction(tx, source_account_id, provider_name, account_name):
    """Transform TrueLayer transaction to Firefly III format"""
    amount = abs(float(tx.get("amount", 0)))
    transaction_type = tx.get("transaction_type", "debit")
    
    # Determine transaction type for Firefly
    if transaction_type == "credit":
        firefly_type = "deposit"
        source_name = tx.get("description", "Unknown source")
        destination_id = source_account_id
    else:
        firefly_type = "withdrawal"
        source_id = source_account_id
        destination_name = tx.get("description", "Unknown destination")
    
    transaction = {
        "error_if_duplicate_hash": True,
        "apply_rules": True,
        "transactions": [{
            "type": firefly_type,
            "date": tx.get("timestamp", datetime.now().isoformat()),
            "amount": str(amount),
            "description": tx.get("description", "TrueLayer transaction"),
            "currency_code": tx.get("currency", "GBP"),
            "category_name": tx.get("transaction_category"),
            "external_id": tx.get("transaction_id"),
            "notes": f"Provider: {provider_name}\nAccount: {account_name}\nOriginal ID: {tx.get('provider_transaction_id', 'N/A')}"
        }]
    }
    
    # Set source/destination
    if firefly_type == "deposit":
        transaction["transactions"][0]["source_name"] = source_name
        transaction["transactions"][0]["destination_id"] = str(destination_id)
    else:
        transaction["transactions"][0]["source_id"] = str(source_id)
        transaction["transactions"][0]["destination_name"] = destination_name
    
    return transaction


# ===================================================================
# SYNC LOGIC
# ===================================================================

def sync_provider(provider_name, provider_data):
    """Sync a single provider to Firefly III"""
    logger.info(f"Syncing provider: {provider_name}")
    
    config = load_config()
    firefly_url = config.get('firefly_url', '').rstrip('/')
    firefly_token = config.get('firefly_token', '')
    
    if not firefly_url or not firefly_token:
        logger.error("Firefly III not configured")
        return {"error": "Firefly III not configured", "synced": 0}
    
    try:
        # Refresh access token
        access_token, new_refresh = refresh_access_token(
            provider_data['client_id'],
            provider_data['client_secret'],
            provider_data['refresh_token']
        )
        
        # Update refresh token
        providers = load_providers()
        providers[provider_name]['refresh_token'] = new_refresh
        save_providers(providers)
        
        # Get accounts
        account_type = provider_data.get('type', 'accounts')
        accounts = get_truelayer_accounts(access_token, account_type)
        
        if not accounts:
            logger.warning(f"No accounts found for {provider_name}")
            return {"error": "No accounts found", "synced": 0}
        
        sync_state = load_sync_state()
        total_synced = 0
        
        for account in accounts:
            account_id = account.get("account_id")
            account_name = account.get("display_name", f"{provider_name}_account")
            
            logger.info(f"Processing account: {account_name}")
            
            # Create or get Firefly account
            firefly_account_id = create_firefly_account(
                firefly_url,
                firefly_token,
                {
                    "name": f"{provider_name} - {account_name}",
                    "type": "asset",
                    "currency": account.get("currency", "GBP"),
                    "notes": f"TrueLayer Account ID: {account_id}"
                }
            )
            
            if not firefly_account_id:
                logger.error(f"Failed to create Firefly account for {account_name}")
                continue
            
            # Get last sync timestamp
            state_key = f"{provider_name}_{account_id}"
            last_sync = sync_state.get(state_key)
            
            # Fetch transactions
            transactions = get_truelayer_transactions(
                access_token,
                account_type,
                account_id,
                last_sync
            )
            
            logger.info(f"Found {len(transactions)} transactions for {account_name}")
            
            for tx in transactions:
                firefly_tx = transform_to_firefly_transaction(
                    tx,
                    firefly_account_id,
                    provider_name,
                    account_name
                )
                
                tx_id = create_firefly_transaction(firefly_url, firefly_token, firefly_tx)
                if tx_id:
                    total_synced += 1
            
            # Update sync state
            if transactions:
                newest_ts = max(tx["timestamp"] for tx in transactions)
                sync_state[state_key] = newest_ts
        
        save_sync_state(sync_state)
        logger.info(f"Synced {total_synced} transactions from {provider_name}")
        
        return {"synced": total_synced}
        
    except Exception as e:
        logger.error(f"Error syncing {provider_name}: {e}")
        return {"error": str(e), "synced": 0}


def sync_all_providers():
    """Sync all providers to Firefly III"""
    providers = load_providers()
    results = {}
    
    for provider_name, provider_data in providers.items():
        results[provider_name] = sync_provider(provider_name, provider_data)
    
    return results


# ===================================================================
# BACKGROUND SYNC
# ===================================================================

def background_sync_task():
    """Background task for automatic syncing"""
    while True:
        config = load_config()
        if config.get('auto_sync', False):
            logger.info("Running automatic sync...")
            sync_all_providers()
        
        interval = config.get('sync_interval', 3600)
        time.sleep(interval)


# Start background sync thread
sync_thread = Thread(target=background_sync_task, daemon=True)
sync_thread.start()


# ===================================================================
# WEB ROUTES
# ===================================================================

@app.route('/')
def index():
    """Main dashboard"""
    providers = load_providers()
    config = load_config()
    return render_template('index.html', providers=providers, config=config)


@app.route('/api/providers', methods=['GET'])
def get_providers():
    """Get all providers"""
    return jsonify(load_providers())


@app.route('/api/providers', methods=['POST'])
def add_provider():
    """Add or update provider"""
    data = request.json
    
    provider_name = data.get('name')
    if not provider_name:
        return jsonify({"error": "Provider name required"}), 400
    
    providers = load_providers()
    providers[provider_name] = {
        "client_id": data.get('client_id'),
        "client_secret": data.get('client_secret'),
        "refresh_token": data.get('refresh_token'),
        "type": data.get('type', 'accounts')
    }
    save_providers(providers)
    
    return jsonify({"message": "Provider saved successfully"})


@app.route('/api/providers/<provider_name>', methods=['DELETE'])
def delete_provider(provider_name):
    """Delete a provider"""
    providers = load_providers()
    if provider_name in providers:
        del providers[provider_name]
        save_providers(providers)
        return jsonify({"message": "Provider deleted"})
    return jsonify({"error": "Provider not found"}), 404


@app.route('/api/config', methods=['GET'])
def get_config():
    """Get Firefly III configuration"""
    return jsonify(load_config())


@app.route('/api/config', methods=['POST'])
def save_config_route():
    """Save Firefly III configuration"""
    data = request.json
    config = load_config()
    
    config['firefly_url'] = data.get('firefly_url', '').rstrip('/')
    config['firefly_token'] = data.get('firefly_token', '')
    config['sync_interval'] = int(data.get('sync_interval', 3600))
    config['auto_sync'] = data.get('auto_sync', False)
    
    save_config(config)
    return jsonify({"message": "Configuration saved"})


@app.route('/api/sync', methods=['POST'])
def manual_sync():
    """Trigger manual sync"""
    provider_name = request.json.get('provider')
    
    if provider_name:
        providers = load_providers()
        if provider_name not in providers:
            return jsonify({"error": "Provider not found"}), 404
        result = sync_provider(provider_name, providers[provider_name])
    else:
        result = sync_all_providers()
    
    return jsonify(result)


@app.route('/api/test-firefly', methods=['POST'])
def test_firefly():
    """Test Firefly III connection"""
    config = load_config()
    firefly_url = config.get('firefly_url', '').rstrip('/')
    firefly_token = config.get('firefly_token', '')
    
    if not firefly_url or not firefly_token:
        return jsonify({"error": "Firefly III not configured"}), 400
    
    try:
        headers = {
            "Authorization": f"Bearer {firefly_token}",
            "Accept": "application/json"
        }
        response = requests.get(f"{firefly_url}/api/v1/about", headers=headers, timeout=10)
        response.raise_for_status()
        return jsonify({"success": True, "data": response.json()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
