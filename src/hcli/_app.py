#!/usr/bin/env python3
"""
H-CLI (Hentai-CLI) - Terminal-based streaming client
Themed terminal UI, multi-source support, MPV playback
"""

import argparse
import atexit
import difflib
import os
import re
import shutil
import signal
import sys
import textwrap
import time
import subprocess
import threading
import json
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from typing import List, Tuple, Optional, Dict, Any

import requests
from bs4 import BeautifulSoup

try:
    import pyfiglet
    HAS_PYFIGLET = True
except ImportError:
    HAS_PYFIGLET = False

try:
    import PIL.Image
    from chafa import Canvas, CanvasConfig, PixelType
    HAS_CHAFA = True
except ImportError:
    HAS_CHAFA = False

# ============================================================================
# THEME CONFIGURATION
# ============================================================================
class Theme:
    """Terminal color theme"""

    # Colors
    PRIMARY = "\033[38;5;198m"      # Pink
    SECONDARY = "\033[38;5;213m"    # Light pink
    ACCENT = "\033[38;5;141m"       # Purple
    LIGHT_ACCENT = "\033[38;5;183m" # Light purple
    RED = "\033[38;5;196m"          # Error red
    WHITE = "\033[38;5;255m"        # Text white
    GRAY = "\033[38;5;245m"         # Muted gray
    SILVER = "\033[38;5;252m"       # Silver
    DEEP_PINK = "\033[38;5;199m"    # Deep pink
    HOT_PINK = "\033[38;5;206m"     # Hot pink
    BLUSH = "\033[38;5;218m"        # Soft blush pink
    DIM_ROSE = "\033[38;5;132m"     # Muted mauve/rose
    RESET = "\033[0m"

    # Box drawing
    H = "─"
    V = "│"
    TL = "┌"
    TR = "┐"
    BL = "└"
    BR = "┘"
    ML = "├"
    MR = "┤"

    # Symbols
    SYM_PLAY = "▶"
    SYM_CHECK = "✓"
    SYM_CROSS = "✗"
    SYM_WARN = "⚠"
    SYM_INFO = "ⓘ"
    SYM_LOADING = "⟳"
    SYM_STAR = "★"
    SYM_ARROW = "❯"
    SYM_HEART = "♥"

    # Gradient color stops (ANSI 256): deep pink → hot pink → blush → light purple → purple
    GRADIENT_STOPS = [199, 206, 218, 183, 141]

    @classmethod
    def _lerp_color(cls, c1: int, c2: int, t: float) -> int:
        """Linearly interpolate between two ANSI 256 color codes."""
        return round(c1 + (c2 - c1) * t)

    @classmethod
    def gradient(cls, text: str, stops: Optional[list] = None) -> str:
        """Apply gradient coloring across a string using ANSI 256 colors."""
        stops = stops or cls.GRADIENT_STOPS
        visible = [ch for ch in text if ch not in (" ", "\n", "\t")]
        if len(visible) <= 1:
            return f"\033[38;5;{stops[0]}m{text}{cls.RESET}"

        result = []
        vi = 0
        total = len(visible) - 1
        num_segments = len(stops) - 1

        for ch in text:
            if ch in (" ", "\n", "\t"):
                result.append(ch)
            else:
                pos = vi / total  # 0.0 → 1.0
                seg = min(int(pos * num_segments), num_segments - 1)
                local_t = (pos * num_segments) - seg
                color = cls._lerp_color(stops[seg], stops[seg + 1], local_t)
                result.append(f"\033[38;5;{color}m{ch}")
                vi += 1

        result.append(cls.RESET)
        return "".join(result)

    # -- Layout helpers ------------------------------------------------------

    @classmethod
    def get_width(cls) -> int:
        """Get terminal width."""
        try:
            return shutil.get_terminal_size().columns
        except Exception:
            return 80

    @classmethod
    def _visible_len(cls, text: str) -> int:
        """Length of text without ANSI escape codes."""
        return len(re.sub(r'\033\[[0-9;]*m', '', text))

    @classmethod
    def _center_line(cls, text: str, width: int = 0) -> str:
        """Center a line of text accounting for ANSI codes."""
        w = width or cls.get_width()
        vlen = cls._visible_len(text)
        pad = max(0, (w - vlen) // 2)
        return " " * pad + text

    @classmethod
    def _center_block(cls, block: str, width: int = 0) -> str:
        """Center each line of a multi-line string."""
        return "\n".join(cls._center_line(line, width) for line in block.split("\n"))

    @classmethod
    def _content_pad(cls) -> str:
        """Padding string for centered content container (max ~88 cols)."""
        content_w = min(cls.get_width() - 4, 88)
        return " " * max(0, (cls.get_width() - content_w) // 2)

    # -- Display methods -----------------------------------------------------

    @classmethod
    def banner(cls) -> str:
        """Generate the main banner with ASCII art, centered in terminal"""
        w = 58
        sub_text = "Your Late Night Companion"
        sub_visible = f"  {sub_text}"
        sub_pad_n = w - len(sub_visible)

        if HAS_PYFIGLET:
            art = pyfiglet.figlet_format("H-CLI", font="slant").rstrip("\n")
            art_lines = art.split("\n")
            raw = [f"{cls.PRIMARY}{cls.TL}{cls.H * w}{cls.TR}{cls.RESET}"]
            for al in art_lines:
                padded = al.ljust(w)[:w]
                raw.append(
                    f"{cls.PRIMARY}{cls.V}{cls.RESET}"
                    f"{cls.gradient(padded)}"
                    f"{cls.PRIMARY}{cls.V}{cls.RESET}"
                )
            raw.append(
                f"{cls.PRIMARY}{cls.V}{cls.RESET}"
                f"  {cls.DIM_ROSE}{sub_text}{cls.RESET}"
                f"{' ' * sub_pad_n}"
                f"{cls.PRIMARY}{cls.V}{cls.RESET}"
            )
            raw.append(f"{cls.PRIMARY}{cls.BL}{cls.H * w}{cls.BR}{cls.RESET}")
            banner_str = cls._center_block("\n".join(raw))
            return banner_str + "\n" + cls._pixel_girl(0)

        # Fallback: simple banner
        title_line = f"  {cls.ACCENT}H-CLI{cls.RESET}  {cls.DIM_ROSE}{sub_text}{cls.RESET}"
        title_pad = w - 9 - len(sub_text)
        raw = [
            f"{cls.PRIMARY}{cls.TL}{cls.H * w}{cls.TR}{cls.RESET}",
            f"{cls.PRIMARY}{cls.V}{cls.RESET}{title_line}{' ' * title_pad}{cls.PRIMARY}{cls.V}{cls.RESET}",
            f"{cls.PRIMARY}{cls.V}{cls.RESET}{' ' * w}{cls.PRIMARY}{cls.V}{cls.RESET}",
            f"{cls.PRIMARY}{cls.BL}{cls.H * w}{cls.BR}{cls.RESET}",
        ]
        banner_str = cls._center_block("\n".join(raw))
        return banner_str + "\n" + cls._pixel_girl(0)

    @classmethod
    def header(cls, text: str) -> str:
        """Create a section header with gradient, centered"""
        label = cls.gradient(text.upper())
        line = f"{cls.GRAY}{cls.TL}{cls.H} {label} {cls.GRAY}{cls.H}{cls.TR}{cls.RESET}"
        return f"\n{cls._center_line(line)}\n"

    @classmethod
    def status(cls, level: str, msg: str) -> str:
        """Status indicator: success, error, warning, info, loading"""
        indicators = {
            "success": (cls.ACCENT, cls.SYM_CHECK),
            "error": (cls.RED, cls.SYM_CROSS),
            "warning": (cls.PRIMARY, cls.SYM_WARN),
            "info": (cls.SILVER, cls.SYM_INFO),
            "loading": (cls.ACCENT, cls.SYM_LOADING),
        }
        color, sym = indicators.get(level, indicators["info"])
        pad = cls._content_pad()
        return f"{pad}{color}{sym}{cls.RESET} {cls.WHITE}{msg}{cls.RESET}"

    @classmethod
    def prompt(cls, text: str = "Enter command") -> str:
        """Styled input prompt"""
        pad = cls._content_pad()
        return f"\n{pad}{cls.ACCENT}{cls.SYM_ARROW}{cls.RESET} {cls.PRIMARY}{text}{cls.RESET}: "

    @classmethod
    def progress_bar(cls, current: int, total: int, width: int = 30) -> str:
        """Progress bar"""
        filled = int(width * current / total) if total > 0 else 0
        bar = f"{cls.PRIMARY}[{cls.ACCENT}{'■' * filled}{cls.GRAY}{'□' * (width - filled)}{cls.PRIMARY}]{cls.RESET}"
        return f"{bar} {cls.ACCENT}{current}{cls.GRAY}/{cls.ACCENT}{total}{cls.RESET}"

    @classmethod
    def divider(cls) -> str:
        """Section divider, centered"""
        line = f"{cls.PRIMARY}{cls.H * 60}{cls.RESET}"
        return f"\n{cls._center_line(line)}\n"

    # -- Pixel art mascot (chafa) -------------------------------------------

    _mascot_cache: Dict[int, str] = {}   # frame -> rendered string
    _mascot_height: int = 0              # line count of rendered art

    @classmethod
    def _render_sprite(cls, path: str, width: int = 22) -> str:
        """Render a PNG sprite to terminal art via chafa. Returns raw string."""
        img = PIL.Image.open(path).convert("RGBA")
        pixels = list(img.tobytes())
        config = CanvasConfig()
        config.width = width
        config.height = width
        config.calc_canvas_geometry(img.width, img.height, 1 / 2)
        canvas = Canvas(config)
        canvas.draw_all_pixels(
            PixelType.CHAFA_PIXEL_RGBA8_UNASSOCIATED,
            pixels, img.width, img.height, img.width * 4,
        )
        return canvas.print().decode()

    @classmethod
    def _load_mascot(cls) -> None:
        """Pre-render all 3 mascot frames and cache them."""
        if cls._mascot_cache:
            return
        base = getattr(sys, '_MEIPASS', os.path.dirname(__file__))
        assets = os.path.join(base, "hcli", "assets") if hasattr(sys, '_MEIPASS') else os.path.join(os.path.dirname(__file__), "assets")
        frames = {
            0: os.path.join(assets, "mascot.png"),
            1: os.path.join(assets, "mascot_blink.png"),
            2: os.path.join(assets, "mascot_heart.png"),
        }
        for idx, path in frames.items():
            if os.path.isfile(path):
                cls._mascot_cache[idx] = cls._render_sprite(path)
        if cls._mascot_cache:
            cls._mascot_height = cls._mascot_cache[0].count("\n") + 1

    @classmethod
    def _pixel_girl(cls, frame: int = 0) -> str:
        """Get mascot art for a frame (0=idle, 1=blink, 2=heart), centered."""
        if not HAS_CHAFA:
            return ""
        cls._load_mascot()
        raw = cls._mascot_cache.get(frame, cls._mascot_cache.get(0, ""))
        if not raw:
            return ""
        return cls._center_block(raw)


# ============================================================================
# ANIMATED SPINNER
# ============================================================================
class Spinner:
    """Animated terminal spinner with pixel-art mascot."""
    BRAILLE = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    # Idle animation cycle: idle×6 → blink×1 → idle×4 → heart×2
    _CYCLE = [0]*6 + [1] + [0]*4 + [2]*2

    def __init__(self, message: str, done_message: str = ""):
        self.message = message
        self.done_message = done_message
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._use_art = HAS_CHAFA

    def __enter__(self):
        self._stop.clear()
        # Pre-load mascot frames (populates Theme._mascot_height)
        if self._use_art:
            try:
                Theme._load_mascot()
            except Exception:
                self._use_art = False
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_):
        self._stop.set()
        if self._thread:
            self._thread.join()
        if self._use_art and Theme._mascot_height:
            # Clear the art + message lines
            total = Theme._mascot_height + 1
            for _ in range(total):
                sys.stdout.write("\033[2K\033[1A")
            sys.stdout.write("\033[2K\r")
        else:
            sys.stdout.write("\r\033[K")
        sys.stdout.flush()
        if self.done_message:
            print(Theme.status("success", self.done_message))

    def _spin(self):
        if self._use_art and Theme._mascot_height:
            self._spin_art()
        else:
            self._spin_simple()

    def _spin_simple(self):
        """Fallback: single-line braille spinner."""
        i = 0
        pad = Theme._content_pad()
        while not self._stop.is_set():
            frame = self.BRAILLE[i % len(self.BRAILLE)]
            sys.stdout.write(
                f"\r{pad}{Theme.ACCENT}{frame}{Theme.RESET} "
                f"{Theme.WHITE}{self.message}{Theme.RESET}"
            )
            sys.stdout.flush()
            i += 1
            self._stop.wait(0.08)

    def _spin_art(self):
        """Pixel-art mascot animation with loading message below."""
        art_h = Theme._mascot_height
        cycle_i = 0
        braille_i = 0

        # Reserve vertical space
        sys.stdout.write("\n" * (art_h + 1))
        sys.stdout.flush()

        while not self._stop.is_set():
            art_idx = self._CYCLE[cycle_i % len(self._CYCLE)]
            art = Theme._pixel_girl(art_idx)
            braille = self.BRAILLE[braille_i % len(self.BRAILLE)]

            # Move cursor up to top of art region
            sys.stdout.write(f"\033[{art_h + 1}A")
            for line in art.split("\n"):
                sys.stdout.write(f"\033[2K{line}\n")
            # Message line below art
            pad = Theme._content_pad()
            sys.stdout.write(
                f"\033[2K{pad}{Theme.ACCENT}{braille}{Theme.RESET} "
                f"{Theme.WHITE}{self.message}{Theme.RESET}"
            )
            sys.stdout.flush()

            braille_i += 1
            cycle_i += 1
            self._stop.wait(0.3)


# ============================================================================
# CONFIGURATION
# ============================================================================
class Config:
    """Global configuration"""

    SOURCES: Dict[str, Dict[str, Any]] = {
        "hm": {
            "name": "HentaiMama",
            "base_url": "https://hentaimama.io",
            "search_selector": ".search-page .result-item",
            "episode_selector": "#episodes article.item.se.episodes",
        },
    }

    DEFAULT_QUALITY = "720"
    DOWNLOAD_DIR = os.path.normpath(os.path.expanduser("~/Videos/H-CLI"))

    if os.name == "nt":
        CACHE_DIR = os.path.expanduser("~/.h-cli")
    else:
        CACHE_DIR = os.path.expanduser("~/.cache/h-cli")

    STREAM_CACHE_FILE = os.path.join(CACHE_DIR, "stream_cache.json")
    DATA_CACHE_FILE = os.path.join(CACHE_DIR, "data_cache.json")

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }


