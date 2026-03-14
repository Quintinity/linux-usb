#Requires -Version 5.1
<#
.SYNOPSIS
    Downloads Ubuntu 24.04.2 desktop ISO, verifies its checksum, and launches Rufus to flash a USB drive.
.DESCRIPTION
    - Downloads the ISO (~6GB) and SHA256SUMS using BITS transfer (resumable)
    - Verifies the ISO integrity against the published SHA256 checksum
    - Downloads Rufus 4.6 portable
    - Skips any file that already exists locally
    - Launches Rufus and waits for it to finish
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# --- Configuration ---
$ScriptDir      = Split-Path -Parent $MyInvocation.MyCommand.Definition
$DownloadsDir   = Join-Path $ScriptDir 'downloads'
$IsoUrl         = 'https://releases.ubuntu.com/24.04.2/ubuntu-24.04.2-desktop-amd64.iso'
$ShaUrl         = 'https://releases.ubuntu.com/24.04.2/SHA256SUMS'
$RufusUrl       = 'https://github.com/pbatard/rufus/releases/download/v4.6/rufus-4.6p.exe'
$IsoFile        = Join-Path $DownloadsDir 'ubuntu-24.04.2-desktop-amd64.iso'
$ShaFile        = Join-Path $DownloadsDir 'SHA256SUMS'
$RufusFile      = Join-Path $DownloadsDir 'rufus-4.6p.exe'

# --- Helpers ---
function Write-Step([string]$msg) {
    Write-Host "`n>>> $msg" -ForegroundColor Cyan
}

function Write-Ok([string]$msg) {
    Write-Host "    $msg" -ForegroundColor Green
}

function Write-Err([string]$msg) {
    Write-Host "    $msg" -ForegroundColor Red
}

function Get-FileIfMissing([string]$Url, [string]$Dest, [string]$Label) {
    if (Test-Path $Dest) {
        Write-Ok "$Label already exists — skipping download."
    } else {
        Write-Step "Downloading $Label ..."
        Write-Host "    Source: $Url"
        Start-BitsTransfer -Source $Url -Destination $Dest -DisplayName $Label
        Write-Ok "$Label downloaded."
    }
}

# --- Main ---
Write-Host '============================================' -ForegroundColor Yellow
Write-Host '  Ubuntu 24.04.2 USB Flash Tool' -ForegroundColor Yellow
Write-Host '============================================' -ForegroundColor Yellow

# 1. Create downloads directory
Write-Step 'Preparing downloads directory ...'
if (-not (Test-Path $DownloadsDir)) {
    New-Item -ItemType Directory -Path $DownloadsDir | Out-Null
    Write-Ok "Created $DownloadsDir"
} else {
    Write-Ok "Directory exists: $DownloadsDir"
}

# 2. Download SHA256SUMS (small, do first)
Get-FileIfMissing -Url $ShaUrl  -Dest $ShaFile  -Label 'SHA256SUMS'

# 3. Download Ubuntu ISO (~6 GB)
Get-FileIfMissing -Url $IsoUrl  -Dest $IsoFile  -Label 'Ubuntu 24.04.2 ISO'

# 4. Verify checksum
Write-Step 'Verifying ISO checksum ...'
$expectedLine = (Get-Content $ShaFile | Select-String 'ubuntu-24.04.2-desktop-amd64.iso').Line
if (-not $expectedLine) {
    Write-Err 'Could not find expected hash in SHA256SUMS file.'
    exit 1
}
$expectedHash = ($expectedLine -split '\s+')[0].Trim().ToUpper()

Write-Host '    Computing SHA-256 (this takes a minute for 6 GB) ...'
$actualHash = (Get-FileHash -Path $IsoFile -Algorithm SHA256).Hash.ToUpper()

if ($actualHash -eq $expectedHash) {
    Write-Ok "Checksum OK: $actualHash"
} else {
    Write-Err "Checksum MISMATCH!"
    Write-Err "  Expected: $expectedHash"
    Write-Err "  Actual:   $actualHash"
    Write-Err 'The ISO may be corrupt. Delete it and re-run this script.'
    exit 1
}

# 5. Download Rufus
Get-FileIfMissing -Url $RufusUrl -Dest $RufusFile -Label 'Rufus 4.6 portable'

# 6. Print Rufus instructions
Write-Host ''
Write-Host '============================================' -ForegroundColor Yellow
Write-Host '  Rufus Settings' -ForegroundColor Yellow
Write-Host '============================================' -ForegroundColor Yellow
Write-Host ''
Write-Host '  Device:             Your USB drive (check the letter!)' -ForegroundColor White
Write-Host '  Boot selection:     Disk or ISO image  ->  select the downloaded ISO' -ForegroundColor White
Write-Host '  Partition scheme:   GPT' -ForegroundColor White
Write-Host '  Target system:      UEFI (non-CSM)' -ForegroundColor White
Write-Host '  File system:        FAT32 (default)' -ForegroundColor White
Write-Host '  Everything else:    leave as default' -ForegroundColor White
Write-Host ''
Write-Host "  ISO path: $IsoFile" -ForegroundColor Gray
Write-Host ''

# 7. Launch Rufus
Write-Step 'Launching Rufus — configure and flash, then close when done ...'
Start-Process -FilePath $RufusFile -Wait

# 8. Done
Write-Host ''
Write-Host '============================================' -ForegroundColor Green
Write-Host '  Done — follow docs/BOOT-GUIDE.md' -ForegroundColor Green
Write-Host '============================================' -ForegroundColor Green
