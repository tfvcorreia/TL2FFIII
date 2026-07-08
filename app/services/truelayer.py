import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from app.config import settings
from app.models import Provider, SyncState
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


class TrueLayerService:
    """Handles all TrueLayer API interactions"""
    
    def __init__(self):
        self.token_url = settings.truelayer_token_url
        self.api_base = settings.truelayer_api_base
        self.client_id = settings.truelayer_client_id
        self.client_secret = settings.truelayer_client_secret
    
    def refresh_access_token(self, refresh_token: str) -> Tuple[str, str, datetime]:
        """
        Refresh the access token using refresh token
        Returns: (access_token, refresh_token, expires_at)
        """
        response = requests.post(
            self.token_url,
            data={
                "grant_type": "refresh_token",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": refresh_token
            }
        )
        
        if response.status_code != 200:
            raise Exception(f"Token refresh failed: {response.text}")
        
        data = response.json()
        
        if "access_token" not in data:
            raise Exception(f"No access token in response: {data}")
        
        # Calculate expiration (usually 3600 seconds = 1 hour)
        expires_in = data.get("expires_in", 3600)
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        return data["access_token"], data["refresh_token"], expires_at
    
    def get_valid_token(self, db: Session, provider: Provider) -> str:
        """
        Get a valid access token, refreshing if necessary.
        Skip refresh if token was recently updated (within last 5 minutes).
        """
        # Don't refresh if token was recently re-authenticated (within 5 minutes)
        if provider.updated_at:
            time_since_update = datetime.utcnow() - provider.updated_at
            if time_since_update < timedelta(minutes=5):
                # Token was recently updated, use it as-is
                logger.info(f"Using recently updated token for {provider.name} (updated {time_since_update.total_seconds():.0f}s ago)")
                return provider.access_token
        
        # Check if token needs refresh (refresh 5 minutes before expiry)
        needs_refresh = True
        if provider.token_expires_at:
            needs_refresh = provider.token_expires_at <= datetime.utcnow() + timedelta(minutes=5)
        
        if needs_refresh:
            logger.info(f"Refreshing token for {provider.name}")
            access_token, refresh_token, expires_at = self.refresh_access_token(
                provider.refresh_token
            )
            
            # Update provider in database
            provider.access_token = access_token
            provider.refresh_token = refresh_token
            provider.token_expires_at = expires_at
            provider.updated_at = datetime.utcnow()
            db.commit()
            
            return access_token
        
        return provider.access_token
    
    def get_accounts(self, access_token: str, provider_type: str = "accounts") -> List[Dict]:
        """
        Fetch all accounts or cards for a provider
        """
        endpoint = "accounts" if provider_type == "accounts" else "cards"
        
        headers = {"Authorization": f"Bearer {access_token}"}
        url = f"{self.api_base}/{endpoint}"
        
        logger.info(f"Fetching {endpoint} from {url}")
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            error_detail = response.text
            try:
                error_detail = response.json()
            except:
                pass
            logger.error(f"Failed to fetch {endpoint}: HTTP {response.status_code} - {error_detail}")
            raise Exception(f"Failed to fetch {endpoint}: HTTP {response.status_code} - {error_detail}")
        
        data = response.json()
        logger.info(f"Successfully fetched {len(data.get('results', []))} {endpoint}")
        return data.get("results", [])
    
    def get_transactions(
        self, 
        access_token: str, 
        account_id: str, 
        provider_type: str = "accounts",
        from_timestamp: Optional[str] = None
    ) -> List[Dict]:
        """
        Fetch transactions for an account
        If from_timestamp is provided, only fetch transactions after that time
        """
        endpoint = "accounts" if provider_type == "accounts" else "cards"
        
        url = f"{self.api_base}/{endpoint}/{account_id}/transactions"
        if from_timestamp:
            url += f"?from={from_timestamp}"
        
        headers = {"Authorization": f"Bearer {access_token}"}
        logger.info(f"Fetching transactions from {url}")
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            error_detail = response.text
            try:
                error_detail = response.json()
            except:
                pass
            logger.error(f"Failed to fetch transactions for {account_id}: HTTP {response.status_code} - {error_detail}")
            raise Exception(f"Failed to fetch transactions for {account_id}: HTTP {response.status_code} - {error_detail}")
        
        data = response.json()
        logger.info(f"Successfully fetched {len(data.get('results', []))} transactions for {account_id}")
        return data.get("results", [])
    
    def sync_provider(
        self, 
        db: Session, 
        provider: Provider
    ) -> Dict:
        """
        Sync all accounts for a provider
        Returns summary of sync operation
        """
        summary = {
            "provider": provider.name,
            "accounts_processed": 0,
            "transactions_synced": 0,
            "accounts": []
        }
        
        try:
            # Get valid access token
            access_token = self.get_valid_token(db, provider)
            logger.info(f"Starting sync for provider: {provider.name} (type: {provider.provider_type})")
            
            # Fetch all accounts
            accounts = self.get_accounts(access_token, provider.provider_type)
            
            for account in accounts:
                account_id = account.get("account_id")
                account_name = account.get("display_name", f"{provider.name}_account")
                
                # Get or create sync state
                sync_state = db.query(SyncState).filter(
                    SyncState.account_id == account_id
                ).first()
                
                if not sync_state:
                    sync_state = SyncState(
                        account_id=account_id,
                        provider_name=provider.name,
                        account_name=account_name
                    )
                    db.add(sync_state)
                    db.flush()
                
                # Fetch transactions (incremental if we have a last sync)
                transactions = self.get_transactions(
                    access_token,
                    account_id,
                    provider.provider_type,
                    sync_state.last_sync_timestamp
                )
                
                if transactions:
                    # Update sync state with newest timestamp
                    newest_timestamp = max(tx["timestamp"] for tx in transactions)
                    sync_state.last_sync_timestamp = newest_timestamp
                    sync_state.last_sync_at = datetime.utcnow()
                    sync_state.transaction_count += len(transactions)
                    
                    summary["transactions_synced"] += len(transactions)
                
                summary["accounts_processed"] += 1
                summary["accounts"].append({
                    "id": account_id,
                    "name": account_name,
                    "transactions": len(transactions)
                })
            
            db.commit()
            logger.info(f"Sync completed for {provider.name}: {summary['accounts_processed']} accounts, {summary['transactions_synced']} transactions")
            return summary
            
        except Exception as e:
            logger.error(f"Error syncing {provider.name}: {str(e)}")
            db.rollback()
            raise e
