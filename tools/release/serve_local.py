#!/usr/bin/env python3
"""One-file, dependency-free museum server: local by default, optional private LAN."""
from __future__ import annotations

import argparse
import functools
import http.server
import socket
import threading
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def lan_addresses() -> list[str]:
    found = set()
    for host in {socket.gethostname(), socket.getfqdn()}:
        try:
            for item in socket.getaddrinfo(host, None, family=socket.AF_INET):
                ip = item[4][0]
                if not ip.startswith(("127.", "169.254.")):
                    found.add(ip)
        except OSError:
            pass
    return sorted(found)


def main() -> None:
    parser = argparse.ArgumentParser(description="City on Paper: open the private museum with Python 3")
    parser.add_argument("--lan", action="store_true", help="Allow devices on your trusted Wi-Fi to view this site")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    if not (1 <= args.port <= 65535):
        parser.error("Port must be from 1 to 65535")

    bind = "0.0.0.0" if args.lan else "127.0.0.1"
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
    try:
        server = http.server.ThreadingHTTPServer((bind, args.port), handler)
    except OSError as exc:
        parser.error(f"Cannot start server: {exc}. Try --port 8766")
    url = f"http://127.0.0.1:{server.server_port}/"
    print("\nГОРОД НА БУМАГЕ · CITY ON PAPER")
    print("Откройте на этом компьютере:", url)
    if args.lan:
        print("Доступ с других устройств включён — используйте только доверенный домашний Wi-Fi!")
        for ip in lan_addresses():
            print("iPad/iPhone в той же сети:", f"http://{ip}:{server.server_port}/")
        print("Этот режим без пароля. Не включайте его в общественной сети.")
    else:
        print("По умолчанию музей доступен только на этом компьютере.")
        print("Для iPad/iPhone в домашнем Wi-Fi запустите: python3 serve_local.py --lan")
    print("Нажмите Ctrl+C в окне терминала, чтобы выключить сайт.\n", flush=True)
    if not args.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever(poll_interval=0.2)
    except KeyboardInterrupt:
        print("\nСервер остановлен.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
