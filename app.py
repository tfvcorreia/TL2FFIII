import os
import json
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import requests
from database import Database
from truelayer_client import TrueLayerClient
from firefly_client import FireflyClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-me')

# Initialize database
db = Database()

# Initialize scheduler
scheduler = BackgroundScheduler()


def sync_transactions():
    """Background job to sync transactions from TrueLayer to Firefly III"""
    logger.info("Starting scheduled transaction sync...")
    
    try:
        providers = db.get_all_providers()
        
        if not providers:
            logger.info("No providers configured, skipping sync")
            return
        
        # Get Firefly III configuration
        firefly_config = db.get_firefly_config()
        if not firefly_config:
            logger.warning("Firefly III not configured, skipping sync")
            return
        
        firefly_client = FireflyClient(
            firefly_config['url'],
            firefly_config['token']
        )
        
        total_synced = 0
        
        for provider in providers:
            try:
                logger.info(f"Syncing provider: {provider['name']}")
                
                # Initialize TrueLayer client
                tl_client = TrueLayerClient(
                    client_id=os.environ.get('TRUELAYER_CLIENT_ID'),
                    client_secret=os.environ.get('TRUELAYER_CLIENT_SECRET')
                )
                
                # Refresh access token
                access_token = tl_client.refresh_token(provider['refresh_token'])
                
                # Update refresh token if it changed
                if access_token['refresh_token'] != provider['refresh_token']:
                    db.update_provider_refresh_token(
                        provider['id'],
                        access_token['refresh_token']
                    )
                
                # Get accounts
                accounts = tl_client.get_accounts(
                    access_token['access_token'],
                    provider['account_type']
                )
                
                for account in accounts:
                    account_id = account.get('account_id')
                    display_name = account.get('display_name', f"{provider['name']}_account")
                    
                    logger.info(f"Processing account: {display_name}")
                    
                    # Get last sync timestamp
                    last_sync = db.get_last_sync(provider['id'], account_id)
                    
                    # Fetch transactions
                    transactions = tl_client.get_transactions(
                        access_token['access_token'],
                        provider['account_type'],
                        account_id,
                        from_timestamp=last_sync
                    )
                    
                    if not transactions:
                        logger.info(f"No new transactions for {display_name}")
                        continue
                    
                    logger.info(f"Found {len(transactions)} new transactions")
                    
                    # Transform and send to Firefly III
                    for tx in transactions:
                        try:
                            # Map account to Firefly III account
                            firefly_account_id = db.get_firefly_account_mapping(
                                provider['id'],
                                account_id
                            )
                            
                            if not firefly_account_id:
                                logger.warning(
                                    f"No Firefly III account mapped for {display_name}, "
                                    "using default asset account"
                                )
                                firefly_account_id = None
                            
                            # Create transaction in Firefly III
                            firefly_client.create_transaction(
                                tx,
                                firefly_account_id,
                                provider['name'],
                                display_name
                            )
                            
                            total_synced += 1
                            
                        except Exception as e:
                            logger.error(f"Error processing transaction: {e}")
                            continue
                    
                    # Update last sync timestamp
                    if transactions:
                        newest_ts = max(tx['timestamp'] for tx in transactions)
                        db.update_last_sync(provider['id'], account_id, newest_ts)
                
                # Update last sync time for provider
                db.update_provider_last_sync(provider['id'])
                
            except Exception as e:
                logger.error(f"Error syncing provider {provider['name']}: {e}")
                continue
        
        logger.info(f"Sync completed. Total transactions synced: {total_synced}")
        
    except Exception as e:
        logger.error(f"Error in sync_transactions: {e}")


# Routes
@app.route('/')
def index():
    """Main dashboard"""
    providers = db.get_all_providers()
    firefly_config = db.get_firefly_config()
    sync_status = db.get_sync_status()
    
    return render_template(
        'index.html',
        providers=providers,
        firefly_configured=firefly_config is not None,
        sync_status=sync_status
    )


@app.route('/providers')
def providers():
    """Provider management page"""
    providers = db.get_all_providers()
    return render_template('providers.html', providers=providers)


@app.route('/api/providers', methods=['GET'])
def get_providers():
    """Get all providers"""
    providers = db.get_all_providers()
    return jsonify(providers)


@app.route('/api/providers', methods=['POST'])
def add_provider():
    """Add a new provider"""
    data = request.json
    
    required_fields = ['name', 'refresh_token', 'account_type']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        provider_id = db.add_provider(
            name=data['name'],
            refresh_token=data['refresh_token'],
            account_type=data['account_type']
        )
        
        return jsonify({
            'success': True,
            'provider_id': provider_id,
            'message': f"Provider '{data['name']}' added successfully"
        })
    
    except Exception as e:
        logger.error(f"Error adding provider: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/providers/<int:provider_id>', methods=['DELETE'])
def delete_provider(provider_id):
    """Delete a provider"""
    try:
        db.delete_provider(provider_id)
        return jsonify({'success': True, 'message': 'Provider deleted'})
    except Exception as e:
        logger.error(f"Error deleting provider: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/firefly/config', methods=['GET'])
def get_firefly_config():
    """Get Firefly III configuration"""
    config = db.get_firefly_config()
    
    if config:
        # Don't send the full token to the client
        return jsonify({
            'url': config['url'],
            'configured': True
        })
    
    return jsonify({'configured': False})


@app.route('/api/firefly/config', methods=['POST'])
def save_firefly_config():
    """Save Firefly III configuration"""
    data = request.json
    
    if not data.get('url') or not data.get('token'):
        return jsonify({'error': 'URL and token are required'}), 400
    
    try:
        # Validate connection
        firefly_client = FireflyClient(data['url'], data['token'])
        about = firefly_client.test_connection()
        
        # Save configuration
        db.save_firefly_config(data['url'], data['token'])
        
        return jsonify({
            'success': True,
            'message': 'Firefly III configured successfully',
            'version': about.get('version', 'unknown')
        })
    
    except Exception as e:
        logger.error(f"Error configuring Firefly III: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/sync/manual', methods=['POST'])
def manual_sync():
    """Trigger manual sync"""
    try:
        sync_transactions()
        return jsonify({'success': True, 'message': 'Sync completed'})
    except Exception as e:
        logger.error(f"Error in manual sync: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/sync/status', methods=['GET'])
def sync_status():
    """Get sync status"""
    status = db.get_sync_status()
    return jsonify(status)


@app.route('/settings')
def settings():
    """Settings page"""
    firefly_config = db.get_firefly_config()
    sync_schedule = os.environ.get('SYNC_SCHEDULE', '0 */6 * * *')
    
    return render_template(
        'settings.html',
        firefly_config=firefly_config,
        sync_schedule=sync_schedule
    )


if __name__ == '__main__':
    # Initialize database tables
    db.init_db()
    
    # Start scheduler for automatic syncing
    sync_schedule = os.environ.get('SYNC_SCHEDULE', '0 */6 * * *')  # Default: every 6 hours
    
    try:
        scheduler.add_job(
            func=sync_transactions,
            trigger=CronTrigger.from_crontab(sync_schedule),
            id='sync_transactions',
            name='Sync TrueLayer transactions to Firefly III',
            replace_existing=True
        )
        scheduler.start()
        logger.info(f"Scheduler started with schedule: {sync_schedule}")
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")
    
    # Run Flask app
    app.run(host='0.0.0.0', port=5000, debug=False)
