"""
Minimal static server for the AutoMix Live Lab prototype (Issue #11).

Serves the app directory (index.html, src/, work_local/queue_audio/) over
plain HTTP on the loopback address. No build step, no npm dependency --
kept intentionally simple so "fastest runnable prototype" holds.

Binds to 127.0.0.1 (not "localhost") because Spotify's current redirect
URI policy requires an explicit loopback IP literal, not the "localhost"
hostname, for PKCE redirect URIs
(https://developer.spotify.com/documentation/web-api/concepts/redirect_uri).
Both http://127.0.0.1 and http://localhost are treated as secure contexts
by Chromium, so the Web Playback SDK (which requires EME/secure context)
still works over plain HTTP here.

Usage:
    python apps/automix-live-lab/server/server.py [port]
"""
from __future__ import annotations

import sys
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent
HOST = "127.0.0.1"
DEFAULT_PORT = 5500


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(APP_ROOT), **kwargs)

    def end_headers(self):
        # Local-only dev server; permissive CORS so the page can be
        # iterated on from the Browser tool without extra ceremony.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), fmt % args))


def main() -> int:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
    httpd = ThreadingHTTPServer((HOST, port), Handler)
    print(f"AutoMix Live Lab serving {APP_ROOT} at http://{HOST}:{port}/")
    print("Press Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
