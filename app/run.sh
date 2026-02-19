#!/bin/bash

# Quick run script for local development

echo "🚀 Starting TrueLayer to Firefly III Integration"

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "Run ./setup.sh first to configure your environment"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install/upgrade dependencies
echo "📥 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Create data directory if it doesn't exist
mkdir -p data

echo ""
echo "✅ Starting application..."
echo "📍 Access the UI at: http://localhost:8000"
echo "⏹️  Press Ctrl+C to stop"
echo ""

# Run the application
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
