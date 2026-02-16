# ── H-CLI Installer (Windows) ──
# Downloads the correct pre-built binary from GitHub Releases.
#
# Usage:
#   irm https://raw.githubusercontent.com/Thanukamax/h-cli/main/scripts/install.ps1 | iex
#   .\install.ps1
#   .\install.ps1 -Version v1.0.0

param(
    [string]$Version = "",
    [string]$InstallDir = ""
)

$ErrorActionPreference = "Stop"

$Repo = "Thanukamax/h-cli"
$Cmd = "hcli"

# ── Detect arch ───────────────────────────────────────────────────────────────
$Arch = $env:PROCESSOR_ARCHITECTURE
switch ($Arch) {
    "AMD64"  { $ArchLabel = "x86_64" }
    "x86"    { $ArchLabel = "x86_64" }   # 32-bit PS on 64-bit Windows
    default  {
        Write-Host "Error: Unsupported architecture: $Arch" -ForegroundColor Red
        Write-Host "Install via pipx instead: pipx install git+https://github.com/$Repo.git"
        exit 1
    }
}

$Artifact = "$Cmd-windows-$ArchLabel.zip"
Write-Host "Detected: Windows $ArchLabel -> $Artifact" -ForegroundColor Cyan

# ── Resolve install directory ─────────────────────────────────────────────────
if (-not $InstallDir) {
    $InstallDir = Join-Path $env:LOCALAPPDATA "Programs\$Cmd\bin"
}

# ── Resolve download URLs ────────────────────────────────────────────────────
if ($Version) {
    $BaseUrl = "https://github.com/$Repo/releases/download/$Version"
} else {
    $BaseUrl = "https://github.com/$Repo/releases/latest/download"
}

$ArtifactUrl = "$BaseUrl/$Artifact"
$ChecksumUrl = "$BaseUrl/SHA256SUMS"

# ── Download ──────────────────────────────────────────────────────────────────
$TmpDir = Join-Path ([System.IO.Path]::GetTempPath()) "hcli-install-$([System.Guid]::NewGuid().ToString('N').Substring(0,8))"
New-Item -ItemType Directory -Path $TmpDir -Force | Out-Null

try {
    Write-Host "Downloading $Artifact ..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $ArtifactUrl -OutFile (Join-Path $TmpDir $Artifact) -UseBasicParsing

    Write-Host "Downloading SHA256SUMS ..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $ChecksumUrl -OutFile (Join-Path $TmpDir "SHA256SUMS") -UseBasicParsing

    # ── Verify checksum ──────────────────────────────────────────────────────
    Write-Host "Verifying checksum ..." -ForegroundColor Yellow

    $ActualHash = (Get-FileHash (Join-Path $TmpDir $Artifact) -Algorithm SHA256).Hash.ToLower()
    $ChecksumContent = Get-Content (Join-Path $TmpDir "SHA256SUMS")
    $ExpectedLine = $ChecksumContent | Where-Object { $_ -match $Artifact }

    if (-not $ExpectedLine) {
        Write-Host "Error: $Artifact not found in SHA256SUMS" -ForegroundColor Red
        exit 1
    }

    $ExpectedHash = ($ExpectedLine -split '\s+')[0].ToLower()

    if ($ActualHash -ne $ExpectedHash) {
        Write-Host "Error: Checksum mismatch!" -ForegroundColor Red
        Write-Host "  Expected: $ExpectedHash"
        Write-Host "  Actual:   $ActualHash"
        exit 1
    }

    Write-Host "Checksum OK" -ForegroundColor Green

    # ── Extract + install ────────────────────────────────────────────────────
    Write-Host "Installing to $InstallDir ..." -ForegroundColor Yellow

    Expand-Archive -Path (Join-Path $TmpDir $Artifact) -DestinationPath $TmpDir -Force

    if (!(Test-Path $InstallDir)) {
        New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
    }

    Copy-Item -Path (Join-Path $TmpDir "$Cmd.exe") -Destination (Join-Path $InstallDir "$Cmd.exe") -Force

    Write-Host "Installed $Cmd.exe to $InstallDir" -ForegroundColor Green

    # ── PATH check ───────────────────────────────────────────────────────────
    $UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($UserPath -split ';' -notcontains $InstallDir) {
        Write-Host ""
        Write-Host "$InstallDir is not in your PATH." -ForegroundColor Yellow
        Write-Host ""

        $AddPath = Read-Host "Add it to your User PATH now? [Y/n]"
        if ($AddPath -eq "" -or $AddPath -match "^[Yy]") {
            $NewPath = "$UserPath;$InstallDir"
            [Environment]::SetEnvironmentVariable("Path", $NewPath, "User")
            Write-Host "Added to User PATH." -ForegroundColor Green
            Write-Host "Restart your terminal for the change to take effect." -ForegroundColor Cyan
        } else {
            Write-Host "To add it manually, run:" -ForegroundColor Yellow
            Write-Host "  [Environment]::SetEnvironmentVariable('Path', `$env:Path + ';$InstallDir', 'User')" -ForegroundColor White
        }
    }

} finally {
    # ── Cleanup ──────────────────────────────────────────────────────────────
    Remove-Item -Recurse -Force $TmpDir -ErrorAction SilentlyContinue
}

# ── Done ──────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Done! Run '$Cmd --help' to get started." -ForegroundColor Green
Write-Host ""
Write-Host "You also need mpv and yt-dlp installed:" -ForegroundColor Yellow
Write-Host "  winget install mpv"
Write-Host "  pip install yt-dlp"
