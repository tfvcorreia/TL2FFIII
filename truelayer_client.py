import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class TrueLayerClient:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = "https://auth.truelayer.com/connect/token"
        self.data_api_base = "https://api.truelayer.com/data/v1"
    
    def refresh_token(self, refresh_token):
        """Refresh access token using refresh token"""
        try:
            response = requests.post(
                self.token_url,
                data={
                    "grant_type": "refresh_token",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": refresh_token
                },
                timeout=30
            )
            
            response.raise_for_status()
            data = response.json()
            
            if "access_token" not in data:
                raise Exception(f"Token refresh failed: {data}")
            
            logger.info("Access token refreshed successfully")
            
            return {
                'access_token': data['access_token'],
                'refresh_token': data.get('refresh_token', refresh_token)
            }
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Error refreshing token: {e}")
            raise
    
    def get_accounts(self, access_token, account_type='accounts'):
        """Get all accounts for the user"""
        try:
            endpoint = 'accounts' if account_type == 'accounts' else 'cards'
            
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(
                f"{self.data_api_base}/{endpoint}",
                headers=headers,
                timeout=30
            )
            
            response.raise_for_status()
            data = response.json()
            
            if "results" not in data:
                logger.warning(f"No {endpoint} found in response")
                return []
            
            logger.info(f"Retrieved {len(data['results'])} {endpoint}")
            return data['results']
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching accounts: {e}")
            raise
    
    def get_transactions(self, access_token, account_type, account_id, from_timestamp=None, to_timestamp=None):
        """Get transactions for an account"""
        try:
            endpoint = 'accounts' if account_type == 'accounts' else 'cards'
            
            url = f"{self.data_api_base}/{endpoint}/{account_id}/transactions"
            
            # Add query parameters
            params = {}
            if from_timestamp:
                params['from'] = from_timestamp
            if to_timestamp:
                params['to'] = to_timestamp
            
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=30
            )
            
            response.raise_for_status()
            data = response.json()
            
            if "results" not in data:
                logger.warning(f"No transactions found for account {account_id}")
                return []
            
            transactions = data['results']
            logger.info(f"Retrieved {len(transactions)} transactions for account {account_id}")
            
            return transactions
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching transactions: {e}")
            raise
    
    def get_balance(self, access_token, account_type, account_id):
        """Get balance for an account"""
        try:
            endpoint = 'accounts' if account_type == 'accounts' else 'cards'
            
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(
                f"{self.data_api_base}/{endpoint}/{account_id}/balance",
                headers=headers,
                timeout=30
            )
            
            response.raise_for_status()
            data = response.json()
            
            return data.get('results', [])
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching balance: {e}")
            raise
