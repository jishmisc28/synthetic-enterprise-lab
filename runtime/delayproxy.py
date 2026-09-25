"""Published Postgres port. Adds latency when chaos lms-slow is on."""

from __future__ import annotations

import select
import socket
import threading
import time

import os

from runtime.chaos import load_chaos

LISTEN = ("0.0.0.0", 5432)
UPSTREAM = (os.environ.get("PG_UPSTREAM_HOST", "postgres-lms"), 5432)
SLOW_MS = 2500


def _pipe(src: socket.socket, dst: socket.socket, delay: bool) -> None:
    try:
        while True:
            data = src.recv(65536)
            if not data:
                break
            if delay:
                time.sleep(SLOW_MS / 1000.0)
                delay = False  # once per request burst is enough to feel slow
            dst.sendall(data)
    except OSError:
        pass
    finally:
        try:
            dst.shutdown(socket.SHUT_WR)
        except OSError:
            pass


def _handle(client: socket.socket) -> None:
    delay = bool(load_chaos().get("lms-slow"))
    upstream = socket.create_connection(UPSTREAM, timeout=10)
    threading.Thread(target=_pipe, args=(client, upstream, delay), daemon=True).start()
    _pipe(upstream, client, False)
    client.close()
    upstream.close()


def main() -> None:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(LISTEN)
    srv.listen(64)
    while True:
        readable, _, _ = select.select([srv], [], [], 1.0)
        if not readable:
            continue
        client, _ = srv.accept()
        threading.Thread(target=_handle, args=(client,), daemon=True).start()


if __name__ == "__main__":
    main()
