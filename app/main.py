from fastapi import FastAPI, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging

from app.database import get_db, init_db
from app.models import Provider, SyncState, SyncLog
from app.services.truelayer import TrueLayerService
from app.services.firefly import FireflyService
from app.config import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="TrueLayer to Firefly III Integration")

# Setup templates
templates = Jinja2Templates(directory="app/templates")

# Initialize services
truelayer_service = TrueLayerService()
firefly_service = FireflyService()

# Background scheduler for automatic syncs
scheduler = BackgroundScheduler()


# ============================================================================
# BACKGROUND SYNC FUNCTION
# ============================================================================

def scheduled_sync():
    """Background job to sync all enabled providers"""
    logger.info("Starting scheduled sync...")
    db = next(get_db())
    
    try:
        providers = db.query(Provider).filter(Provider.enabled == True).all()
        
        for provider in providers:
            try:
                logger.info(f"Syncing provider: {provider.name}")
                
                # Sync TrueLayer transactions
                sync_result = truelayer_service.sync_provider(db, provider)
                
                # Get transactions and sync to Firefly
                access_token = truelayer_service.get_valid_token(db, provider)
                
                for account_info in sync_result["accounts"]:
                    if account_info["transactions"] == 0:
                        continue
                    
                    # Fetch transactions for this account
                    sync_state = db.query(SyncState).filter(
                        SyncState.account_id == account_info["id"]
                    ).first()
                    
                    if not sync_state:
                        continue
                    
                    # Determine from_timestamp for incremental sync
                    from_ts = None
                    if sync_state.last_sync_details:
                        from_ts = sync_state.last_sync_details.get("last_firefly_sync")
                    
                    transactions = truelayer_service.get_transactions(
                        access_token,
                        account_info["id"],
                        provider.provider_type,
                        from_ts
                    )
                    
                    if transactions:
                        # Sync to Firefly III
                        firefly_result = firefly_service.sync_truelayer_transactions(
                            transactions,
                            account_info["name"]
                        )
                        
                        # Update sync state
                        sync_state.last_sync_details = {
                            "last_firefly_sync": datetime.utcnow().isoformat(),
                            "firefly_result": firefly_result
                        }
                        db.commit()
                        
                        logger.info(f"Synced {firefly_result['created']} new transactions for {account_info['name']}")
                
                # Log successful sync
                log = SyncLog(
                    provider_name=provider.name,
                    status="success",
                    transactions_synced=sync_result["transactions_synced"],
                    details=sync_result
                )
                db.add(log)
                db.commit()
                
            except Exception as e:
                logger.error(f"Error syncing provider {provider.name}: {str(e)}")
                log = SyncLog(
                    provider_name=provider.name,
                    status="error",
                    error_message=str(e)
                )
                db.add(log)
                db.commit()
    
    finally:
        db.close()
    
    logger.info("Scheduled sync completed")


# ============================================================================
# STARTUP / SHUTDOWN
# ============================================================================

@app.on_event("startup")
def startup_event():
    """Initialize database and start scheduler"""
    logger.info("Initializing database...")
    init_db()
    
    # Start background scheduler
    if not scheduler.running:
        scheduler.add_job(
            scheduled_sync,
            trigger=IntervalTrigger(minutes=settings.sync_interval_minutes),
            id="sync_job",
            replace_existing=True
        )
        scheduler.start()
        logger.info(f"Scheduler started - syncing every {settings.sync_interval_minutes} minutes")


