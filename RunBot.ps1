# ==============================
# Trading Bot Launcher
# ==============================

$BASE_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $BASE_DIR

Write-Host "Starting bot from: $BASE_DIR"

# Activate venv
$venvPath = "$BASE_DIR\.venv\Scripts\Activate.ps1"

if (!(Test-Path $venvPath)) {
    Write-Host "ERROR: Virtual environment not found at $venvPath"
    Pause
    exit 1
}

& $venvPath

# Optional: sanity check
Write-Host "Python path:"
python --version

# Run the bot
python app.py

# Keep window open if it crashes
Write-Host "Bot exited."
Pause
