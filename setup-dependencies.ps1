# BeatBot Dependency Checker and Installer for Windows
# Run this script as Administrator for best results

param(
    [switch]$SkipOllama = $false,
    [switch]$NonInteractive = $false
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "BeatBot Dependency Setup for Windows" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$script:issues = @()
$script:warnings = @()

# Function to check if running as administrator
function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Check admin status
$isAdmin = Test-Administrator
if (-not $isAdmin) {
    Write-Host "WARNING: Not running as Administrator" -ForegroundColor Yellow
    Write-Host "Some installations may require admin privileges" -ForegroundColor Yellow
    Write-Host ""
}

# 1. Check Python version
Write-Host "[1/7] Checking Python version..." -ForegroundColor Green
try {
    $pythonVersion = python --version 2>&1
    Write-Host "   Found: $pythonVersion" -ForegroundColor White
    
    # Extract version number
    if ($pythonVersion -match "Python (\d+)\.(\d+)\.(\d+)") {
        $major = [int]$matches[1]
        $minor = [int]$matches[2]
        
        if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 11)) {
            $script:issues += "Python version is $major.$minor but 3.11+ is required"
            Write-Host "   [X] Python 3.11+ required, found $major.$minor" -ForegroundColor Red
        }
        else {
            Write-Host "   [OK] Python version is compatible" -ForegroundColor Green
        }
    }
}
catch {
    $script:issues += "Python is not installed or not in PATH"
    Write-Host "   [X] Python not found in PATH" -ForegroundColor Red
}

# 2. Check pip
Write-Host ""
Write-Host "[2/7] Checking pip..." -ForegroundColor Green
try {
    $pipVersion = pip --version 2>&1
    Write-Host "   Found: $pipVersion" -ForegroundColor White
    Write-Host "   [OK] pip is available" -ForegroundColor Green
}
catch {
    $script:issues += "pip is not installed or not in PATH"
    Write-Host "   [X] pip not found" -ForegroundColor Red
}

# 3. Check Docker
Write-Host ""
Write-Host "[3/7] Checking Docker..." -ForegroundColor Green
try {
    $dockerVersion = docker --version 2>&1
    Write-Host "   Found: $dockerVersion" -ForegroundColor White
    
    # Check if Docker daemon is running
    $null = docker ps 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   [OK] Docker is installed and running" -ForegroundColor Green
    }
    else {
        $script:warnings += "Docker is installed but daemon is not running"
        Write-Host "   [!] Docker daemon is not running. Please start Docker Desktop." -ForegroundColor Yellow
    }
}
catch {
    $script:issues += "Docker is not installed or not in PATH"
    Write-Host "   [X] Docker not found" -ForegroundColor Red
}

# 4. Check and install Python dependencies
Write-Host ""
Write-Host "[4/7] Checking Python dependencies..." -ForegroundColor Green
$requirementsPath = Join-Path $PSScriptRoot "requirements.txt"

if (Test-Path $requirementsPath) {
    Write-Host "   Found requirements.txt" -ForegroundColor White
    
    if ($script:issues.Count -eq 0) {
        $install = $true
        if (-not $NonInteractive) {
            $response = Read-Host "   Install Python packages from requirements.txt? (Y/n)"
            $install = ($response -eq "" -or $response -eq "Y" -or $response -eq "y")
        }
        
        if ($install) {
            Write-Host "   Installing Python dependencies (this may take a few minutes)..." -ForegroundColor Cyan
            pip install -r $requirementsPath
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "   [OK] Python dependencies installed successfully" -ForegroundColor Green
            }
            else {
                $script:issues += "Failed to install Python dependencies"
                Write-Host "   [X] Failed to install some dependencies" -ForegroundColor Red
            }
        }
        else {
            Write-Host "   [SKIP] Skipped Python package installation" -ForegroundColor Yellow
        }
    }
    else {
        Write-Host "   [SKIP] Skipping installation due to previous errors" -ForegroundColor Yellow
    }
}
else {
    $script:warnings += "requirements.txt not found in current directory"
    Write-Host "   [!] requirements.txt not found at: $requirementsPath" -ForegroundColor Yellow
}

