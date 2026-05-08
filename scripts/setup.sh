#!/bin/bash
# Setup script for eToro Portfolio Manager
echo "Setting up eToro Portfolio Manager..."

# Backend setup
echo "Installing Python dependencies..."
cd backend
pip install -r requirements.txt
cd ..

# Frontend setup
echo "Installing Node.js dependencies..."
cd frontend
npm install
cd ..

# Environment setup
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file from .env.example"
    echo "Please edit .env with your API keys and configuration"
fi

# Create directories
mkdir -p logs data

echo "Setup complete!"
echo ""
echo "To start the backend:"
echo "  cd backend && uvicorn main:app --reload"
echo ""
echo "To start the frontend:"
echo "  cd frontend && npm run dev"
echo ""
echo "To start with Docker:"
echo "  docker-compose -f docker/docker-compose.yml up"
