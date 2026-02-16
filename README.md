# H-CLI

A terminal-based streaming client with a themed UI, multi-source support, and MPV playback.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

---

## Quick Start

### Linux
```bash
git clone https://github.com/Thanukamax/h-cli.git
cd h-cli/H-CLI\ code
bash install.sh
source ~/.bashrc   # or: source ~/.zshrc
```

### Windows (PowerShell)
```powershell
git clone https://github.com/Thanukamax/h-cli.git
cd "h-cli\H-CLI code"
.\install.ps1
```

The installer handles everything — installs Python dependencies, checks for mpv, and adds shell aliases so you can run `hcli` from anywhere.

## Requirements

- **Python 3.8+**
- **MPV** - Video player ([mpv.io](https://mpv.io))
- **yt-dlp** - Required for downloads and some external mirrors (`pip install yt-dlp`)

## Manual Installation

If you prefer not to use the installer:

### Linux (Debian/Ubuntu)
```bash
sudo apt update && sudo apt install python3 python3-pip mpv ffmpeg
pip3 install requests beautifulsoup4 yt-dlp
```

### Linux (Fedora)
```bash
sudo dnf install python3 python3-pip mpv ffmpeg
pip3 install requests beautifulsoup4 yt-dlp
```

### Windows
```powershell
winget install mpv
pip install requests beautifulsoup4 yt-dlp
```

Then run directly with:
```bash
python "H-CLI code/h-cli.py"
```

## Commands

After running the installer:

| Command | Description |
|---------|-------------|
| `hcli` | Interactive mode |
| `hcli "search term"` | Search and stream |
| `hcli360 "search term"` | Stream at 360p |
| `hcli480 "search term"` | Stream at 480p |
| `hcli720 "search term"` | Stream at 720p |
| `hcli1080 "search term"` | Stream at 1080p |
| `hclidl "search term"` | Download mode |
| `hclicc` | Clear stream cache |

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
