#!/usr/bin/env python3
"""
H-CLI (Hentai-CLI) - Terminal-based streaming client
Themed terminal UI, multi-source support, MPV playback
"""

import argparse
import atexit
import os
import re
import signal
import sys
import time
import subprocess
import threading
import json
from collections import OrderedDict
from typing import List, Tuple, Optional, Dict, Any

import requests
from bs4 import BeautifulSoup

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
    SYM_ARROW = "»"

    @classmethod
    def banner(cls) -> str:
        """Generate the main banner"""
        w = 58
        lines = [
            f"{cls.PRIMARY}{cls.TL}{cls.H * w}{cls.TR}{cls.RESET}",
            f"{cls.PRIMARY}{cls.V}{cls.RESET}  {cls.ACCENT}H-CLI{cls.RESET}  {cls.GRAY}Terminal Streaming Client{cls.RESET}{' ' * 23}{cls.PRIMARY}{cls.V}{cls.RESET}",
            f"{cls.PRIMARY}{cls.V}{cls.RESET}{' ' * w}{cls.PRIMARY}{cls.V}{cls.RESET}",
            f"{cls.PRIMARY}{cls.BL}{cls.H * w}{cls.BR}{cls.RESET}",
        ]
        return "\n".join(lines)

    @classmethod
    def header(cls, text: str) -> str:
        """Create a section header"""
        return f"\n  {cls.GRAY}{cls.TL}{cls.H} {text.upper()} {cls.H}{cls.TR}{cls.RESET}\n"

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
        return f"  {color}{sym}{cls.RESET} {cls.WHITE}{msg}{cls.RESET}"

    @classmethod
    def prompt(cls, text: str = "Enter command") -> str:
        """Styled input prompt"""
        return f"\n{cls.ACCENT}{cls.SYM_ARROW}{cls.RESET} {cls.PRIMARY}{text}{cls.RESET}: "

    @classmethod
    def progress_bar(cls, current: int, total: int, width: int = 30) -> str:
        """Progress bar"""
        filled = int(width * current / total) if total > 0 else 0
        bar = f"{cls.PRIMARY}[{cls.ACCENT}{'■' * filled}{cls.GRAY}{'□' * (width - filled)}{cls.PRIMARY}]{cls.RESET}"
        return f"{bar} {cls.ACCENT}{current}{cls.GRAY}/{cls.ACCENT}{total}{cls.RESET}"

    @classmethod
    def divider(cls) -> str:
        """Section divider"""
        return f"\n  {cls.PRIMARY}{cls.H * 60}{cls.RESET}\n"


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
    """LRU cache for stream URLs"""

    def __init__(self, max_size: int = 100):
        self.cache: OrderedDict = OrderedDict()
        self.max_size = max_size
        self._load()

    def get(self, url: str) -> Optional[str]:
        if url in self.cache:
            self.cache.move_to_end(url)
            return self.cache[url]
        return None

    def put(self, url: str, stream_url: str):
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
            with open(Config.STREAM_CACHE_FILE, "w") as f:
                json.dump(list(self.cache.items()), f)
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

        # Wipe cache
        try:
            if os.path.exists(Config.STREAM_CACHE_FILE):
                os.remove(Config.STREAM_CACHE_FILE)
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
# SCRAPER
# ============================================================================
class Scraper:
    """Search and fetch episode lists from HentaiMama"""

    def __init__(self, source_key: str = "hm"):
        self.source = Config.SOURCES[source_key]
        self.base_url = self.source["base_url"]

    def search(self, query: str) -> List[Tuple[str, str]]:
        """Search for series, returns list of (title, url)"""
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

        return results

    def get_series_info(self, series_url: str) -> Dict[str, Any]:
        """Get series description, genres, metadata"""
        soup = Utils.fetch_soup(series_url, timeout=12)

        info: Dict[str, Any] = {"title": "", "description": "", "genres": [],
                                 "studio": "", "status": "", "date": ""}

        # Description
        paragraphs = soup.select(".wp-content p")
        info["description"] = "\n".join(
            p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)
        )

        # Genres
        info["genres"] = [a.get_text(strip=True) for a in soup.select(".sgeneros a")]

        # Custom fields: title, studio, first air, last air, status
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

    def get_episodes(self, series_url: str) -> List[Tuple[str, str]]:
        """Get all episodes for a series, returns sorted list of (title, url)"""
        soup = Utils.fetch_soup(series_url, timeout=12)
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
            print(Theme.status("loading", "Downloading..."))
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(Theme.status("success", "Download complete!"))
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
        print(Theme.header(title))
        for i, (name, _) in enumerate(items, 1):
            display = name[:55] + "..." if len(name) > 55 else name
            print(f"  {Theme.ACCENT}{i:3d}.{Theme.RESET} {Theme.WHITE}{display}{Theme.RESET}")

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
        start = (page - 1) * per_page
        end = min(start + per_page, len(episodes))
        total_pages = (len(episodes) + per_page - 1) // per_page

        print(Theme.header(f"Episodes  ({start + 1}-{end} of {len(episodes)})"))

        for i in range(start, end):
            title = episodes[i][0]
            display = title[:55] + "..." if len(title) > 55 else title
            print(f"  {Theme.SILVER}{i + 1:3d}.{Theme.RESET} {Theme.WHITE}{display}{Theme.RESET}")

        if total_pages > 1:
            print(f"\n  {Theme.GRAY}Page {page}/{total_pages}  "
                  f"{Theme.SECONDARY}[N]ext  [P]rev{Theme.RESET}")

        return total_pages

    @staticmethod
    def display_series_info(info: Dict[str, Any]):
        """Display series metadata inline"""
        if info.get("title"):
            print(f"\n  {Theme.ACCENT}{info['title']}{Theme.RESET}")
        if info.get("studio"):
            print(f"  {Theme.GRAY}Studio: {Theme.WHITE}{info['studio']}{Theme.RESET}")
        if info.get("status"):
            print(f"  {Theme.GRAY}Status: {Theme.WHITE}{info['status']}{Theme.RESET}")
        if info.get("date"):
            print(f"  {Theme.GRAY}Aired:  {Theme.WHITE}{info['date']}{Theme.RESET}")
        if info.get("genres"):
            print(f"  {Theme.GRAY}Genres: {Theme.SECONDARY}{', '.join(info['genres'])}{Theme.RESET}")
        if info.get("description"):
            print(f"\n  {Theme.WHITE}{info['description'][:300]}{Theme.RESET}")

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

            print(f"\n  {Theme.GRAY}Enter episode numbers (e.g. {Theme.SECONDARY}1-5,8,10-12{Theme.GRAY}), "
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
        print(Theme.header(f"Now Playing  ({current}/{total})"))
        print(f"  {Theme.SECONDARY}{title[:60]}{Theme.RESET}")
        print()
        print(f"  {Theme.SECONDARY}[N]{Theme.RESET} Next    "
              f"{Theme.SECONDARY}[P]{Theme.RESET} Previous    "
              f"{Theme.SECONDARY}[S]{Theme.RESET} Skip to    "
              f"{Theme.SECONDARY}[R]{Theme.RESET} Replay")
        print(f"  {Theme.SECONDARY}[D]{Theme.RESET} Download "
              f"{Theme.SECONDARY}[Q]{Theme.RESET} Quit")
        print(f"\n  {Theme.GRAY}Close MPV or enter a command to continue...{Theme.RESET}")


# ============================================================================
# MAIN APPLICATION
# ============================================================================
class HentaiCLI:
    """Main application controller"""

    def __init__(self):
        self.player: Optional[Player] = None
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

        results = self._search(args.query, args.source)
        if not results:
            print(Theme.status("error", "No results found"))
            return

        idx = UI.select_from_list(results, "Search Results")
        _, series_url = results[idx]

        series_info = self._show_series_info(series_url)

        episodes = self._get_episodes(series_url, args.source)
        if not episodes:
            print(Theme.status("error", "No episodes found"))
            return

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

            results = self._search(query, source=None)
            if not results:
                print(Theme.status("error", "No results found"))
                time.sleep(2)
                continue

            idx = UI.select_from_list(results, "Search Results")
            _, series_url = results[idx]

            series_info = self._show_series_info(series_url)

            series_title = results[idx][0].split(" (")[0]
            episodes = self._get_episodes(series_url)
            if not episodes:
                print(Theme.status("error", "No episodes found"))
                time.sleep(2)
                continue

            selected = UI.select_episodes(episodes, series_info)

            print(f"\n  {Theme.SECONDARY}[P]{Theme.RESET} Play    "
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
        print(Theme.status("loading", f"Searching '{query}'..."))

        scraper = Scraper(source or "hm")
        results = scraper.search(query)

        if results:
            print(Theme.status("success", f"Found {len(results)} result(s)"))
        return results

    def _show_series_info(self, series_url: str) -> Dict[str, Any]:
        """Fetch and display series description and metadata"""
        print(Theme.status("loading", "Fetching series info..."))
        scraper = Scraper("hm")
        info = scraper.get_series_info(series_url)
        UI.display_series_info(info)
        print()
        return info

    def _get_episodes(self, url: str, source: Optional[str] = None) -> List[Tuple[str, str]]:
        """Fetch episodes for a series"""
        print(Theme.status("loading", "Fetching episodes..."))

        scraper = Scraper(source or "hm")
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
        print(Theme.status("loading", f"Downloading {len(episodes)} episode(s)..."))

        ok, fail = 0, 0
        for i, (title, url) in enumerate(episodes, 1):
            print(f"\n  {Theme.ACCENT}[{i}/{len(episodes)}]{Theme.RESET} {Theme.WHITE}{title[:60]}{Theme.RESET}")
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
        print(Theme.status("loading", "Clearing cache..."))
        try:
            if os.path.exists(Config.STREAM_CACHE_FILE):
                os.remove(Config.STREAM_CACHE_FILE)
                print(Theme.status("success", "Cache cleared"))
            else:
                print(Theme.status("info", "No cache to clear"))
        except OSError as e:
            print(Theme.status("error", f"Failed: {e}"))

    def _cleanup(self):
        if self.player:
            self.player.stop()
