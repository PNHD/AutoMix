"""
Minimal local static-file + upload server for the M2 Signalsmith
browser-WASM bridge (Issue #7's documented WASM/WebAudio fallback path --
see docs/research/P0-M3-R3-DSP-CANDIDATE-PROVENANCE.md sec.1.2).

Serves:
  GET  /<anything under web/ or vendor/ or serve_tmp/>  -- static files
  POST /upload?name=<filename>                          -- writes the raw
       request body to serve_tmp/<filename> (name is sanitized to a bare
       filename, no path traversal).

Everything here talks only to localhost; no audio leaves the machine.

Usage:
    python scripts/serve.py [port]
"""
import http.server
import os
import socketserver
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVE_TMP = ROOT / "serve_tmp"
SERVE_TMP.mkdir(exist_ok=True)

ALLOWED_ROOTS = [ROOT / "web", ROOT / "vendor", SERVE_TMP]


class Handler(http.server.SimpleHTTPRequestHandler):
    # Windows' registry-derived mimetypes guess frequently maps .js/.mjs to
    # "text/plain", which browsers reject for `<script type="module">` per
    # the HTML spec's strict MIME check for module scripts -- force the
    # correct type explicitly rather than relying on the OS guess.
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, ".mjs": "text/javascript", ".js": "text/javascript", ".wasm": "application/wasm"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, fmt, *args):
        sys.stderr.write("[serve] " + (fmt % args) + "\n")

    def do_POST(self):
        if not self.path.startswith("/upload"):
            self.send_error(404, "not found")
            return
        from urllib.parse import urlparse, parse_qs
        query = parse_qs(urlparse(self.path).query)
        name = query.get("name", [None])[0]
        if not name or "/" in name or "\\" in name or ".." in name:
            self.send_error(400, "invalid name")
            return
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        out_path = SERVE_TMP / name
        out_path.write_bytes(body)
        sys.stderr.write(f"[serve] wrote {out_path} ({len(body)} bytes)\n")
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(b"OK")

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    with socketserver.TCPServer(("127.0.0.1", port), Handler) as httpd:
        sys.stderr.write(f"[serve] listening on http://127.0.0.1:{port} (root={ROOT})\n")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
