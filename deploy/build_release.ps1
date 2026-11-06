#Requires -Version 5.1
<#
.SYNOPSIS
    Costruisce in locale la cartella hnbot-release/ pronta per la VM OCI.

.DESCRIPTION
    Copia shared/, telegram_bot/, webserver/ e scripts/ in una cartella pulita
    applicando le stesse esclusioni di scripts/release_oci.py: niente .env,
    sessioni Telegram, database, cache, certificati o log.

    Alla fine verifica che i file obbligatori ci siano, che non siano finiti
    segreti nella cartella e stampa le versioni dichiarate dal codice.

.PARAMETER Destination
    Cartella di output. Default: <repo>/hnbot-release

.PARAMETER Archive
    Crea anche <cartella>.zip da trasferire con scp (unzip o python3 -m zipfile sulla VM).

.PARAMETER KeepExisting
    Non cancella la cartella di output se esiste gia (default: la ricrea).

.EXAMPLE
    .\deploy\build_release.ps1

.EXAMPLE
    .\deploy\build_release.ps1 -Destination C:\temp\hnbot-release -Archive
#>
[CmdletBinding()]
param(
    [string]$Destination,
    [switch]$Archive,
    [switch]$KeepExisting
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

# --- Percorsi -----------------------------------------------------------------

$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not $Destination) {
    $Destination = Join-Path $projectRoot 'hnbot-release'
}
$destFull = [System.IO.Path]::GetFullPath($Destination).TrimEnd('\')

$components = @('shared', 'telegram_bot', 'webserver', 'scripts')

# Stesse esclusioni di release_oci.py (piu la cache di pytest).
$excludedDirs = @(
    '__pycache__', '.pytest_cache', 'db', '.sessions',
    '.venv', 'venv', 'certs', '.git'
)
$excludedFiles = @(
    '.env', '.env.*',
    '*.session', '*.session-journal',
    '*.db', '*.db-wal', '*.db-shm',
    '*.log', '*.bak', 'server.err', '*.pyc', '*.pyo'
)

$requiredFiles = @(
    'shared/database.py',
    'shared/requirements.txt',
    'telegram_bot/bot.py',
    'telegram_bot/requirements.txt',
    'webserver/server.py',
    'webserver/requirements.txt',
    'webserver/htmldata.py',
    'webserver/static/app.js',
    'webserver/locales/en.json',
    'webserver/locales/it.json'
)

# --- Controlli preliminari -------------------------------------------------------

foreach ($tool in @('robocopy')) {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        throw "Comando richiesto non trovato: $tool"
    }
}

foreach ($component in $components) {
    if (-not (Test-Path -LiteralPath (Join-Path $projectRoot $component) -PathType Container)) {
        throw "Componente mancante nel repository: $component"
    }
}