@app.on_event("shutdown")
def shutdown_event():
    """Cleanup on shutdown"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")


# ============================================================================
# WEB UI ROUTES
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, db: Session = Depends(get_db)):
    """Main dashboard"""
    providers = db.query(Provider).all()
    sync_states = db.query(SyncState).all()
    recent_logs = db.query(SyncLog).order_by(SyncLog.timestamp.desc()).limit(10).all()
    
    # Test Firefly connection
    firefly_connected = firefly_service.test_connection()
    
    return templates.TemplateResponse("main.html", {
        "request": request,
        "providers": providers,
        "sync_states": sync_states,
        "recent_logs": recent_logs,
        "firefly_connected": firefly_connected
    })


# ============================================================================
# API ROUTES - PROVIDERS
# ============================================================================

@app.post("/api/providers")
async def create_provider(
    name: str = Form(...),
    provider_type: str = Form(...),
    access_token: str = Form(...),
    refresh_token: str = Form(...),
    db: Session = Depends(get_db)
):
    """Add a new provider"""
    # Check if provider already exists
    existing = db.query(Provider).filter(Provider.name == name).first()
    if existing:
        raise HTTPException(400, "Provider with this name already exists")
    
    provider = Provider(
        name=name,
        provider_type=provider_type,
        access_token=access_token,
        refresh_token=refresh_token
    )
    
    db.add(provider)
    db.commit()
    db.refresh(provider)
    
    return {"status": "success", "provider": {
        "id": provider.id,
        "name": provider.name,
        "type": provider.provider_type
    }}


@app.get("/api/providers")
async def list_providers(db: Session = Depends(get_db)):
    """List all providers"""
    providers = db.query(Provider).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "type": p.provider_type,
            "enabled": p.enabled,
            "created_at": p.created_at.isoformat()
        }
        for p in providers
    ]


@app.delete("/api/providers/{provider_id}")
async def delete_provider(provider_id: int, db: Session = Depends(get_db)):
    """Delete a provider"""
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(404, "Provider not found")
    
    db.delete(provider)
    db.commit()
    
    return {"status": "success"}


@app.put("/api/providers/{provider_id}/toggle")
async def toggle_provider(provider_id: int, db: Session = Depends(get_db)):
    """Enable/disable a provider"""
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(404, "Provider not found")
    
    provider.enabled = not provider.enabled
    db.commit()
    
    return {"status": "success", "enabled": provider.enabled}


# ============================================================================
# API ROUTES - SYNC
# ============================================================================

@app.post("/api/sync")
async def manual_sync(db: Session = Depends(get_db)):
    """Manually trigger a sync"""
    try:
        scheduled_sync()
        return {"status": "success", "message": "Sync completed"}
    except Exception as e:
        logger.error(f"Manual sync failed: {str(e)}")
        raise HTTPException(500, str(e))


@app.post("/api/sync/{provider_id}")
async def sync_provider(provider_id: int, db: Session = Depends(get_db)):
    """Sync a specific provider"""
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(404, "Provider not found")
    
    try:
        result = truelayer_service.sync_provider(db, provider)
        
        log = SyncLog(
            provider_name=provider.name,
            status="success",
            transactions_synced=result["transactions_synced"],
            details=result
        )
        db.add(log)
        db.commit()
        
        return {"status": "success", "result": result}
    except Exception as e:
        logger.error(f"Sync failed: {str(e)}")
        
        log = SyncLog(
            provider_name=provider.name,
            status="error",
            error_message=str(e)
        )
        db.add(log)
        db.commit()
        
        raise HTTPException(500, str(e))


@app.get("/api/sync/status")
async def sync_status(db: Session = Depends(get_db)):
    """Get current sync status"""
    total_providers = db.query(Provider).count()
    enabled_providers = db.query(Provider).filter(Provider.enabled == True).count()
    total_accounts = db.query(SyncState).count()
    
    last_sync = db.query(SyncLog).order_by(SyncLog.timestamp.desc()).first()
    
    return {
        "total_providers": total_providers,
        "enabled_providers": enabled_providers,
        "total_accounts": total_accounts,
        "last_sync": last_sync.timestamp.isoformat() if last_sync else None,
        "scheduler_running": scheduler.running
    }


# ============================================================================
# API ROUTES - FIREFLY
# ============================================================================

@app.get("/api/firefly/test")
async def test_firefly():
    """Test Firefly III connection"""
    connected = firefly_service.test_connection()
    return {"connected": connected}


@app.get("/api/firefly/accounts")
async def get_firefly_accounts():
    """Get Firefly III accounts"""
    try:
        accounts = firefly_service.get_accounts()
        return {"status": "success", "accounts": accounts}
    except Exception as e:
        raise HTTPException(500, str(e))


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }
