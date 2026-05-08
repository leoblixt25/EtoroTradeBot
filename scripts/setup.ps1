# Setup script for eToro Portfolio Manager (Windows PowerShell)
Write-Host "Setting up eToro Portfolio Manager..." -ForegroundColor Green

# Backend setup
Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
Set-Location -LiteralPath "backend"
pip install -r requirements.txt
if ($?) { Write-Host "Backend dependencies installed" -ForegroundColor Green }
Set-Location ..

# Frontend setup
Write-Host "Installing Node.js dependencies..." -ForegroundColor Yellow
Set-Location -LiteralPath "frontend"
npm install
if ($?) { Write-Host "Frontend dependencies installed" -ForegroundColor Green }
Set-Location ..

# Environment setup
if (-not (Test-Path -LiteralPath ".env")) {
    Copy-Item -LiteralPath ".env.example" -Destination ".env"
    Write-Host "Created .env file from .env.example" -ForegroundColor Green
    Write-Host "Please edit .env with your API keys and configuration" -ForegroundColor Yellow
}

# Create directories
New-Item -ItemType Directory -Path "logs" -Force | Out-Null
New-Item -ItemType Directory -Path "data" -Force | Out-Null
Write-Host "Created logs/ and data/ directories" -ForegroundColor Green

Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "To start the backend:" -ForegroundColor Cyan
Write-Host "  cd backend; uvicorn main:app --reload" -ForegroundColor White
Write-Host ""
Write-Host "To start the frontend:" -ForegroundColor Cyan
Write-Host "  cd frontend; npm run dev" -ForegroundColor White
Write-Host ""
Write-Host "To start with Docker:" -ForegroundColor Cyan
Write-Host "  docker-compose -f docker/docker-compose.yml up" -ForegroundColor White
