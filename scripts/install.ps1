# ── H-CLI Installer (Windows PowerShell) ──
# Alternative installation via shell functions (for users who don't use pipx)

$repoDir = Split-Path $PSScriptRoot

Write-Host "--- H-CLI Windows Installer ---" -ForegroundColor Cyan

# 1. Detect Python
$pythonCmd = "python"
if (!(Get-Command $pythonCmd -ErrorAction SilentlyContinue)) {
    $pythonCmd = "python3"
    if (!(Get-Command $pythonCmd -ErrorAction SilentlyContinue)) {
        $pythonCmd = "py"
        if (!(Get-Command $pythonCmd -ErrorAction SilentlyContinue)) {
            Write-Host "Error: Python not found. Install Python 3.9+ from https://www.python.org/" -ForegroundColor Red
            exit
        }
    }
}
Write-Host "Found Python: $(Get-Command $pythonCmd | Select-Object -ExpandProperty Source)" -ForegroundColor Gray

# 2. Install dependencies
Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
& $pythonCmd -m pip install requests beautifulsoup4 yt-dlp

# 3. Check for mpv
if (!(Get-Command mpv -ErrorAction SilentlyContinue)) {
    Write-Host "Warning: 'mpv' not found. Install it via 'winget install mpv' or from https://mpv.io/" -ForegroundColor Yellow
}

# 4. Add to PowerShell Profile
$profilePath = $PROFILE.CurrentUserCurrentHost
if (!$profilePath) { $profilePath = $PROFILE }

$profileDir = Split-Path $profilePath
if (!(Test-Path $profileDir)) {
    New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
}
if (!(Test-Path $profilePath)) {
    New-Item -ItemType File -Path $profilePath -Force | Out-Null
}

$srcDir = Join-Path $repoDir "src"

$aliasCode = @"

# --- H-CLI Aliases ---
function hcli { `$env:PYTHONPATH="$srcDir"; $pythonCmd -m hcli `$args }
function hcli360 { `$env:PYTHONPATH="$srcDir"; $pythonCmd -m hcli -q 360 `$args }
function hcli480 { `$env:PYTHONPATH="$srcDir"; $pythonCmd -m hcli -q 480 `$args }
function hcli720 { `$env:PYTHONPATH="$srcDir"; $pythonCmd -m hcli -q 720 `$args }
function hcli1080 { `$env:PYTHONPATH="$srcDir"; $pythonCmd -m hcli -q 1080 `$args }
function hclidl { `$env:PYTHONPATH="$srcDir"; $pythonCmd -m hcli -d `$args }
function hclicc { `$env:PYTHONPATH="$srcDir"; $pythonCmd -m hcli --clear-cache }
# ----------------------
"@

$currentContent = Get-Content $profilePath -ErrorAction SilentlyContinue
if (!($currentContent -match "H-CLI Aliases")) {
    Add-Content -Path $profilePath -Value $aliasCode
    Write-Host "Aliases added to $profilePath" -ForegroundColor Green
    Write-Host "Restart PowerShell or run: . `$PROFILE" -ForegroundColor Cyan
} else {
    Write-Host "H-CLI aliases already exist in your profile. Skipping." -ForegroundColor Gray
}

Write-Host ""
Write-Host "Commands:" -ForegroundColor Cyan
Write-Host "  hcli                   Interactive mode"
Write-Host "  hcli `"search term`"     Search and stream"
Write-Host "  hcli1080 `"search term`" Stream at 1080p"
Write-Host "  hclidl `"search term`"   Download mode"
Write-Host "  hclicc                 Clear stream cache"
Write-Host ""
Write-Host "Installation complete!" -ForegroundColor Green
