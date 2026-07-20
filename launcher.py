from __future__ import annotations

import multiprocessing
import sys
import threading
import webbrowser
from pathlib import Path

from cargo_loading.web_server import run_server


HOST = "127.0.0.1"


def resource_path(relative_path: str) -> Path:
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base_path / relative_path


def build_url(host: str, port: int) -> str:
    return f"http://{host}:{port}/"


def open_browser_when_started(host: str, port: int) -> None:
    threading.Timer(1.0, webbrowser.open, args=(build_url(host, port),)).start()


def main() -> None:
    run_server(host=HOST, port=0, static_dir=resource_path("web"), on_started=open_browser_when_started)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
