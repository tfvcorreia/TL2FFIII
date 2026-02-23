from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON, Text
from datetime import datetime
from app.database import Base


class Provider(Base):
    """Stores TrueLayer provider configurations"""
    __tablename__ = "providers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    provider_type = Column(String, nullable=False)  # 'accounts' or 'cards'
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    token_expires_at = Column(DateTime, nullable=True)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Optional: store provider-specific settings
    settings = Column(JSON, default={})


class SyncState(Base):
    """Tracks synchronization state per account"""
    __tablename__ = "sync_state"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(String, unique=True, index=True, nullable=False)
    provider_name = Column(String, nullable=False)
    account_name = Column(String, nullable=True)
    last_sync_timestamp = Column(String, nullable=True)  # ISO format timestamp
    last_sync_at = Column(DateTime, default=datetime.utcnow)
    transaction_count = Column(Integer, default=0)
    firefly_account_id = Column(String, nullable=True)  # Link to Firefly III account
    enabled = Column(Boolean, default=True)
    
    # Store last successful sync details
    last_sync_details = Column(JSON, default={})


class SyncLog(Base):
    """Log of sync operations"""
    __tablename__ = "sync_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    provider_name = Column(String, nullable=True)
    account_id = Column(String, nullable=True)
    status = Column(String, nullable=False)  # 'success', 'error', 'partial'
    transactions_synced = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    details = Column(JSON, default={})

class Settings(Base):
    """Stores application settings configurable via the UI"""
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
