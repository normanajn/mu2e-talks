# stop-mu2e-talks-docker.ps1 — stop Mu2eTalks Docker containers
#
# Usage:
#   .\stop-mu2e-talks-docker.ps1 [-Volumes]
#
# Options:
#   -Volumes    Also remove data volumes (wipes the database — use with care)

param([switch]$Volumes)

$ErrorActionPreference = 'Stop'
$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
$ModeFile   = Join-Path $ScriptDir '.mu2e-talks-docker.mode'
$QuickName  = 'mu2e-talks-quick'
Set-Location $ProjectDir

function Write-Info($t)  { Write-Host "==> $t" -ForegroundColor Cyan }
function Write-Ok($t)    { Write-Host "✓  $t"  -ForegroundColor Green }
function Write-Warn($t)  { Write-Host "!  $t"  -ForegroundColor Yellow }

$mode = ''
if (Test-Path $ModeFile) { $mode = (Get-Content $ModeFile).Trim() }

# ── Compose full stack ────────────────────────────────────────────────────────
$composeRunning = $false
$composeCheck = docker compose version 2>$null
if ($LASTEXITCODE -eq 0) {
    $running = docker compose ps -q 2>$null
    if ($running) { $composeRunning = $true }
}

if ($mode -eq 'compose' -or $composeRunning) {
    Write-Info 'Stopping compose stack...'
    if ($Volumes) {
        Write-Warn 'Removing volumes (database will be wiped)...'
        docker compose down -v
        Write-Ok 'Stack stopped and volumes removed'
    } else {
        docker compose down
        Write-Ok 'Stack stopped (volumes preserved)'
    }
    Remove-Item $ModeFile -Force -ErrorAction SilentlyContinue
    exit 0
}

# ── Quick container ───────────────────────────────────────────────────────────
$exists = docker container inspect $QuickName 2>$null
if ($mode -eq $QuickName -or $exists) {
    Write-Info "Stopping quick container ($QuickName)..."
    docker rm -f $QuickName | Out-Null
    Write-Ok 'Container stopped'
    Remove-Item $ModeFile -Force -ErrorAction SilentlyContinue
    exit 0
}

Write-Warn 'No running Mu2eTalks Docker containers found.'