# ============================================================================
# CACHE
# ============================================================================
class StreamCache:
    """LRU cache for stream URLs (thread-safe)"""

    def __init__(self, max_size: int = 100):
        self.cache: OrderedDict = OrderedDict()
        self.max_size = max_size
        self._lock = threading.Lock()
        self._load()

    def get(self, url: str) -> Optional[str]:
        with self._lock:
            if url in self.cache:
                self.cache.move_to_end(url)
                return self.cache[url]
            return None

    def put(self, url: str, stream_url: str):
        with self._lock:
            if url in self.cache:
                self.cache.move_to_end(url)
            else:
                if len(self.cache) >= self.max_size:
                    self.cache.popitem(last=False)
                self.cache[url] = stream_url
            self._save()

    def _save(self):
        try:
            os.makedirs(Config.CACHE_DIR, exist_ok=True)
            snapshot = list(self.cache.items())
            with open(Config.STREAM_CACHE_FILE, "w") as f:
                json.dump(snapshot, f)
        except OSError:
            pass

    def _load(self):
        try:
            if os.path.exists(Config.STREAM_CACHE_FILE):
                with open(Config.STREAM_CACHE_FILE, "r") as f:
                    items = json.load(f)
                    self.cache = OrderedDict(items[-self.max_size :])
        except (OSError, json.JSONDecodeError):
            self.cache = OrderedDict()


