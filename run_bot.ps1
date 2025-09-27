# Run the Telegram bookmark bot in a virtual environment (PowerShell)
# Usage: .\run_bot.ps1

$venvPath = "$PSScriptRoot\.venv"
if (-Not (Test-Path $venvPath)) {
    python -m venv $venvPath
}

$activate = "$venvPath\Scripts\Activate.ps1"
if (Test-Path $activate) {
    & $activate
} else {
    Write-Host "Virtual environment activate script not found; ensure Python and venv are available." -ForegroundColor Yellow
}

Write-Host "Installing dependencies..."
python -m pip install --upgrade pip
python -m pip install -r "$PSScriptRoot\telegram_bot\requirements-full.txt"

Write-Host "Make sure you created a .env file next to this script (or edit .env.example)."
Write-Host "Starting bot..."
python "$PSScriptRoot\telegram_bot\bot.py"
