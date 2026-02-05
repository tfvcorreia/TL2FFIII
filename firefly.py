import requests
from typing import Dict, List, Optional
from datetime import datetime
from app.config import settings


class FireflyService:
    """Handles all Firefly III API interactions"""
    
    def __init__(self):
        self.base_url = settings.firefly_url.rstrip('/')
        self.token = settings.firefly_token
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def test_connection(self) -> bool:
        """Test if Firefly III connection is working"""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/about",
                headers=self.headers,
                timeout=10
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def get_accounts(self, account_type: str = "asset") -> List[Dict]:
        """
        Fetch accounts from Firefly III
        account_type: 'asset', 'expense', 'revenue', etc.
        """
        response = requests.get(
            f"{self.base_url}/api/v1/accounts",
            headers=self.headers,
            params={"type": account_type}
        )
        
        if response.status_code != 200:
            raise Exception(f"Failed to fetch Firefly accounts: {response.text}")
        
        data = response.json()
        return data.get("data", [])
    
    def create_account(self, name: str, account_type: str = "asset", **kwargs) -> Dict:
        """
        Create a new account in Firefly III
        """
        payload = {
            "name": name,
            "type": account_type,
            **kwargs
        }
        
        response = requests.post(
            f"{self.base_url}/api/v1/accounts",
            headers=self.headers,
            json=payload
        )
        
        if response.status_code not in [200, 201]:
            raise Exception(f"Failed to create Firefly account: {response.text}")
        
        return response.json()
    
    def get_or_create_account(self, account_name: str) -> str:
        """
        Get or create an asset account in Firefly III
        Returns the account ID
        """
        # Search for existing account
        accounts = self.get_accounts("asset")
        
        for account in accounts:
            if account["attributes"]["name"] == account_name:
                return account["id"]
        
        # Create new account if not found
        result = self.create_account(account_name, "asset")
        return result["data"]["id"]
    
    def convert_transaction(self, truelayer_tx: Dict, source_account_id: str) -> Dict:
        """
        Convert TrueLayer transaction format to Firefly III format
        """
        amount = abs(truelayer_tx.get("amount", 0))
        is_withdrawal = truelayer_tx.get("transaction_type") == "DEBIT"
        
        # Prepare transaction for Firefly III
        transaction = {
            "type": "withdrawal" if is_withdrawal else "deposit",
            "date": truelayer_tx.get("timestamp", datetime.utcnow().isoformat()),
            "amount": str(amount),
            "description": truelayer_tx.get("description", "Transaction"),
            "currency_code": truelayer_tx.get("currency", "GBP"),
            "source_id" if is_withdrawal else "destination_id": source_account_id,
        }
        
        # Add category if available
        category = truelayer_tx.get("transaction_category")
        if category:
            transaction["category_name"] = category
        
        # Add external ID to prevent duplicates
        external_id = truelayer_tx.get("transaction_id") or truelayer_tx.get("provider_transaction_id")
        if external_id:
            transaction["external_id"] = external_id
        
        # Add notes with provider info
        notes = f"Provider: {truelayer_tx.get('provider', 'unknown')}\n"
        notes += f"Account: {truelayer_tx.get('source_account', 'unknown')}"
        transaction["notes"] = notes
        
        return transaction
    
    def import_transaction(self, transaction: Dict) -> Dict:
        """
        Import a single transaction to Firefly III
        """
        payload = {
            "error_if_duplicate_hash": True,
            "apply_rules": True,
            "transactions": [transaction]
        }
        
        response = requests.post(
            f"{self.base_url}/api/v1/transactions",
            headers=self.headers,
            json=payload
        )
        
        # 422 might mean duplicate - that's okay
        if response.status_code in [200, 201]:
            return {"status": "created", "data": response.json()}
        elif response.status_code == 422:
            return {"status": "duplicate", "data": response.json()}
        else:
            return {"status": "error", "message": response.text}
    
    def import_transactions(self, transactions: List[Dict]) -> Dict:
        """
        Import multiple transactions to Firefly III
        Returns summary of import operation
        """
        summary = {
            "total": len(transactions),
            "created": 0,
            "duplicates": 0,
            "errors": 0,
            "error_details": []
        }
        
        for tx in transactions:
            result = self.import_transaction(tx)
            
            if result["status"] == "created":
                summary["created"] += 1
            elif result["status"] == "duplicate":
                summary["duplicates"] += 1
            else:
                summary["errors"] += 1
                summary["error_details"].append({
                    "transaction": tx,
                    "error": result.get("message")
                })
        
        return summary
    
    def sync_truelayer_transactions(
        self, 
        truelayer_transactions: List[Dict],
        firefly_account_name: str
    ) -> Dict:
        """
        Sync TrueLayer transactions to Firefly III
        """
        # Get or create the Firefly account
        account_id = self.get_or_create_account(firefly_account_name)
        
        # Convert transactions
        firefly_transactions = [
            self.convert_transaction(tx, account_id)
            for tx in truelayer_transactions
        ]
        
        # Import to Firefly
        return self.import_transactions(firefly_transactions)
