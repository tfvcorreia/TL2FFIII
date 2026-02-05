# Development Guide

## Local Development Setup

### Prerequisites

- Python 3.11+
- pip
- Virtual environment (recommended)

### Setup

1. **Clone the repository**
```bash
git clone <your-repo>
cd truelayer-firefly
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your credentials
```

5. **Run locally**
```bash
# From project root
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

6. **Access the app**
```
http://localhost:8000
```

## Project Structure

```
truelayer-firefly/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app and routes
│   ├── config.py            # Configuration management
│   ├── database.py          # Database setup
│   ├── models.py            # SQLAlchemy models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── truelayer.py     # TrueLayer API service
│   │   └── firefly.py       # Firefly III API service
│   └── templates/
│       └── index.html       # Web UI
├── data/                    # Database storage (created at runtime)
├── requirements.txt         # Python dependencies
├── Dockerfile              # Docker image
├── docker-compose.yml      # Docker Compose config
├── .env.example            # Environment template
├── .env                    # Your configuration (git-ignored)
├── setup.sh               # Setup helper script
└── README.md              # Main documentation
```

## Development Workflow

### Making Changes

1. Make your changes to the code
2. Test locally with `--reload` flag (auto-restart on changes)
3. Test in Docker:
```bash
docker-compose build
docker-compose up
```

### Database Migrations

If you modify models in `app/models.py`:

1. For SQLite (default), just delete the database file and restart
2. For PostgreSQL with Alembic:
```bash
# Initialize Alembic (first time only)
alembic init alembic

# Generate migration
alembic revision --autogenerate -m "description"

# Apply migration
alembic upgrade head
```

### Testing

#### Manual Testing

1. Add a test provider with dummy tokens
2. Try syncing (will fail but shows the flow)
3. Check database: `sqlite3 data/truelayer_firefly.db`

#### API Testing

Use curl or Postman:

```bash
# Health check
curl http://localhost:8000/health

# List providers
curl http://localhost:8000/api/providers

# Add provider (form data)
curl -X POST http://localhost:8000/api/providers \
  -F "name=TestBank" \
  -F "provider_type=accounts" \
  -F "access_token=dummy" \
  -F "refresh_token=dummy"
```

## Common Development Tasks

### Reset Database

```bash
rm data/truelayer_firefly.db
# Restart app to recreate
```

### View Logs

```bash
# Docker
docker logs -f truelayer-firefly

# Local
# Logs print to console when running with uvicorn
```

### Debug Mode

Enable in `.env`:
```env
DEBUG=true
```

This will:
- Show detailed error messages
- Enable auto-reload
- Show more verbose logs

### Change Sync Interval for Testing

```env
SYNC_INTERVAL_MINUTES=5  # Sync every 5 minutes
```

## Adding New Features

### Adding a New API Endpoint

1. Add route in `app/main.py`:
```python
@app.get("/api/my-endpoint")
async def my_endpoint(db: Session = Depends(get_db)):
    # Your code
    return {"data": "response"}
```

2. Add UI button/action in `app/templates/index.html`
3. Test locally

### Adding a New Service

1. Create `app/services/myservice.py`
2. Implement service class
3. Import and use in `app/main.py`

### Modifying the Database

1. Update models in `app/models.py`
2. Delete database for SQLite (it recreates)
3. Or create Alembic migration for PostgreSQL

## Troubleshooting Development Issues

### Import Errors

Make sure you're running from project root:
```bash
# Good
cd /path/to/truelayer-firefly
uvicorn app.main:app

# Bad
cd /path/to/truelayer-firefly/app
uvicorn main:app  # Won't work!
```

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Kill it
kill -9 <PID>
```

### Database Locked (SQLite)

- Close any DB browser tools
- Make sure only one instance is running
- Restart the application

## Best Practices

1. **Always test locally before Docker**
2. **Use virtual environments**
3. **Don't commit .env or database files**
4. **Keep services modular** (separate TrueLayer, Firefly, etc.)
5. **Add logging** for debugging
6. **Handle errors gracefully**
7. **Document your changes**

## Useful Commands

```bash
# Install new package
pip install package-name
pip freeze > requirements.txt

# Format code (optional)
pip install black
black app/

# Check for issues
pip install pylint
pylint app/

# Run in background
uvicorn app.main:app --host 0.0.0.0 --port 8000 &

# Stop background process
pkill -f uvicorn
```

## Contributing

When contributing:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Update README if needed
6. Submit a pull request

---

Happy coding! 🚀
