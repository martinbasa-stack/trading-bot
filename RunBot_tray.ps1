# ==============================
# Trading Bot Launcher (Hidden)
# ==============================

$BASE_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $BASE_DIR

$venvPath = "$BASE_DIR\.venv\Scripts\Activate.ps1"
$pythonw  = "$BASE_DIR\.venv\Scripts\trading-bot.exe" # Copy and rename the pythonw.exe

if (!(Test-Path $venvPath)) {
    [System.Windows.Forms.MessageBox]::Show(
        "Virtual environment not found!",
        "Launcher Error",
        0,
        16
    )
    exit 1
}

& $venvPath
& $pythonw tray_app.py