class DataCache:
    """Persistent multi-layer cache with TTL for scraped data (thread-safe)."""

    TTL = {
        "search": 3600,       # 1 hour
        "series_info": 86400, # 24 hours
        "episodes": 21600,    # 6 hours
        "registry": 2592000,  # 30 days
    }
    MAX_ENTRIES = 750

    def __init__(self):
        self._data: OrderedDict = OrderedDict()
        self._lock = threading.Lock()
        self._load()

    def get(self, namespace: str, key: str) -> Optional[Any]:
        with self._lock:
            full_key = f"{namespace}:{key}"
            entry = self._data.get(full_key)
            if entry is None:
                return None
            if time.time() - entry["ts"] > entry["ttl"]:
                del self._data[full_key]
                return None
            self._data.move_to_end(full_key)
            return entry["val"]

    def has(self, namespace: str, key: str) -> bool:
        """Check if a valid (non-expired) entry exists without fetching."""
        with self._lock:
            full_key = f"{namespace}:{key}"
            entry = self._data.get(full_key)
            if entry is None:
                return False
            if time.time() - entry["ts"] > entry["ttl"]:
                del self._data[full_key]
                return False
            return True

    def put(self, namespace: str, key: str, value: Any):
        with self._lock:
            full_key = f"{namespace}:{key}"
            ttl = self.TTL.get(namespace, 3600)
            self._data[full_key] = {"val": value, "ts": time.time(), "ttl": ttl}
            self._data.move_to_end(full_key)
            self._evict()
            self._save()

    def scan(self, namespace: str) -> List[Any]:
        """Return all valid values for a namespace."""
        with self._lock:
            results = []
            now = time.time()
            prefix = f"{namespace}:"
            for key, entry in self._data.items():
                if key.startswith(prefix) and now - entry["ts"] <= entry["ttl"]:
                    results.append(entry["val"])
            return results

    def _evict(self):
        now = time.time()
        expired = [k for k, v in self._data.items() if now - v["ts"] > v["ttl"]]
        for k in expired:
            del self._data[k]
        while len(self._data) > self.MAX_ENTRIES:
            self._data.popitem(last=False)

    def clear(self):
        with self._lock:
            self._data = OrderedDict()
            self._save()

    def stats(self) -> Dict[str, int]:
        """Count valid entries per namespace."""
        with self._lock:
            counts: Dict[str, int] = {}
            now = time.time()
            for key, entry in self._data.items():
                if now - entry["ts"] <= entry["ttl"]:
                    ns = key.split(":", 1)[0]
                    counts[ns] = counts.get(ns, 0) + 1
            return counts

    def _save(self):
        try:
            os.makedirs(Config.CACHE_DIR, exist_ok=True)
            snapshot = list(self._data.items())
            with open(Config.DATA_CACHE_FILE, "w") as f:
                json.dump(snapshot, f)
        except OSError:
            pass

    def _load(self):
        try:
            if os.path.exists(Config.DATA_CACHE_FILE):
                with open(Config.DATA_CACHE_FILE, "r") as f:
                    items = json.load(f)
                self._data = OrderedDict(items[-self.MAX_ENTRIES:])
        except (OSError, json.JSONDecodeError):
            self._data = OrderedDict()


# ============================================================================
# UTILITIES
# ============================================================================
class Utils:
    """Helper functions"""

    @staticmethod
    def clear_screen():
        os.system("cls" if os.name == "nt" else "clear")

    @staticmethod
    def sanitize_filename(name: str) -> str:
        sanitized = re.sub(r'[\\/:*?"<>|]', "_", name).strip(" .")
        sanitized = re.sub(r"_+", "_", sanitized)
        return sanitized or "untitled"

    @staticmethod
    def extract_episode_number(title: str, url: str) -> int:
        patterns = [
            r"episode\s*[-]?\s*(\d+)",
            r"ep\s*[-]?\s*(\d+)",
            r"(\d{2,})\s*$",
            r"\b(\d{2,})\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                return int(match.group(1))
        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return 999999

    @staticmethod
    def fetch_soup(url: str, timeout: int = 10) -> BeautifulSoup:
        """Fetch page and return BeautifulSoup, with curl fallback"""
        try:
            resp = requests.get(url, headers=Config.HEADERS, timeout=timeout)
            if resp.status_code == 200:
                return BeautifulSoup(resp.text, "html.parser")
        except requests.exceptions.RequestException:
            pass

        # curl fallback
        try:
            cmd = ["curl", "-s", "-L", "-m", str(timeout),
                   "-H", f"User-Agent: {Config.HEADERS['User-Agent']}", url]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 2)
            if result.returncode == 0:
                return BeautifulSoup(result.stdout, "html.parser")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return BeautifulSoup("", "html.parser")


# ============================================================================
# PANIC QUIT  —  background keypress monitor (space x3 within 2s = kill all)
# ============================================================================
class PanicQuit:
    """3 space keypresses within WINDOW seconds = emergency exit."""

    _timestamps: List[float] = []
    WINDOW = 2.0

    @classmethod
    def on_key(cls, ch: str):
        if ch == ' ':
            now = time.time()
            cls._timestamps.append(now)
            cls._timestamps = [t for t in cls._timestamps
                               if now - t <= cls.WINDOW]
            if len(cls._timestamps) >= 3:
                cls._emergency_quit()
        else:
            cls._timestamps.clear()

    @classmethod
    def _emergency_quit(cls):
        # Restore terminal FIRST so the shell isn't left in raw mode
        _InputReader.restore_terminal()

        # Kill any MPV we spawned
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/IM", "mpv.exe"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.run(["pkill", "-f", "mpv"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            pass

        # Wipe caches
        for cache_file in (Config.STREAM_CACHE_FILE, Config.DATA_CACHE_FILE):
            try:
                if os.path.exists(cache_file):
                    os.remove(cache_file)
            except OSError:
                pass

        # Clear screen and hard exit — no traceback, no atexit
        os.system("cls" if os.name == "nt" else "clear")
        os._exit(0)