# 5. Install Playwright browsers
Write-Host ""
Write-Host "[5/7] Checking Playwright browsers..." -ForegroundColor Green
try {
    # Check if playwright is installed
    $playwrightCheck = python -c "import playwright; print('installed')" 2>&1
    
    if ($playwrightCheck -match "installed") {
        Write-Host "   Playwright package is installed" -ForegroundColor White
        
        $install = $true
        if (-not $NonInteractive) {
            $response = Read-Host "   Install Playwright browsers? (Y/n)"
            $install = ($response -eq "" -or $response -eq "Y" -or $response -eq "y")
        }
        
        if ($install) {
            Write-Host "   Installing Playwright browsers (this may take several minutes)..." -ForegroundColor Cyan
            playwright install chromium
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "   [OK] Playwright browsers installed" -ForegroundColor Green
            }
            else {
                $script:warnings += "Failed to install Playwright browsers"
                Write-Host "   [!] Failed to install Playwright browsers" -ForegroundColor Yellow
            }
        }
        else {
            Write-Host "   [SKIP] Skipped Playwright browser installation" -ForegroundColor Yellow
        }
    }
    else {
        Write-Host "   [SKIP] Playwright not installed yet (will be available after step 4)" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "   [SKIP] Playwright check skipped" -ForegroundColor Yellow
}

# 6. Check for Ollama (optional but recommended)
Write-Host ""
Write-Host "[6/7] Checking Ollama (optional LLM provider)..." -ForegroundColor Green
if (-not $SkipOllama) {
    try {
        $ollamaVersion = ollama --version 2>&1
        Write-Host "   Found: $ollamaVersion" -ForegroundColor White
        Write-Host "   [OK] Ollama is installed" -ForegroundColor Green
    }
    catch {
        Write-Host "   [INFO] Ollama not found (optional)" -ForegroundColor Cyan
        Write-Host "   To use local LLMs, install Ollama from: https://ollama.ai" -ForegroundColor Cyan
        
        if (-not $NonInteractive) {
            $response = Read-Host "   Open Ollama website in browser? (y/N)"
            if ($response -eq "Y" -or $response -eq "y") {
                Start-Process "https://ollama.ai"
            }
        }
    }
}
else {
    Write-Host "   [SKIP] Skipped Ollama check (SkipOllama flag)" -ForegroundColor Yellow
}

# 7. Verify installation
Write-Host ""
Write-Host "[7/7] Verifying critical imports..." -ForegroundColor Green
$criticalPackages = @(
    "litellm",
    "aiohttp",
    "yaml",
    "docker",
    "cryptography",
    "pydantic"
)

foreach ($package in $criticalPackages) {
    $importName = $package
    if ($package -eq "yaml") { $importName = "yaml" }
    
    $result = python -c "import $importName; print('OK')" 2>&1
    if ($result -match "OK") {
        Write-Host "   [OK] $package" -ForegroundColor Green
    }
    else {
        Write-Host "   [X] $package - import failed" -ForegroundColor Red
    }
}

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setup Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($script:issues.Count -eq 0 -and $script:warnings.Count -eq 0) {
    Write-Host "[OK] All dependencies are ready!" -ForegroundColor Green
    Write-Host ""
    Write-Host "You can now run BeatBot with:" -ForegroundColor White
    Write-Host "   python main.py" -ForegroundColor Cyan
}
else {
    if ($script:issues.Count -gt 0) {
        Write-Host "[X] Critical Issues Found:" -ForegroundColor Red
        foreach ($issue in $script:issues) {
            Write-Host "   - $issue" -ForegroundColor Red
        }
    }
    
    if ($script:warnings.Count -gt 0) {
        Write-Host ""
        Write-Host "[!] Warnings:" -ForegroundColor Yellow
        foreach ($warning in $script:warnings) {
            Write-Host "   - $warning" -ForegroundColor Yellow
        }
    }
    
    if ($script:issues.Count -gt 0) {
        Write-Host ""
        Write-Host "Please resolve the critical issues above before running BeatBot." -ForegroundColor Red
        exit 1
    }
    else {
        Write-Host ""
        Write-Host "You can proceed, but address warnings for best experience." -ForegroundColor Yellow
    }
}

# Additional setup suggestions
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Next Steps" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Ensure Docker Desktop is running" -ForegroundColor White
Write-Host "2. (Optional) Install Ollama and pull a model:" -ForegroundColor White
Write-Host "   ollama pull llama3.2" -ForegroundColor Cyan
Write-Host "3. Configure BeatBot:" -ForegroundColor White
Write-Host "   Edit config/default_config.yaml" -ForegroundColor Cyan
Write-Host "4. Run BeatBot:" -ForegroundColor White
Write-Host "   python main.py --mode interactive" -ForegroundColor Cyan
Write-Host ""
