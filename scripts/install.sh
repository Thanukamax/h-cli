#!/usr/bin/env bash
set -euo pipefail

# ── H-CLI Installer (Linux / macOS) ──
# Downloads the correct pre-built binary from GitHub Releases.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/Thanukamax/h-cli/main/scripts/install.sh | bash
#   curl -fsSL ... | bash -s -- --version v1.0.0
#   curl -fsSL ... | bash -s -- --sudo
#   curl -fsSL ... | bash -s -- --dir /opt/bin

REPO="Thanukamax/h-cli"
CMD="hcli"
VERSION=""
INSTALL_DIR="$HOME/.local/bin"
USE_SUDO=""

# ── Parse flags ───────────────────────────────────────────────────────────────
while [ $# -gt 0 ]; do
    case "$1" in
        --version|-v) VERSION="$2"; shift 2 ;;
        --sudo)       USE_SUDO="sudo"; INSTALL_DIR="/usr/local/bin"; shift ;;
        --dir)        INSTALL_DIR="$2"; shift 2 ;;
        --help|-h)
            echo "Usage: install.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --version, -v VERSION   Install a specific version (e.g. v1.0.0)"
            echo "  --sudo                  Install to /usr/local/bin (requires sudo)"
            echo "  --dir PATH              Install to a custom directory"
            echo "  --help, -h              Show this help"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# ── Detect OS + arch ─────────────────────────────────────────────────────────
OS="$(uname -s)"
ARCH="$(uname -m)"

case "$OS" in
    Linux)  PLATFORM="linux" ;;
    Darwin) PLATFORM="macos" ;;
    *)      echo "Error: Unsupported OS: $OS"; exit 1 ;;
esac

case "$ARCH" in
    x86_64|amd64)   ARCH_LABEL="x86_64" ;;
    aarch64|arm64)   ARCH_LABEL="arm64" ;;
    *)               echo "Error: Unsupported architecture: $ARCH"; exit 1 ;;
esac

# Linux arm64 builds are not currently provided
if [ "$PLATFORM" = "linux" ] && [ "$ARCH_LABEL" = "arm64" ]; then
    echo "Error: Linux arm64 binaries are not available yet."
    echo "Install via pipx instead: pipx install git+https://github.com/$REPO.git"
    exit 1
fi

ARTIFACT="${CMD}-${PLATFORM}-${ARCH_LABEL}.tar.gz"
echo "Detected: $OS $ARCH → $ARTIFACT"

# ── Resolve download URL ─────────────────────────────────────────────────────
if [ -n "$VERSION" ]; then
    BASE_URL="https://github.com/$REPO/releases/download/$VERSION"
else
    BASE_URL="https://github.com/$REPO/releases/latest/download"
fi

ARTIFACT_URL="$BASE_URL/$ARTIFACT"
CHECKSUM_URL="$BASE_URL/SHA256SUMS"

# ── Pick a download tool ─────────────────────────────────────────────────────
fetch() {
    local url="$1" dest="$2"
    if command -v curl &>/dev/null; then
        curl -fSL --progress-bar -o "$dest" "$url"
    elif command -v wget &>/dev/null; then
        wget -q --show-progress -O "$dest" "$url"
    else
        echo "Error: curl or wget is required"
        exit 1
    fi
}

# ── Download ──────────────────────────────────────────────────────────────────
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

echo "Downloading $ARTIFACT ..."
fetch "$ARTIFACT_URL" "$TMPDIR/$ARTIFACT"

echo "Downloading SHA256SUMS ..."
fetch "$CHECKSUM_URL" "$TMPDIR/SHA256SUMS"

# ── Verify checksum ──────────────────────────────────────────────────────────
echo "Verifying checksum ..."
cd "$TMPDIR"

if command -v sha256sum &>/dev/null; then
    sha256sum -c SHA256SUMS --ignore-missing --status
elif command -v shasum &>/dev/null; then
    shasum -a 256 -c SHA256SUMS --ignore-missing --status
else
    echo "Warning: No sha256sum or shasum found — skipping verification"
fi

echo "Checksum OK"

# ── Extract + install ─────────────────────────────────────────────────────────
tar xzf "$ARTIFACT"

$USE_SUDO mkdir -p "$INSTALL_DIR"
$USE_SUDO install -m 755 "$CMD" "$INSTALL_DIR/$CMD"

echo "Installed $CMD to $INSTALL_DIR/$CMD"

# ── PATH check ───────────────────────────────────────────────────────────────
if ! echo "$PATH" | tr ':' '\n' | grep -qx "$INSTALL_DIR"; then
    echo ""
    echo "WARNING: $INSTALL_DIR is not in your PATH."
    echo ""
    SHELL_NAME="$(basename "$SHELL" 2>/dev/null || echo bash)"
    case "$SHELL_NAME" in
        zsh)  RC="$HOME/.zshrc" ;;
        fish) RC="$HOME/.config/fish/config.fish" ;;
        *)    RC="$HOME/.bashrc" ;;
    esac
    if [ "$SHELL_NAME" = "fish" ]; then
        echo "Add it by running:"
        echo "  fish_add_path $INSTALL_DIR"
    else
        echo "Add it by running:"
        echo "  echo 'export PATH=\"$INSTALL_DIR:\$PATH\"' >> $RC"
        echo "  source $RC"
    fi
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "Done! Run '$CMD --help' to get started."
echo ""
echo "You also need mpv and yt-dlp installed on your system:"
case "$PLATFORM" in
    linux)
        echo "  sudo apt install mpv ffmpeg   # Debian/Ubuntu"
        echo "  sudo dnf install mpv ffmpeg   # Fedora"
        echo "  pip install yt-dlp"
        ;;
    macos)
        echo "  brew install mpv yt-dlp"
        ;;
esac
echo ""
echo "Optional (terminal mascot art):"
case "$PLATFORM" in
    linux)
        echo "  sudo apt install chafa        # Debian/Ubuntu"
        echo "  sudo dnf install chafa        # Fedora"
        ;;
    macos)
        echo "  brew install chafa"
        ;;
esac