class _InputReader:
    """Owns stdin in cbreak mode via a background thread.

    * Always monitors every keypress for PanicQuit.
    * When a prompt is active, builds a line buffer and returns it.
    * When no prompt is active, keypresses are swallowed (Ctrl-C still works).
    """

    _old_termios = None
    _buf: List[str] = []
    _ready = threading.Event()
    _active = False
    _ctrl_c = False
    _lock = threading.Lock()

    # ── bootstrap ──────────────────────────────────────────────────────

    @classmethod
    def start(cls):
        if not sys.stdin.isatty():
            return
        if os.name == "nt":
            threading.Thread(target=cls._win_loop, daemon=True).start()
        else:
            cls._init_unix()
            threading.Thread(target=cls._unix_loop, daemon=True).start()

    @classmethod
    def _init_unix(cls):
        import termios
        fd = sys.stdin.fileno()
        cls._old_termios = termios.tcgetattr(fd)
        new = termios.tcgetattr(fd)
        # Raw-ish: no canonical mode, no echo, no signal chars (we handle them)
        new[3] &= ~(termios.ICANON | termios.ECHO | termios.ISIG)
        new[6][termios.VMIN] = 1
        new[6][termios.VTIME] = 0
        termios.tcsetattr(fd, termios.TCSAFLUSH, new)
        atexit.register(cls.restore_terminal)

    @classmethod
    def restore_terminal(cls):
        if cls._old_termios is not None:
            import termios
            try:
                termios.tcsetattr(sys.stdin.fileno(),
                                  termios.TCSADRAIN, cls._old_termios)
            except Exception:
                pass
            cls._old_termios = None

    # ── reader loops ───────────────────────────────────────────────────

    @classmethod
    def _unix_loop(cls):
        import select as sel
        try:
            while True:
                try:
                    ch = sys.stdin.read(1)
                except OSError:
                    continue
                if not ch:
                    break

                PanicQuit.on_key(ch)

                with cls._lock:
                    if not cls._active:
                        # No prompt — Ctrl-C still raises in main thread
                        if ch == '\x03':
                            os.kill(os.getpid(), signal.SIGINT)
                        continue

                    # ── building a line for the active prompt ──
                    if ch in ('\r', '\n'):
                        cls._active = False
                        sys.stdout.write('\n')
                        sys.stdout.flush()
                        cls._ready.set()
                    elif ch in ('\x7f', '\x08'):       # backspace
                        if cls._buf:
                            cls._buf.pop()
                            sys.stdout.write('\b \b')
                            sys.stdout.flush()
                    elif ch == '\x03':                  # Ctrl-C
                        cls._ctrl_c = True
                        cls._active = False
                        cls._buf.clear()
                        sys.stdout.write('\n')
                        sys.stdout.flush()
                        cls._ready.set()
                    elif ch == '\x04':                  # Ctrl-D (EOF)
                        cls._ctrl_c = True
                        cls._active = False
                        cls._buf.clear()
                        cls._ready.set()
                    elif ch == '\x1b':                  # escape sequence
                        while sel.select([sys.stdin], [], [], 0.05)[0]:
                            sys.stdin.read(1)
                    elif 32 <= ord(ch) < 127:           # printable ASCII
                        cls._buf.append(ch)
                        sys.stdout.write(ch)
                        sys.stdout.flush()
        except Exception:
            pass

    @classmethod
    def _win_loop(cls):
        import msvcrt
        try:
            while True:
                if msvcrt.kbhit():
                    ch = msvcrt.getwch()
                    PanicQuit.on_key(ch)
                    with cls._lock:
                        if not cls._active:
                            if ch == '\x03':
                                os.kill(os.getpid(), signal.SIGINT)
                            continue
                        if ch in ('\r', '\n'):
                            cls._active = False
                            sys.stdout.write('\n')
                            sys.stdout.flush()
                            cls._ready.set()
                        elif ch == '\x08':
                            if cls._buf:
                                cls._buf.pop()
                                sys.stdout.write('\b \b')
                                sys.stdout.flush()
                        elif ch == '\x03':
                            cls._ctrl_c = True
                            cls._active = False
                            cls._buf.clear()
                            cls._ready.set()
                        elif ch >= ' ':
                            cls._buf.append(ch)
                            sys.stdout.write(ch)
                            sys.stdout.flush()
                else:
                    time.sleep(0.02)
        except Exception:
            pass

    # ── public interface ───────────────────────────────────────────────

    @classmethod
    def get_line(cls, prompt: str = "") -> str:
        # Fallback when stdin is not a terminal (piped input)
        if cls._old_termios is None and os.name != "nt":
            return input(prompt)

        sys.stdout.write(prompt)
        sys.stdout.flush()

        with cls._lock:
            cls._buf.clear()
            cls._ready.clear()
            cls._ctrl_c = False
            cls._active = True

        # Periodic timeout so the main thread can still receive signals
        while not cls._ready.wait(timeout=0.2):
            pass

        with cls._lock:
            cls._active = False
            line = ''.join(cls._buf)
            cls._buf.clear()
            ctrl_c = cls._ctrl_c
            cls._ctrl_c = False

        if ctrl_c:
            raise KeyboardInterrupt
        return line


def safe_input(prompt: str = "") -> str:
    """Drop-in input() replacement routed through the background reader."""
    return _InputReader.get_line(prompt)


