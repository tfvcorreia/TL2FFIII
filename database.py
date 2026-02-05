import sqlite3
import json
from datetime import datetime
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path='data/app.db'):
        self.db_path = db_path
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def init_db(self):
        """Initialize database tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Providers table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS providers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    refresh_token TEXT NOT NULL,
                    account_type TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_sync TIMESTAMP,
                    enabled BOOLEAN DEFAULT 1
                )
            ''')
            
            # Sync state table (tracks last sync per account)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sync_state (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider_id INTEGER NOT NULL,
                    account_id TEXT NOT NULL,
                    last_timestamp TEXT,
                    last_sync TIMESTAMP,
                    FOREIGN KEY (provider_id) REFERENCES providers(id) ON DELETE CASCADE,
                    UNIQUE(provider_id, account_id)
                )
            ''')
            
            # Firefly III configuration
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS firefly_config (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    url TEXT NOT NULL,
                    token TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Account mapping (TrueLayer account -> Firefly III account)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS account_mapping (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider_id INTEGER NOT NULL,
                    truelayer_account_id TEXT NOT NULL,
                    firefly_account_id INTEGER NOT NULL,
                    account_name TEXT,
                    FOREIGN KEY (provider_id) REFERENCES providers(id) ON DELETE CASCADE,
                    UNIQUE(provider_id, truelayer_account_id)
                )
            ''')
            
            # Sync log
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sync_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider_id INTEGER,
                    status TEXT NOT NULL,
                    transactions_count INTEGER DEFAULT 0,
                    error_message TEXT,
                    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (provider_id) REFERENCES providers(id) ON DELETE SET NULL
                )
            ''')
            
            conn.commit()
            logger.info("Database initialized successfully")
    
    def add_provider(self, name, refresh_token, account_type):
        """Add a new provider"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO providers (name, refresh_token, account_type) VALUES (?, ?, ?)',
                (name, refresh_token, account_type)
            )
            return cursor.lastrowid
    
    def get_all_providers(self):
        """Get all providers"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    id, name, account_type, created_at, last_sync, enabled
                FROM providers
                ORDER BY name
            ''')
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def get_provider(self, provider_id):
        """Get a specific provider with refresh token"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM providers WHERE id = ?',
                (provider_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def update_provider_refresh_token(self, provider_id, refresh_token):
        """Update provider's refresh token"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE providers SET refresh_token = ? WHERE id = ?',
                (refresh_token, provider_id)
            )
    
    def update_provider_last_sync(self, provider_id):
        """Update provider's last sync timestamp"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE providers SET last_sync = CURRENT_TIMESTAMP WHERE id = ?',
                (provider_id,)
            )
    
    def delete_provider(self, provider_id):
        """Delete a provider"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM providers WHERE id = ?', (provider_id,))
    
    def get_last_sync(self, provider_id, account_id):
        """Get last sync timestamp for an account"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT last_timestamp FROM sync_state WHERE provider_id = ? AND account_id = ?',
                (provider_id, account_id)
            )
            row = cursor.fetchone()
            return row['last_timestamp'] if row else None
    
    def update_last_sync(self, provider_id, account_id, timestamp):
        """Update last sync timestamp for an account"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO sync_state (provider_id, account_id, last_timestamp, last_sync)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(provider_id, account_id) 
                DO UPDATE SET last_timestamp = ?, last_sync = CURRENT_TIMESTAMP
            ''', (provider_id, account_id, timestamp, timestamp))
    
    def save_firefly_config(self, url, token):
        """Save Firefly III configuration"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO firefly_config (id, url, token, updated_at)
                VALUES (1, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) 
                DO UPDATE SET url = ?, token = ?, updated_at = CURRENT_TIMESTAMP
            ''', (url, token, url, token))
    
    def get_firefly_config(self):
        """Get Firefly III configuration"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT url, token FROM firefly_config WHERE id = 1')
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_firefly_account_mapping(self, provider_id, truelayer_account_id):
        """Get Firefly III account ID for a TrueLayer account"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT firefly_account_id FROM account_mapping WHERE provider_id = ? AND truelayer_account_id = ?',
                (provider_id, truelayer_account_id)
            )
            row = cursor.fetchone()
            return row['firefly_account_id'] if row else None
    
    def save_account_mapping(self, provider_id, truelayer_account_id, firefly_account_id, account_name):
        """Save account mapping"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO account_mapping (provider_id, truelayer_account_id, firefly_account_id, account_name)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(provider_id, truelayer_account_id)
                DO UPDATE SET firefly_account_id = ?, account_name = ?
            ''', (provider_id, truelayer_account_id, firefly_account_id, account_name, firefly_account_id, account_name))
    
    def log_sync(self, provider_id, status, transactions_count=0, error_message=None):
        """Log sync operation"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO sync_log (provider_id, status, transactions_count, error_message) VALUES (?, ?, ?, ?)',
                (provider_id, status, transactions_count, error_message)
            )
    
    def get_sync_status(self):
        """Get overall sync status"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get last sync log entry
            cursor.execute('''
                SELECT 
                    synced_at as last_sync,
                    status,
                    SUM(transactions_count) as total_transactions
                FROM sync_log
                WHERE synced_at = (SELECT MAX(synced_at) FROM sync_log)
                GROUP BY synced_at, status
                LIMIT 1
            ''')
            
            row = cursor.fetchone()
            
            if row:
                return {
                    'last_sync': row['last_sync'],
                    'status': row['status'],
                    'total_transactions': row['total_transactions']
                }
            
            return {
                'last_sync': None,
                'status': 'never_run',
                'total_transactions': 0
            }
