# H-CLI

A terminal-based streaming client with a themed UI, multi-source support, and MPV playback.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

---

## Quick Start

```bash
# Install dependencies
pip install requests beautifulsoup4

# Run interactive mode
python h-cli.py

# Or search directly
python h-cli.py "search term"
```

## Requirements

- **Python 3.8+**
- **MPV** - Video player ([mpv.io](https://mpv.io))
- **yt-dlp** - Required for downloads and some external mirrors (`pip install yt-dlp`)

### Python packages

```bash
pip install requests beautifulsoup4
```

## Installation

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

### Android (Termux)
```bash
pkg install python mpv ffmpeg
pip install requests beautifulsoup4 yt-dlp
```

## Usage

```bash
# Interactive mode - prompts for search
python h-cli.py

# Direct search and stream
python h-cli.py "search term"

# Stream at 1080p
python h-cli.py "search term" -q 1080

# Download mode
python h-cli.py "search term" -d

# Clear stream cache
python h-cli.py --clear-cache
```

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