# ============================================================================
# STREAM EXTRACTOR
# ============================================================================
class StreamExtractor:
    """Extract playable stream URLs from episode pages via AJAX + base64 pipeline"""

    cache = StreamCache()

    @classmethod
    def extract(cls, episode_url: str) -> str:
        """Extract stream URL - checks cache first"""
        cached = cls.cache.get(episode_url)
        if cached:
            return cached

        stream = cls._extract_fresh(episode_url)
        if stream and stream != episode_url:
            cls.cache.put(episode_url, stream)
        return stream

    @classmethod
    def _extract_fresh(cls, url: str) -> str:
        """Extract direct MP4 URL from episode page"""
        import base64

        if url.endswith((".m3u8", ".mp4", ".mkv")):
            return url

        # Step 1: Get the episode post ID
        soup = Utils.fetch_soup(url)
        post_id_el = soup.select_one('input[name="idpost"]')
        if not post_id_el:
            return url
        post_id = post_id_el.get("value", "")
        if not post_id:
            return url

        # Step 2: AJAX call to get player iframe HTML
        try:
            resp = requests.post(
                "https://hentaimama.io/wp-admin/admin-ajax.php",
                data={"action": "get_player_contents", "a": post_id},
                headers={**Config.HEADERS, "Referer": url},
                timeout=10,
            )
            mirrors = resp.json()
        except (requests.RequestException, json.JSONDecodeError):
            return url

        if not isinstance(mirrors, list) or not mirrors:
            return url

        # Step 3: Try each mirror, prefer self-hosted (new2.php / newjav.php)
        for mirror_html in mirrors:
            iframe_match = re.search(r'src=["\']([^"\']+)["\']', mirror_html)
            if not iframe_match:
                continue
            iframe_src = iframe_match.group(1)

            # Self-hosted mirrors with base64 param
            b64_match = re.search(r'[?&]p=([A-Za-z0-9+/=]+)', iframe_src)
            if b64_match and ("new2.php" in iframe_src or "newjav.php" in iframe_src):
                try:
                    decoded = base64.b64decode(b64_match.group(1)).decode("utf-8")
                except Exception:
                    continue

                # Fetch the embed page to get direct MP4 URL
                embed_text = cls._fetch_embed_page(iframe_src, url)
                if embed_text:
                    file_match = re.search(r'file:\s*["\']([^"\']+)["\']', embed_text)
                    if file_match:
                        return file_match.group(1)

        # Step 4: Try external embeds with yt-dlp
        for mirror_html in mirrors:
            iframe_match = re.search(r'src=["\']([^"\']+)["\']', mirror_html)
            if iframe_match:
                ext_url = iframe_match.group(1)
                if "hentaimama.io" not in ext_url:
                    result = cls._ytdlp_fallback(ext_url)
                    if result != ext_url:
                        return result

        return url

    @staticmethod
    def _fetch_embed_page(embed_url: str, referer: str) -> str:
        """Fetch embed page HTML, with curl fallback for slow responses"""
        # Try requests first
        try:
            resp = requests.get(
                embed_url,
                headers={**Config.HEADERS, "Referer": referer},
                timeout=20,
            )
            if resp.status_code == 200 and resp.text:
                return resp.text
        except requests.RequestException:
            pass

        # Curl fallback
        try:
            cmd = [
                "curl", "-s", "-L", "-m", "25",
                "-H", f"User-Agent: {Config.HEADERS['User-Agent']}",
                "-H", f"Referer: {referer}",
                embed_url,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return result.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        return ""

    @staticmethod
    def _ytdlp_fallback(url: str) -> str:
        """Last resort: use yt-dlp to get stream URL"""
        try:
            cmd = [
                "yt-dlp", "--get-url", "--quiet",
                "--no-check-certificates",
                "--user-agent", Config.HEADERS["User-Agent"],
                url,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if line.startswith("http"):
                        return line
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return url


# ============================================================================
# PRELOADER
# ============================================================================
class Preloader:
    """Background preload next episodes for instant playback"""

    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def preload(self, episodes: List[Tuple[str, str]], current_idx: int):
        """Preload next 2 episodes in background"""
        self.stop()
        self._stop.clear()

        urls = [ep[1] for ep in episodes[current_idx + 1 : current_idx + 3]]
        if not urls:
            return

        def worker():
            for url in urls:
                if self._stop.is_set():
                    break
                StreamExtractor.extract(url)

        self._thread = threading.Thread(target=worker, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1)


# ============================================================================
# BACKGROUND PREFETCHER
# ============================================================================
class BackgroundPrefetcher:
    """Speculatively prefetch series pages and streams in background threads."""

    def __init__(self, max_workers: int = 3):
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._futures: list = []

    def prefetch_series_pages(self, results: List[Tuple[str, str]],
                              scraper: "Scraper", max_items: int = 5):
        """Prefetch series pages for top N search results (skips cached)."""
        self._cancel_pending()
        for _, url in results[:max_items]:
            if scraper.cache.has("series_info", url) and scraper.cache.has("episodes", url):
                continue
            fut = self._executor.submit(self._safe_fetch_series, scraper, url)
            self._futures.append(fut)

    def prefetch_streams(self, episodes: List[Tuple[str, str]], max_items: int = 3):
        """Prefetch stream URLs for first N episodes (skips cached)."""
        self._cancel_pending()
        for _, url in episodes[:max_items]:
            if StreamExtractor.cache.get(url) is not None:
                continue
            fut = self._executor.submit(self._safe_extract_stream, url)
            self._futures.append(fut)

    def _cancel_pending(self):
        """Cancel queued-but-not-started futures."""
        for fut in self._futures:
            fut.cancel()
        self._futures.clear()

    def shutdown(self):
        """Cancel pending work and shut down the executor."""
        self._cancel_pending()
        self._executor.shutdown(wait=False)

    @staticmethod
    def _safe_fetch_series(scraper: "Scraper", url: str):
        try:
            scraper._fetch_series_page(url)
        except Exception:
            pass  # Silent failure — worst case: user sees normal spinner

    @staticmethod
    def _safe_extract_stream(url: str):
        try:
            StreamExtractor.extract(url)
        except Exception:
            pass


# ============================================================================
# SCRAPER
# ============================================================================
class Scraper:
    """Search and fetch episode lists from HentaiMama"""

    cache = DataCache()

    def __init__(self, source_key: str = "hm"):
        self.source = Config.SOURCES[source_key]
        self.base_url = self.source["base_url"]

    def search(self, query: str) -> List[Tuple[str, str]]:
        """Search for series, returns list of (title, url)"""
        cache_key = f"{self.base_url}:{query}"
        cached = self.cache.get("search", cache_key)
        if cached is not None:
            return cached

        url = f"{self.base_url}/?s={query.replace(' ', '+')}"
        soup = Utils.fetch_soup(url)

        results = []
        seen: set = set()

        for item in soup.select(self.source["search_selector"])[:15]:
            title_el = item.select_one(".title a")
            if not title_el:
                continue
            href = title_el.get("href", "")
            title = title_el.get_text(strip=True)
            if href and href not in seen:
                seen.add(href)
                # Grab extra metadata
                year_el = item.select_one(".meta .year")
                rating_el = item.select_one(".meta .rating")
                year = year_el.get_text(strip=True) if year_el else ""
                rating = rating_el.get_text(strip=True) if rating_el else ""
                suffix = ""
                if year:
                    suffix += f" ({year})"
                if rating:
                    suffix += f" [{rating}]"
                results.append((f"{title}{suffix}", href))

        results.sort(key=lambda r: self._relevance_score(query, r[0]), reverse=True)
        self.cache.put("search", cache_key, results)
        return results

    @staticmethod
    def _relevance_score(query: str, title: str) -> float:
        """Score how relevant a title is to the query (0.0–1.0)."""
        cleaned = re.sub(r"\s*\(\d{4}\)", "", title)
        cleaned = re.sub(r"\s*\[[^\]]*\]", "", cleaned)
        q = query.lower()
        t = cleaned.lower()
        q_tokens = re.split(r"[\s\W]+", q)
        t_tokens = re.split(r"[\s\W]+", t)
        q_tokens = [tok for tok in q_tokens if tok]
        t_tokens = [tok for tok in t_tokens if tok]
        if not q_tokens:
            return 0.0
        scores = []
        for qt in q_tokens:
            if qt in t:
                scores.append(1.0)
            elif t_tokens:
                best = max(
                    difflib.SequenceMatcher(None, qt, tt).ratio()
                    for tt in t_tokens
                )
                scores.append(best)
            else:
                scores.append(0.0)
        return sum(scores) / len(scores)

    def _build_word_bank(self, current_results: List[Tuple[str, str]]) -> set:
        """Collect known words from all cached data and current results."""
        titles: List[str] = []
        # Registry entries (30-day cache of browsed titles)
        for entry in self.cache.scan("registry"):
            if isinstance(entry, dict) and entry.get("title"):
                titles.append(entry["title"])
        # Past search results cached locally
        for cached_list in self.cache.scan("search"):
            if isinstance(cached_list, list):
                for item in cached_list:
                    if isinstance(item, (list, tuple)) and len(item) >= 1:
                        titles.append(str(item[0]))
        # Series info titles
        for info in self.cache.scan("series_info"):
            if isinstance(info, dict) and info.get("title"):
                titles.append(info["title"])
        # Current search results
        for title, _ in current_results:
            titles.append(title)
        words: set = set()
        for t in titles:
            for tok in re.split(r"[\s\W]+", t.lower()):
                if len(tok) >= 2:
                    words.add(tok)
        return words

    @staticmethod
    def _fuzzy_correct(query: str, word_bank: set) -> Optional[str]:
        """Attempt to correct a misspelled query using known words."""
        tokens = re.split(r"[\s]+", query.lower())
        tokens = [tok for tok in tokens if tok]
        if not tokens or not word_bank:
            return None
        corrected = []
        changed = False
        bank_list = list(word_bank)
        for tok in tokens:
            if tok in word_bank:
                corrected.append(tok)
                continue
            matches = difflib.get_close_matches(tok, bank_list, n=1, cutoff=0.5)
            if matches and matches[0] != tok:
                corrected.append(matches[0])
                changed = True
            else:
                corrected.append(tok)
        return " ".join(corrected) if changed else None

    def _local_fuzzy_search(self, query: str) -> List[Tuple[str, str]]:
        """Last-resort search: score every cached title against the query."""
        candidates: List[Tuple[str, str]] = []
        seen_urls: set = set()
        # Gather from registry
        for entry in self.cache.scan("registry"):
            if isinstance(entry, dict) and entry.get("title") and entry.get("url"):
                url = entry["url"]
                if url not in seen_urls:
                    seen_urls.add(url)
                    candidates.append((entry["title"], url))
        # Gather from past search results
        for cached_list in self.cache.scan("search"):
            if isinstance(cached_list, list):
                for item in cached_list:
                    if isinstance(item, (list, tuple)) and len(item) >= 2:
                        url = str(item[1])
                        if url not in seen_urls:
                            seen_urls.add(url)
                            candidates.append((str(item[0]), url))
        if not candidates:
            return []
        scored = [(self._relevance_score(query, title), title, url)
                  for title, url in candidates]
        scored.sort(key=lambda x: x[0], reverse=True)
        # Return anything above a very low threshold (letters vaguely overlap)
        return [(title, url) for score, title, url in scored[:15] if score > 0.5]

    def _parse_series_info(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Parse series metadata from a BeautifulSoup object (no HTTP)."""
        info: Dict[str, Any] = {"title": "", "description": "", "genres": [],
                                 "studio": "", "status": "", "date": ""}

        paragraphs = soup.select(".wp-content p")
        info["description"] = "\n".join(
            p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)
        )

        info["genres"] = [a.get_text(strip=True) for a in soup.select(".sgeneros a")]

        fields = [s.get_text(strip=True) for s in soup.select(".custom_fields span.valor")]
        if len(fields) >= 1:
            info["title"] = fields[0]
        if len(fields) >= 2:
            info["studio"] = fields[1]
        if len(fields) >= 3:
            info["date"] = fields[2]
        if len(fields) >= 5:
            info["status"] = fields[4]

        return info

    def _parse_episodes(self, soup: BeautifulSoup) -> List[Tuple[str, str]]:
        """Parse episode list from a BeautifulSoup object (no HTTP)."""
        episodes = []

        for article in soup.select(self.source["episode_selector"]):
            link = article.select_one(".season_m a")
            if not link:
                continue
            href = link.get("href", "")
            ep_label = link.select_one(".c")
            ep_name = ep_label.get_text(strip=True) if ep_label else "Episode"
            if href:
                episodes.append((ep_name, href))

        # Episodes come newest-first from the site, reverse for sequential order
        episodes.reverse()
        return episodes

    def _fetch_series_page(self, series_url: str):
        """Fetch series page once, parse and cache both info + episodes."""
        # Skip if both are already cached
        if self.cache.has("series_info", series_url) and self.cache.has("episodes", series_url):
            return

        soup = Utils.fetch_soup(series_url, timeout=12)

        if not self.cache.has("series_info", series_url):
            info = self._parse_series_info(soup)
            self.cache.put("series_info", series_url, info)

        if not self.cache.has("episodes", series_url):
            episodes = self._parse_episodes(soup)
            self.cache.put("episodes", series_url, episodes)

        # Register in persistent registry
        self._register_series(series_url)

    def get_series_info(self, series_url: str) -> Dict[str, Any]:
        """Get series description, genres, metadata"""
        cached = self.cache.get("series_info", series_url)
        if cached is not None:
            return cached

        # Unified fetch populates both caches
        self._fetch_series_page(series_url)
        result = self.cache.get("series_info", series_url)
        return result if result is not None else {
            "title": "", "description": "", "genres": [],
            "studio": "", "status": "", "date": ""
        }

    def get_episodes(self, series_url: str) -> List[Tuple[str, str]]:
        """Get all episodes for a series, returns sorted list of (title, url)"""
        cached = self.cache.get("episodes", series_url)
        if cached is not None:
            return cached

        # Unified fetch populates both caches
        self._fetch_series_page(series_url)
        result = self.cache.get("episodes", series_url)
        return result if result is not None else []

    def _register_series(self, series_url: str):
        """Store a lightweight registry entry for the series (30-day TTL)."""
        info = self.cache.get("series_info", series_url)
        episodes = self.cache.get("episodes", series_url)
        if not info:
            return
        entry = {
            "title": info.get("title", ""),
            "url": series_url,
            "genres": info.get("genres", []),
            "studio": info.get("studio", ""),
            "episode_count": len(episodes) if episodes else 0,
            "last_seen": time.time(),
        }
        self.cache.put("registry", series_url, entry)

    def get_registry_entries(self) -> List[Dict[str, Any]]:
        """Return all registry entries sorted by last_seen descending."""
        entries = self.cache.scan("registry")
        entries.sort(key=lambda e: e.get("last_seen", 0), reverse=True)
        return entries


# ============================================================================
# PLAYER
# ============================================================================
class Player:
    """MPV playback controller"""

    def __init__(self, quality: str = Config.DEFAULT_QUALITY):
        self.quality = quality
        self._process: Optional[subprocess.Popen] = None
        self._preloader = Preloader()

    def play(self, url: str, episodes: List[Tuple[str, str]] = None,
             current_idx: int = 0) -> bool:
        """Launch MPV with the given stream URL"""
        stream_url = StreamExtractor.extract(url)

        if episodes and current_idx < len(episodes) - 1:
            self._preloader.preload(episodes, current_idx)

        cmd = [
            "mpv", stream_url,
            f"--ytdl-format=bestvideo[height<={self.quality}]+bestaudio/best[height<={self.quality}]/best",
            "--cache=yes",
            "--cache-secs=60",
            "--no-terminal",
        ]

        try:
            self._process = subprocess.Popen(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            print(Theme.status("success", "Player launched!"))
            return True
        except FileNotFoundError:
            print(Theme.status("error", "MPV not found. Install it: https://mpv.io"))
            return False

    def stop(self):
        self._preloader.stop()
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._process.kill()

    def is_playing(self) -> bool:
        return self._process is not None and self._process.poll() is None


# ============================================================================
# DOWNLOADER
# ============================================================================
class Downloader:
    """Download episodes via yt-dlp"""

    @staticmethod
    def download(url: str, series_title: str, ep_title: str, quality: str) -> bool:
        stream_url = StreamExtractor.extract(url)

        series_dir = os.path.join(Config.DOWNLOAD_DIR, Utils.sanitize_filename(series_title))
        os.makedirs(series_dir, exist_ok=True)

        output_path = os.path.join(series_dir, f"{Utils.sanitize_filename(ep_title)}.%(ext)s")

        cmd = [
            "yt-dlp",
            "-f", f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]/best",
            "-o", output_path,
            "--no-check-certificates",
            "--no-part",
            "--concurrent-fragments", "4",
            stream_url,
        ]

        try:
            with Spinner("Downloading...", "Download complete!"):
                subprocess.run(cmd, check=True, capture_output=True, text=True)
            return True
        except subprocess.CalledProcessError:
            print(Theme.status("error", "Download failed"))
            return False
        except FileNotFoundError:
            print(Theme.status("error", "yt-dlp not found. Install it: pip install yt-dlp"))
            return False


# ============================================================================
# USER INTERFACE
# ============================================================================
class UI:
    """All user-facing display and input logic"""

    @staticmethod
    def show_banner():
        Utils.clear_screen()
        print(Theme.banner())
        print()

    @staticmethod
    def select_from_list(items: List[Tuple[str, str]], title: str) -> int:
        """Display numbered list, return selected index"""
        pad = Theme._content_pad()
        max_name = min(Theme.get_width() - len(pad) - 8, 80)

        print(Theme.header(title))
        for i, (name, _) in enumerate(items, 1):
            display = name[:max_name] + "..." if len(name) > max_name else name
            print(f"{pad}{Theme.ACCENT}{i:3d}.{Theme.RESET} {Theme.WHITE}{display}{Theme.RESET}")

        while True:
            try:
                choice = safe_input(Theme.prompt(f"Select [1-{len(items)}]")).strip()
                idx = int(choice) - 1
                if 0 <= idx < len(items):
                    return idx
                print(Theme.status("error", f"Pick between 1 and {len(items)}"))
            except ValueError:
                print(Theme.status("error", "Enter a valid number"))
            except KeyboardInterrupt:
                raise

    @staticmethod
    def display_episodes(episodes: List[Tuple[str, str]], page: int = 1,
                         per_page: int = 20) -> int:
        """Display paginated episode list, return total pages"""
        pad = Theme._content_pad()
        max_name = min(Theme.get_width() - len(pad) - 8, 80)
        start = (page - 1) * per_page
        end = min(start + per_page, len(episodes))
        total_pages = (len(episodes) + per_page - 1) // per_page

        print(Theme.header(f"Episodes  ({start + 1}-{end} of {len(episodes)})"))

        for i in range(start, end):
            title = episodes[i][0]
            display = title[:max_name] + "..." if len(title) > max_name else title
            print(f"{pad}{Theme.SILVER}{i + 1:3d}.{Theme.RESET} {Theme.WHITE}{display}{Theme.RESET}")

        if total_pages > 1:
            print(f"\n{pad}{Theme.GRAY}Page {page}/{total_pages}  "
                  f"{Theme.SECONDARY}[N]ext  [P]rev{Theme.RESET}")

        return total_pages

    @staticmethod
    def display_series_info(info: Dict[str, Any]):
        """Display series metadata in a centered card"""
        pad = Theme._content_pad()
        desc_w = min(Theme.get_width() - len(pad) * 2 - 2, 84)

        if info.get("title"):
            print(f"\n{pad}{Theme.ACCENT}{info['title']}{Theme.RESET}")
            title_len = min(len(info['title']), desc_w)
            print(f"{pad}{Theme.DIM_ROSE}{Theme.H * title_len}{Theme.RESET}")
        if info.get("studio"):
            print(f"{pad}{Theme.GRAY}Studio: {Theme.WHITE}{info['studio']}{Theme.RESET}")
        if info.get("status"):
            print(f"{pad}{Theme.GRAY}Status: {Theme.WHITE}{info['status']}{Theme.RESET}")
        if info.get("date"):
            print(f"{pad}{Theme.GRAY}Aired:  {Theme.WHITE}{info['date']}{Theme.RESET}")
        if info.get("genres"):
            print(f"{pad}{Theme.GRAY}Genres: {Theme.SECONDARY}{', '.join(info['genres'])}{Theme.RESET}")
        if info.get("description"):
            print()
            for paragraph in info['description'].split("\n"):
                paragraph = paragraph.strip()
                if paragraph:
                    wrapped = textwrap.fill(paragraph, width=desc_w)
                    for line in wrapped.split("\n"):
                        print(f"{pad}{Theme.BLUSH}{line}{Theme.RESET}")

    @staticmethod
    def select_episodes(episodes: List[Tuple[str, str]],
                        series_info: Optional[Dict[str, Any]] = None) -> List[Tuple[str, str]]:
        """Interactive episode selection with pagination"""
        page = 1
        per_page = 20

        while True:
            Utils.clear_screen()
            UI.show_banner()
            if series_info:
                UI.display_series_info(series_info)
            total_pages = UI.display_episodes(episodes, page, per_page)

            pad = Theme._content_pad()
            print(f"\n{pad}{Theme.GRAY}Enter episode numbers (e.g. {Theme.SECONDARY}1-5,8,10-12{Theme.GRAY}), "
                  f"{Theme.SECONDARY}all{Theme.GRAY}, or {Theme.SECONDARY}n/p{Theme.GRAY} to navigate{Theme.RESET}")

            try:
                choice = safe_input(Theme.prompt("Select episodes")).strip().lower()

                if choice == "n" and page < total_pages:
                    page += 1
                    continue
                elif choice == "p" and page > 1:
                    page -= 1
                    continue
                elif choice in ("", "all", "a"):
                    return episodes

                # Parse ranges like 1-5,8,10-12
                selected = []
                for part in choice.split(","):
                    part = part.strip()
                    if "-" in part:
                        s, e = map(int, part.split("-"))
                        if s < 1 or e > len(episodes) or s > e:
                            raise IndexError
                        selected.extend(episodes[s - 1 : e])
                    else:
                        n = int(part)
                        if n < 1 or n > len(episodes):
                            raise IndexError
                        selected.append(episodes[n - 1])

                if selected:
                    print(Theme.status("success", f"Selected {len(selected)} episode(s)"))
                    return selected
            except (ValueError, IndexError):
                print(Theme.status("error", f"Invalid input. Use 1-{len(episodes)}"))
                time.sleep(1)
            except KeyboardInterrupt:
                raise

    @staticmethod
    def show_playback_controls(title: str, current: int, total: int):
        """Display playback controls"""
        pad = Theme._content_pad()
        max_title = min(Theme.get_width() - len(pad) - 4, 80)
        display = title[:max_title] + "..." if len(title) > max_title else title

        print(Theme.header(f"Now Playing  ({current}/{total})"))
        print(f"{pad}{Theme.SECONDARY}{display}{Theme.RESET}")
        print()
        print(f"{pad}{Theme.SECONDARY}[N]{Theme.RESET} Next    "
              f"{Theme.SECONDARY}[P]{Theme.RESET} Previous    "
              f"{Theme.SECONDARY}[S]{Theme.RESET} Skip to    "
              f"{Theme.SECONDARY}[R]{Theme.RESET} Replay")
        print(f"{pad}{Theme.SECONDARY}[D]{Theme.RESET} Download "
              f"{Theme.SECONDARY}[Q]{Theme.RESET} Quit")
        print(f"\n{pad}{Theme.GRAY}Close MPV or enter a command to continue...{Theme.RESET}")


# ============================================================================
# MAIN APPLICATION
# ============================================================================
class HentaiCLI:
    """Main application controller"""

    def __init__(self):
        self.player: Optional[Player] = None
        self._prefetcher = BackgroundPrefetcher(max_workers=3)
        os.makedirs(Config.CACHE_DIR, exist_ok=True)
        os.makedirs(Config.DOWNLOAD_DIR, exist_ok=True)

    def run(self):
        """Entry point - parse args and dispatch"""
        parser = argparse.ArgumentParser(
            prog="hcli",
            description="H-CLI - Terminal streaming client",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  hcli "search term"              Search and stream
  hcli "search term" -q 1080      Stream at 1080p
  hcli "search term" -d           Download mode
            """,
        )
        parser.add_argument("query", nargs="?", help="Search query")
        parser.add_argument("-s", "--source", choices=["hm"], default="hm",
                            help="Source to search (default: hm)")
        parser.add_argument("-q", "--quality", default=Config.DEFAULT_QUALITY,
                            help=f"Video quality (default: {Config.DEFAULT_QUALITY})")
        parser.add_argument("-d", "--download", action="store_true",
                            help="Download instead of stream")
        parser.add_argument("--clear-cache", action="store_true",
                            help="Clear stream cache")

        args = parser.parse_args()

        if args.clear_cache:
            self._clear_cache()
            if not args.query:
                return

        try:
            if args.query:
                self._direct_mode(args)
            else:
                self._interactive_mode()
        except KeyboardInterrupt:
            self._cleanup()
            print(f"\n{Theme.divider()}")
            print(Theme.status("info", "Session ended. Goodbye!"))

    # -- modes ---------------------------------------------------------------

    def _direct_mode(self, args):
        """Run with CLI arguments"""
        UI.show_banner()

        scraper = Scraper(args.source or "hm")
        results = self._search(args.query, args.source)
        if not results:
            print(Theme.status("error", "No results found"))
            return

        # Layer 2: prefetch top series pages while user reads results
        self._prefetcher.prefetch_series_pages(results, scraper)

        idx = UI.select_from_list(results, "Search Results")
        _, series_url = results[idx]

        series_info = self._show_series_info(series_url)

        episodes = self._get_episodes(series_url, args.source)
        if not episodes:
            print(Theme.status("error", "No episodes found"))
            return

        # Layer 3: prefetch first 3 streams while user reads episode list
        self._prefetcher.prefetch_streams(episodes)

        series_title = results[idx][0].split(" (")[0]  # strip year/rating suffix
        selected = UI.select_episodes(episodes, series_info)

        if args.download:
            self._download_episodes(selected, series_title, args.quality)
        else:
            self._play_episodes(selected, series_title, args.quality)

    def _interactive_mode(self):
        """Fully interactive loop"""
        while True:
            UI.show_banner()

            query = safe_input(Theme.prompt("Search")).strip()
            if not query:
                print(Theme.status("warning", "Enter a search term"))
                time.sleep(1)
                continue

            scraper = Scraper("hm")
            results = self._search(query, source=None)
            if not results:
                print(Theme.status("error", "No results found"))
                time.sleep(2)
                continue

            # Layer 2: prefetch top series pages while user reads results
            self._prefetcher.prefetch_series_pages(results, scraper)

            idx = UI.select_from_list(results, "Search Results")
            _, series_url = results[idx]

            series_info = self._show_series_info(series_url)

            series_title = results[idx][0].split(" (")[0]
            episodes = self._get_episodes(series_url)
            if not episodes:
                print(Theme.status("error", "No episodes found"))
                time.sleep(2)
                continue

            # Layer 3: prefetch first 3 streams while user reads episode list
            self._prefetcher.prefetch_streams(episodes)

            selected = UI.select_episodes(episodes, series_info)

            pad = Theme._content_pad()
            print(f"\n{pad}{Theme.SECONDARY}[P]{Theme.RESET} Play    "
                  f"{Theme.SECONDARY}[D]{Theme.RESET} Download")
            choice = safe_input(Theme.prompt("Choose [P]")).strip().lower()

            if choice == "d":
                self._download_episodes(selected, series_title, Config.DEFAULT_QUALITY)
            else:
                self._play_episodes(selected, series_title, Config.DEFAULT_QUALITY)

            again = safe_input(Theme.prompt("Search again? [Y/n]")).strip().lower()
            if again in ("n", "no"):
                print(Theme.status("info", "Goodbye!"))
                break

    # -- core actions --------------------------------------------------------

    def _search(self, query: str, source: Optional[str] = None) -> List[Tuple[str, str]]:
        """Search for series"""
        scraper = Scraper(source or "hm")
        cache_key = f"{scraper.base_url}:{query}"

        if Scraper.cache.has("search", cache_key):
            results = scraper.search(query)
            if results:
                print(Theme.status("success", f"Found {len(results)} result(s) (cached)"))
        else:
            with Spinner(f"Searching '{query}'..."):
                results = scraper.search(query)
            if results:
                print(Theme.status("success", f"Found {len(results)} result(s)"))

        # Fuzzy correction: try harder if results are empty or irrelevant
        best_score = max(
            (Scraper._relevance_score(query, r[0]) for r in results), default=0.0
        )
        if best_score < 0.4:
            word_bank = scraper._build_word_bank(results)
            corrected = Scraper._fuzzy_correct(query, word_bank)
            if corrected and corrected != query.lower():
                with Spinner(f"Searching '{corrected}'..."):
                    corrected_results = scraper.search(corrected)
                if corrected_results:
                    print(Theme.status(
                        "info",
                        f"Showing results for '{corrected}' (searched for '{query}')",
                    ))
                    results = corrected_results

        # Last resort: if still empty, search local cache for anything close
        if not results:
            local = scraper._local_fuzzy_search(query)
            if local:
                print(Theme.status("info", f"Showing closest matches from history"))
                results = local

        return results

    def _show_series_info(self, series_url: str) -> Dict[str, Any]:
        """Fetch and display series description and metadata"""
        scraper = Scraper("hm")

        if Scraper.cache.has("series_info", series_url):
            info = scraper.get_series_info(series_url)
        else:
            with Spinner("Fetching series info..."):
                info = scraper.get_series_info(series_url)
        UI.display_series_info(info)
        print()
        return info

    def _get_episodes(self, url: str, source: Optional[str] = None) -> List[Tuple[str, str]]:
        """Fetch episodes for a series"""
        scraper = Scraper(source or "hm")

        if Scraper.cache.has("episodes", url):
            episodes = scraper.get_episodes(url)
            if episodes:
                print(Theme.status("success", f"Found {len(episodes)} episode(s) (cached)"))
        else:
            with Spinner("Fetching episodes..."):
                episodes = scraper.get_episodes(url)
            if episodes:
                print(Theme.status("success", f"Found {len(episodes)} episode(s)"))
        return episodes

    def _play_episodes(self, episodes: List[Tuple[str, str]], series_title: str,
                       quality: str):
        """Play episodes sequentially with controls"""
        self.player = Player(quality)
        current_idx = 0

        while current_idx < len(episodes):
            title, url = episodes[current_idx]

            Utils.clear_screen()
            UI.show_banner()
            UI.show_playback_controls(title, current_idx + 1, len(episodes))

            if not self.player.play(url, episodes, current_idx):
                return

            # Monitor player
            finished = threading.Event()

            def monitor():
                while self.player.is_playing():
                    time.sleep(0.5)
                finished.set()

            threading.Thread(target=monitor, daemon=True).start()

            action = None
            while action is None:
                try:
                    cmd = safe_input(Theme.prompt("Command [N/P/S/R/D/Q]")).strip().lower()
                except KeyboardInterrupt:
                    self.player.stop()
                    return

                if cmd in ("n", ""):
                    if current_idx < len(episodes) - 1:
                        action = "next"
                    elif finished.is_set():
                        action = "done"
                    else:
                        print(Theme.status("warning", "Already at last episode"))
                elif cmd == "p":
                    action = "prev" if current_idx > 0 else None
                    if action is None:
                        print(Theme.status("warning", "Already at first episode"))
                elif cmd == "r":
                    action = "replay"
                elif cmd == "s":
                    try:
                        n = int(safe_input(Theme.prompt(f"Skip to [1-{len(episodes)}]")).strip())
                        if 1 <= n <= len(episodes):
                            action = ("skip", n - 1)
                    except (ValueError, KeyboardInterrupt):
                        pass
                elif cmd == "d":
                    Downloader.download(url, series_title, title, quality)
                elif cmd == "q":
                    action = "quit"

            self.player.stop()

            if action == "next":
                current_idx += 1
            elif action == "prev":
                current_idx -= 1
            elif action == "replay":
                pass
            elif action == "quit":
                break
            elif action == "done":
                current_idx += 1
            elif isinstance(action, tuple) and action[0] == "skip":
                current_idx = action[1]

        print(Theme.status("success", "Playback session complete"))

    def _download_episodes(self, episodes: List[Tuple[str, str]], series_title: str,
                           quality: str):
        """Download selected episodes"""
        print(Theme.divider())
        print(Theme.status("info", f"Downloading {len(episodes)} episode(s)..."))

        ok, fail = 0, 0
        for i, (title, url) in enumerate(episodes, 1):
            pad = Theme._content_pad()
            max_t = min(Theme.get_width() - len(pad) - 10, 80)
            display = title[:max_t] + "..." if len(title) > max_t else title
            print(f"\n{pad}{Theme.ACCENT}[{i}/{len(episodes)}]{Theme.RESET} {Theme.WHITE}{display}{Theme.RESET}")
            if Downloader.download(url, series_title, title, quality):
                ok += 1
            else:
                fail += 1

        print(Theme.divider())
        print(Theme.status("success", f"{ok}/{len(episodes)} downloaded"))
        if fail:
            print(Theme.status("error", f"{fail} failed"))
        print(Theme.status("info", f"Saved to: {Config.DOWNLOAD_DIR}"))

    # -- helpers -------------------------------------------------------------

    def _clear_cache(self):
        self._prefetcher.shutdown()
        with Spinner("Clearing cache..."):
            cleared = False
            for path in (Config.STREAM_CACHE_FILE, Config.DATA_CACHE_FILE):
                try:
                    if os.path.exists(path):
                        os.remove(path)
                        cleared = True
                except OSError:
                    pass
            StreamExtractor.cache = StreamCache()
            Scraper.cache = DataCache()
        self._prefetcher = BackgroundPrefetcher(max_workers=3)
        if cleared:
            print(Theme.status("success", "All caches cleared"))
        else:
            print(Theme.status("info", "No cache to clear"))

    def _cleanup(self):
        self._prefetcher.shutdown()
        if self.player:
            self.player.stop()
