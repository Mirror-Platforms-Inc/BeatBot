# BeatBot - One-Shot Setup Script for Windows/PowerShell
# Run with: .\setup.ps1

Write-Host "🤖 BeatBot Setup Starting..." -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
Write-Host "Checking Docker..." -ForegroundColor Yellow
try {
    docker info | Out-Null
    Write-Host "✅ Docker is running" -ForegroundColor Green
}
catch {
    Write-Host "❌ Docker is not running. Please start Docker Desktop and try again." -ForegroundColor Red
    exit 1
}

# Check if Ollama is installed
Write-Host "Checking Ollama..." -ForegroundColor Yellow
try {
    ollama list | Out-Null
    Write-Host "✅ Ollama is installed" -ForegroundColor Green
}
catch {
    Write-Host "⚠️  Ollama not found. Install from https://ollama.ai" -ForegroundColor Yellow
}

# Create virtual environment
Write-Host ""
Write-Host "Creating virtual environment..." -ForegroundColor Yellow
if (Test-Path "venv") {
    Write-Host "Virtual environment already exists, skipping..." -ForegroundColor Gray
}
else {
    python -m venv venv
    Write-Host "✅ Virtual environment created" -ForegroundColor Green
}

# Activate virtual environment
Write-Host ""
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"
Write-Host "✅ Virtual environment activated" -ForegroundColor Green

# Install dependencies
Write-Host ""
Write-Host "Installing dependencies (this may take a few minutes)..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
Write-Host "✅ Dependencies installed" -ForegroundColor Green

# Build Docker sandbox image
Write-Host ""
Write-Host "Building Docker sandbox image..." -ForegroundColor Yellow
docker build -f docker/sandbox/Dockerfile -t beatbot-sandbox:latest docker/sandbox/ --quiet
Write-Host "✅ Sandbox image built" -ForegroundColor Green

# Set environment variables
Write-Host ""
Write-Host "Configuring environment..." -ForegroundColor Yellow
$env:BEATBOT_MODEL_DEFAULT = "ollama/gemma3:12b"
$env:BEATBOT_SANDBOX_ENABLED = "true"
$env:BEATBOT_REQUIRE_APPROVAL = "true"
Write-Host "✅ Environment configured" -ForegroundColor Green

# Check if model is pulled
Write-Host ""
Write-Host "Checking for Gemma 3 12B model..." -ForegroundColor Yellow
$models = ollama list 2>$null
if ($models -match "gemma3:12b") {
    Write-Host "✅ Gemma 3 12B model found" -ForegroundColor Green
}
else {
    Write-Host "⚠️  Gemma 3 12B not found. Pull it with:" -ForegroundColor Yellow
    Write-Host "   ollama pull gemma3:12b" -ForegroundColor White
}

# Setup complete
Write-Host ""
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "🎉 Setup Complete!" -ForegroundColor Green
Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host ""
Write-Host "To start BeatBot:" -ForegroundColor White
Write-Host "  python main.py --mode interactive" -ForegroundColor Cyan
Write-Host ""
Write-Host "First time? Try these commands:" -ForegroundColor White
Write-Host "  'help' - Show available commands" -ForegroundColor Gray
Write-Host "  'What's my system info?' - Get CPU/memory stats" -ForegroundColor Gray
Write-Host "  'List files in current directory' - Test file operations" -ForegroundColor Gray
Write-Host ""
Write-Host "Press any key to start BeatBot now, or Ctrl+C to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# Start BeatBot
Write-Host ""
python main.py --mode interactive
