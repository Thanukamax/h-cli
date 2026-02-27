# H-CLI

A terminal-based streaming client with a themed UI, multi-source support, and MPV playback.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

---

## Install

### One-line install (recommended)

**Linux / macOS:**
```bash
curl -fsSL https://raw.githubusercontent.com/Thanukamax/h-cli/main/scripts/install.sh | bash
```

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/Thanukamax/h-cli/main/scripts/install.ps1 | iex
```

The installer automatically detects your OS and architecture, downloads the correct binary from [GitHub Releases](https://github.com/Thanukamax/h-cli/releases/latest), verifies the SHA256 checksum, and installs to `~/.local/bin` (Linux/macOS) or `%LOCALAPPDATA%\Programs\hcli\bin` (Windows).

**Options (Linux/macOS):**
```bash
# Install a specific version
curl -fsSL ... | bash -s -- --version v1.0.0

# Install to /usr/local/bin (requires sudo)
curl -fsSL ... | bash -s -- --sudo

# Install to a custom directory
curl -fsSL ... | bash -s -- --dir /opt/bin
```

**Options (Windows):**
```powershell
# Save and run with flags
Invoke-WebRequest -Uri https://raw.githubusercontent.com/Thanukamax/h-cli/main/scripts/install.ps1 -OutFile install.ps1
.\install.ps1 -Version v1.0.0
.\install.ps1 -InstallDir "C:\Tools"
```

### Manual download

Download the latest release for your platform from [Releases](https://github.com/Thanukamax/h-cli/releases/latest):

| Platform | File |
|----------|------|
| Linux x86_64 | `hcli-linux-x86_64.tar.gz` |
| macOS arm64 (Apple Silicon) | `hcli-macos-arm64.tar.gz` |
| Windows x86_64 | `hcli-windows-x86_64.zip` |

```bash
# Linux / macOS
tar xzf hcli-linux-x86_64.tar.gz
sudo mv hcli /usr/local/bin/

# Windows — extract the zip, then add the folder to your PATH
```

#### Verify checksums

Each release includes a `SHA256SUMS` file:

```bash
# Linux
sha256sum -c SHA256SUMS --ignore-missing

# macOS
shasum -a 256 -c SHA256SUMS --ignore-missing

# Windows (PowerShell)
(Get-FileHash hcli-windows-x86_64.zip -Algorithm SHA256).Hash
# Compare with the hash in SHA256SUMS
```

### With pipx / uv (requires Python 3.9+)

```bash
pipx install git+https://github.com/Thanukamax/h-cli.git
```

or with uv:

```bash
uv tool install git+https://github.com/Thanukamax/h-cli.git
```

## Requirements

- **MPV** - Video player ([mpv.io](https://mpv.io))
- **yt-dlp** - Required for downloads and some external mirrors (`pip install yt-dlp`)

#### Optional (terminal mascot / image rendering)

- **chafa** - Terminal image renderer ([hpjansson.org/chafa](https://hpjansson.org/chafa/))
- **Pillow** and **chafa.py** are Python dependencies (auto-installed via pip/pipx/uv)
- **pyfiglet** - ASCII art text banners (auto-installed)

If these are missing, H-CLI works fine — you just won't see the mascot art.

### System Dependencies

#### Linux (Debian/Ubuntu)
```bash
sudo apt update && sudo apt install mpv ffmpeg chafa
pip install yt-dlp
```

#### Linux (Fedora)
```bash
sudo dnf install mpv ffmpeg chafa
pip install yt-dlp
```

#### Windows
```powershell
winget install mpv
choco install chafa    # or: scoop install chafa
pip install yt-dlp
```

## Commands

| Command | Description |
|---------|-------------|
| `hcli` | Interactive mode |
| `hcli "search term"` | Search and stream |
| `hcli -q 1080` | Stream at 1080p |
| `hcli -d` | Download mode |
| `hcli --clear-cache` | Clear stream cache |

## Playback Controls

| Key | Action |
|-----|--------|
| `n` / `enter` | Next episode |
| `p` | Previous episode |
| `s` | Skip to specific episode |
| `r` | Replay current |
| `d` | Download current episode |
| `q` | Quit |

### Panic Quit

Press **space 3 times within 2 seconds** at any point during the session to instantly kill the app. This works during loading screens, playback, prompts — everywhere. On trigger it kills MPV, wipes the stream cache, clears the terminal, and hard-exits.

## How It Works

1. **Search** - Scrapes search results from the configured source
2. **Episode listing** - Fetches and sorts episodes chronologically
3. **Stream extraction** - Resolves direct MP4 URLs via AJAX + base64 decoding pipeline
4. **Caching** - LRU cache (100 entries) persists resolved URLs between sessions
5. **Preloading** - Background thread resolves the next 2 episodes while you watch
6. **Playback** - Launches MPV with the resolved stream URL

## File Locations

| Path | Description |
|------|-------------|
| `~/.cache/h-cli/` | Stream URL cache (Linux) |
| `~/.h-cli/` | Stream URL cache (Windows) |
| `~/Videos/H-CLI/` | Downloaded episodes |

## Disclaimer

This tool is for educational purposes only. Not affiliated with any streaming sites.

---

Made by [Thanukamax](https://github.com/Thanukamax)