$rootTrimmed = $projectRoot.TrimEnd('\')
if ($destFull -eq $rootTrimmed) {
    throw "La destinazione non puo essere la root del progetto."
}
foreach ($component in $components) {
    $componentPath = (Join-Path $rootTrimmed $component)
    if ($destFull.StartsWith($componentPath + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "La destinazione non puo stare dentro il componente '$component'."
    }
}

# --- Costruzione ------------------------------------------------------------------

if (Test-Path -LiteralPath $destFull) {
    if ($KeepExisting) {
        Write-Host "Uso la cartella esistente: $destFull" -ForegroundColor Yellow
    }
    else {
        Write-Host "Rimuovo la release precedente: $destFull"
        Remove-Item -LiteralPath $destFull -Recurse -Force
    }
}
if (-not (Test-Path -LiteralPath $destFull)) {
    New-Item -ItemType Directory -Path $destFull | Out-Null
}

Write-Host ""
Write-Host "Costruzione release in $destFull" -ForegroundColor Cyan

foreach ($component in $components) {
    $source = Join-Path $projectRoot $component
    $target = Join-Path $destFull $component

    $arguments = @(
        $source, $target,
        '/E', '/COPY:DAT', '/DCOPY:DAT',
        '/NFL', '/NDL', '/NJH', '/NJS', '/NP',
        '/R:0', '/W:0'
    )
    $arguments += '/XD'
    $arguments += $excludedDirs
    $arguments += '/XF'
    $arguments += $excludedFiles

    & robocopy @arguments | Out-Null
    $exitCode = $LASTEXITCODE
    # robocopy: 0-7 successo (0 = niente da copiare), >=8 errore.
    if ($exitCode -ge 8) {
        throw "robocopy ha fallito su '$component' (exit code $exitCode)."
    }
    Write-Host ("  - {0,-14} copiato" -f $component) -ForegroundColor DarkGray
}

# --- Verifiche ---------------------------------------------------------------------

$missing = @()
foreach ($relative in $requiredFiles) {
    if (-not (Test-Path -LiteralPath (Join-Path $destFull $relative) -PathType Leaf)) {
        $missing += $relative
    }
}
if ($missing.Count -gt 0) {
    throw ("File obbligatori mancanti nella release: " + ($missing -join ', '))
}

$leaked = @(Get-ChildItem -LiteralPath $destFull -Recurse -File -Force | Where-Object {
        $_.Name -eq '.env' -or
        $_.Name -like '*.session*' -or
        $_.Name -like '*.db' -or
        $_.Name -like '*.db-*'
    })
if ($leaked.Count -gt 0) {
    $names = ($leaked | ForEach-Object { $_.FullName.Substring($destFull.Length + 1) }) -join ', '
    throw "File non ammessi nella release: $names"
}

function Get-DeclaredValue {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Pattern
    )

    $match = Select-String -LiteralPath $Path -Pattern $Pattern -List
    if ($null -eq $match) {
        return 'non trovato'
    }
    return $match.Matches[0].Groups[1].Value
}

$webVersion = Get-DeclaredValue -Path (Join-Path $destFull 'webserver/server.py') -Pattern '__version__\s*=\s*"([^"]+)"'
$botVersion = Get-DeclaredValue -Path (Join-Path $destFull 'telegram_bot/bot.py') -Pattern '__version__\s*=\s*"([^"]+)"'
$schemaVersion = Get-DeclaredValue -Path (Join-Path $destFull 'shared/database.py') -Pattern 'SCHEMA_VERSION\s*=\s*(\d+)'

$files = @(Get-ChildItem -LiteralPath $destFull -Recurse -File -Force)
$totalSize = [math]::Round((($files | Measure-Object -Property Length -Sum).Sum / 1KB), 1)

Write-Host ""
Write-Host "Release pronta" -ForegroundColor Green
Write-Host ("  Percorso : {0}" -f $destFull)
Write-Host ("  File     : {0}  ({1} KB)" -f $files.Count, $totalSize)
Write-Host ("  Versioni : webserver {0} | bot {1} | schema DB {2}" -f $webVersion, $botVersion, $schemaVersion)

# --- Archivio opzionale -------------------------------------------------------------

if ($Archive) {
    $archivePath = "$destFull.zip"
    if (Test-Path -LiteralPath $archivePath) {
        Remove-Item -LiteralPath $archivePath -Force
    }

    Compress-Archive -Path $destFull -DestinationPath $archivePath -CompressionLevel Optimal -Force

    $hash = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash
    $archiveSize = [math]::Round(((Get-Item -LiteralPath $archivePath).Length / 1KB), 1)
    Write-Host ("  Archivio : {0}  ({1} KB)" -f $archivePath, $archiveSize)
    Write-Host ("  SHA256   : {0}" -f $hash)
}

# --- Prossimi passi ------------------------------------------------------------------

Write-Host ""
Write-Host "Prossimi passi" -ForegroundColor Cyan
Write-Host "  1) Sulla VM, rimuovi la release precedente (scp -r anniderebbe le cartelle):"
Write-Host "       rm -rf /home/ubuntu/hnbot-release"
Write-Host "  2) Dal PC, copia la cartella:"
Write-Host ("       scp -r -i `$env:USERPROFILE\.ssh\hnbot-oci.pem ""{0}"" ubuntu@HOST:/home/ubuntu/hnbot-release" -f $destFull)
Write-Host "     oppure copia solo l'archivio e aprilo sulla VM:"
Write-Host ("       scp -i `$env:USERPROFILE\.ssh\hnbot-oci.pem ""{0}.zip"" ubuntu@HOST:~" -f $destFull)
Write-Host "       unzip -o ~/hnbot-release.zip -d ~   (oppure: python3 -m zipfile -e ~/hnbot-release.zip ~)"
Write-Host "  3) Sulla VM, verifica e applica:"
Write-Host "       python3 /home/ubuntu/release_oci.py --source /home/ubuntu/hnbot-release"
Write-Host "       sudo python3 /home/ubuntu/release_oci.py --source /home/ubuntu/hnbot-release --apply --acknowledge-telegram-linking"
