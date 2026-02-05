import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class FireflyClient:
    def __init__(self, url, token):
        self.url = url.rstrip('/')
        self.token = token
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def test_connection(self):
        """Test connection to Firefly III"""
        try:
            response = requests.get(
                f"{self.url}/api/v1/about",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Connected to Firefly III v{data.get('data', {}).get('version', 'unknown')}")
            
            return data.get('data', {})
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Error connecting to Firefly III: {e}")
            raise Exception(f"Failed to connect to Firefly III: {str(e)}")
    
    def get_accounts(self, account_type='asset'):
        """Get all accounts of a specific type"""
        try:
            response = requests.get(
                f"{self.url}/api/v1/accounts",
                headers=self.headers,
                params={'type': account_type},
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            accounts = data.get('data', [])
            
            logger.info(f"Retrieved {len(accounts)} {account_type} accounts")
            return accounts
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching accounts: {e}")
            raise
    
    def create_transaction(self, truelayer_transaction, firefly_account_id, provider_name, account_name):
        """Create a transaction in Firefly III from TrueLayer transaction"""
        try:
            # Parse TrueLayer transaction
            amount = abs(float(truelayer_transaction.get('amount', 0)))
            description = truelayer_transaction.get('description', 'Unknown transaction')
            timestamp = truelayer_transaction.get('timestamp')
            currency = truelayer_transaction.get('currency', 'GBP')
            transaction_type = truelayer_transaction.get('transaction_type', '').lower()
            category = truelayer_transaction.get('transaction_category', '')
            
            # Parse timestamp
            try:
                if timestamp:
                    # TrueLayer format: 2024-01-15T10:30:00Z
                    date = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                else:
                    date = datetime.now()
            except:
                date = datetime.now()
            
            # Determine transaction type for Firefly III
            # TrueLayer types: DEBIT, CREDIT
            if transaction_type == 'credit' or amount > 0:
                firefly_type = 'deposit'
                source_name = description  # Use description as source for deposits
                destination_id = firefly_account_id
                destination_name = account_name
            else:
                firefly_type = 'withdrawal'
                source_id = firefly_account_id
                source_name = account_name
                destination_name = description  # Use description as destination for withdrawals
            
            # Build transaction data
            transaction_data = {
                'error_if_duplicate_hash': True,
                'apply_rules': True,
                'fire_webhooks': True,
                'transactions': [
                    {
                        'type': firefly_type,
                        'date': date.strftime('%Y-%m-%dT%H:%M:%S%z'),
                        'amount': str(amount),
                        'description': description,
                        'currency_code': currency,
                        'external_id': truelayer_transaction.get('transaction_id', ''),
                        'notes': f"Imported from TrueLayer ({provider_name})",
                        'tags': [provider_name, 'truelayer-import']
                    }
                ]
            }
            
            # Add source/destination based on type
            if firefly_type == 'deposit':
                transaction_data['transactions'][0]['source_name'] = source_name
                if destination_id:
                    transaction_data['transactions'][0]['destination_id'] = str(destination_id)
                else:
                    transaction_data['transactions'][0]['destination_name'] = destination_name
            else:
                if source_id:
                    transaction_data['transactions'][0]['source_id'] = str(source_id)
                else:
                    transaction_data['transactions'][0]['source_name'] = source_name
                transaction_data['transactions'][0]['destination_name'] = destination_name
            
            # Add category if available
            if category:
                transaction_data['transactions'][0]['category_name'] = category
            
            # Create transaction
            response = requests.post(
                f"{self.url}/api/v1/transactions",
                headers=self.headers,
                json=transaction_data,
                timeout=30
            )
            
            # Handle duplicate transactions gracefully
            if response.status_code == 422:
                error_data = response.json()
                if 'duplicate' in str(error_data).lower():
                    logger.debug(f"Duplicate transaction skipped: {description}")
                    return None
            
            response.raise_for_status()
            
            result = response.json()
            logger.debug(f"Created transaction: {description} ({amount} {currency})")
            
            return result
        
        except requests.exceptions.RequestException as e:
            # Don't raise on duplicates
            if hasattr(e, 'response') and e.response.status_code == 422:
                logger.debug(f"Duplicate transaction: {description}")
                return None
            
            logger.error(f"Error creating transaction: {e}")
            raise
    
    def get_or_create_account(self, account_name, account_type='asset', currency='GBP'):
        """Get existing account or create new one"""
        try:
            # Search for existing account
            accounts = self.get_accounts(account_type)
            
            for account in accounts:
                if account['attributes']['name'].lower() == account_name.lower():
                    logger.info(f"Found existing account: {account_name}")
                    return account['id']
            
            # Create new account
            account_data = {
                'name': account_name,
                'type': account_type,
                'currency_code': currency,
                'active': True,
                'notes': 'Created by TrueLayer integration'
            }
            
            response = requests.post(
                f"{self.url}/api/v1/accounts",
                headers=self.headers,
                json=account_data,
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            account_id = result['data']['id']
            logger.info(f"Created new account: {account_name} (ID: {account_id})")
            
            return account_id
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting/creating account: {e}")
            raise
