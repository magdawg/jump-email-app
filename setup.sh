#!/bin/bash

# AI Email Sorter - Local Development Setup Script

echo "🚀 Setting up AI Email Sorter for local development..."
echo ""

# Check prerequisites
echo "Checking prerequisites..."

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.11+"
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+"
    exit 1
fi

if ! command -v psql &> /dev/null; then
    echo "⚠️  PostgreSQL client not found. Make sure PostgreSQL is installed."
fi

echo "✅ Prerequisites check passed"
echo ""

# Backend setup
echo "📦 Setting up backend..."
cd backend

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install -q -r requirements.txt

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit backend/.env and add your API keys!"
fi

cd ..

echo "✅ Backend setup complete"
echo ""

# Frontend setup
echo "📦 Setting up frontend..."
cd frontend

# Install dependencies
echo "Installing Node dependencies..."
npm install

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
fi

cd ..

echo "✅ Frontend setup complete"
echo ""

# Create database
echo "🗄️  Setting up database..."
if command -v createdb &> /dev/null; then
    createdb emailsorter 2>/dev/null && echo "✅ Database 'emailsorter' created" || echo "ℹ️  Database might already exist"
else
    echo "⚠️  Could not create database automatically. Please run: createdb emailsorter"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit backend/.env and add your API keys:"
echo "   - GOOGLE_CLIENT_ID"
echo "   - GOOGLE_CLIENT_SECRET"
echo "   - ANTHROPIC_API_KEY"
echo ""
echo "2. Start the backend:"
echo "   cd backend && source venv/bin/activate && python main.py"
echo ""
echo "3. In a new terminal, start the frontend:"
echo "   cd frontend && npm start"
echo ""
echo "4. Visit http://localhost:3000"
echo ""
echo "📖 See README.md for detailed setup instructions"
