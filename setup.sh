#!/bin/bash
# Setup script for auto-apply-agent

set -e

echo "🚀 Setting up Auto-Apply Agent..."

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q -r requirements.txt

# Create .env if not exists
if [ ! -f ".env" ]; then
    echo "⚙️  Creating .env file (copy from config/.env.example)..."
    cp config/.env.example .env
    echo "⚠️  Please edit .env and add your LLM_API_KEY"
fi

# Create profile.json if not exists
if [ ! -f "profile.json" ]; then
    echo "👤 Creating profile.json (copy from template)..."
    cp config/profile.json.template profile.json
    echo "⚠️  Please edit profile.json with your information"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env and add your LLM_API_KEY"
echo "2. Edit profile.json with your information"
echo "3. Run: python agent.py '<job_application_url>'"
echo ""
