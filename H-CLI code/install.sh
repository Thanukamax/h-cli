#!/bin/bash

# ── H-CLI Installer (Linux / macOS / Termux) ──

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
HCLI_PATH="$SCRIPT_DIR/h-cli.py"

# Make sure it's executable
chmod +x "$HCLI_PATH"

echo "--- H-CLI Installer ---"

# 1. Detect python command
PYTHON_CMD=""
for cmd in python3 python; do
    if command -v "$cmd" &> /dev/null; then
        PYTHON_CMD="$cmd"
        break
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "Error: Python not found. Install Python 3.8+ first."
    exit 1
fi
echo "Found Python: $(command -v $PYTHON_CMD)"

# 2. Install Python dependencies
echo "Installing Python dependencies..."
$PYTHON_CMD -m pip install --user requests beautifulsoup4 yt-dlp 2>/dev/null || \
    pip install requests beautifulsoup4 yt-dlp

# 3. Check for mpv
if ! command -v mpv &> /dev/null; then
    echo "Warning: 'mpv' not found. You need it for streaming."
    echo "  Debian/Ubuntu:  sudo apt install mpv"
    echo "  Fedora:         sudo dnf install mpv"
    echo "  Termux:         pkg install mpv"
    echo "  macOS:          brew install mpv"
fi

# 4. Detect shell config file
RC_FILE="$HOME/.bashrc"
if [ -n "$ZSH_VERSION" ] || [ -f "$HOME/.zshrc" ]; then
    RC_FILE="$HOME/.zshrc"
fi

echo "Found shell config: $RC_FILE"

# 5. Check if aliases already exist
if grep -q "H-CLI Aliases" "$RC_FILE" 2>/dev/null; then
    echo "H-CLI aliases already exist in $RC_FILE. Skipping."
else
    # Backup config
    cp "$RC_FILE" "${RC_FILE}.bak"
    echo "Adding aliases..."

    {
        echo ""
        echo "# H-CLI Aliases"
        echo "alias hcli='$PYTHON_CMD \"$HCLI_PATH\"'"
        echo "alias hcli360='$PYTHON_CMD \"$HCLI_PATH\" -q 360'"
        echo "alias hcli480='$PYTHON_CMD \"$HCLI_PATH\" -q 480'"
        echo "alias hcli720='$PYTHON_CMD \"$HCLI_PATH\" -q 720'"
        echo "alias hcli1080='$PYTHON_CMD \"$HCLI_PATH\" -q 1080'"
        echo "alias hclidl='$PYTHON_CMD \"$HCLI_PATH\" -d'"
        echo "alias hclicc='$PYTHON_CMD \"$HCLI_PATH\" --clear-cache'"
    } >> "$RC_FILE"

    echo "Aliases added to $RC_FILE"
fi

echo ""
echo "---------------------------------------------------"
echo "To start using them immediately, run:"
echo "  source $RC_FILE"
echo ""
echo "Commands:"
echo "  hcli                   Interactive mode"
echo "  hcli \"search term\"     Search and stream"
echo "  hcli1080 \"search term\" Stream at 1080p"
echo "  hclidl \"search term\"   Download mode"
echo "  hclicc                 Clear stream cache"
echo "---------------------------------------------------"
