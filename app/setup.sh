#!/bin/bash

# Setup script for TrueLayer to Firefly III Integration

echo "🏦 TrueLayer to Firefly III Integration Setup"
echo "=============================================="
echo ""

# Check if .env exists
if [ -f .env ]; then
    echo "⚠️  .env file already exists!"
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Setup cancelled."
        exit 0
    fi
fi

# Create .env file
echo "Creating .env file..."
cp .env.example .env

echo ""
echo "📝 Please provide the following information:"
echo ""

# TrueLayer credentials
read -p "TrueLayer Client ID: " TRUELAYER_CLIENT_ID
read -p "TrueLayer Client Secret: " TRUELAYER_CLIENT_SECRET

echo ""

# Firefly III credentials
read -p "Firefly III URL (e.g., http://firefly:8080): " FIREFLY_URL
read -p "Firefly III Personal Access Token: " FIREFLY_TOKEN

echo ""

# Optional settings
read -p "Sync interval in minutes [60]: " SYNC_INTERVAL
SYNC_INTERVAL=${SYNC_INTERVAL:-60}

read -p "Timezone [Europe/London]: " TIMEZONE
TIMEZONE=${TIMEZONE:-Europe/London}

# Generate secret key
SECRET_KEY=$(openssl rand -hex 32 2>/dev/null || cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 64 | head -n 1)

# Write to .env
cat > .env << EOF
# TrueLayer API Configuration
TRUELAYER_CLIENT_ID=$TRUELAYER_CLIENT_ID
TRUELAYER_CLIENT_SECRET=$TRUELAYER_CLIENT_SECRET

# Firefly III Configuration
FIREFLY_URL=$FIREFLY_URL
FIREFLY_TOKEN=$FIREFLY_TOKEN

# Database Configuration
DATABASE_URL=sqlite:////app/data/truelayer_firefly.db

# Application Settings
SYNC_INTERVAL_MINUTES=$SYNC_INTERVAL
SECRET_KEY=$SECRET_KEY
DEBUG=false

# Timezone
TIMEZONE=$TIMEZONE
EOF

echo ""
echo "✅ Configuration saved to .env"
echo ""
echo "Next steps:"
echo "1. Create data directory: mkdir -p data"
echo "2. Start with Docker: docker-compose up -d"
echo "3. Access the UI at: http://localhost:8000"
echo ""
echo "For TrueNAS Scale / Dockge deployment:"
echo "1. Create a new stack in Dockge"
echo "2. Copy docker-compose.yml content"
echo "3. Add environment variables from .env file"
echo "4. Deploy the stack"
echo ""
