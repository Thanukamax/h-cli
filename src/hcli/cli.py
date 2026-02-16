"""CLI entry point for H-CLI."""
import os
import sys


def main():
    if os.name == "nt":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass

    from hcli._app import Config, _InputReader, HentaiCLI

    os.makedirs(Config.CACHE_DIR, exist_ok=True)
    os.makedirs(Config.DOWNLOAD_DIR, exist_ok=True)

    _InputReader.start()

    app = HentaiCLI()
    app.run()


if __name__ == "__main__":
    main()
