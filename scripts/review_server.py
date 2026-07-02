#!/usr/bin/env python3
"""Tiny local server for the merge-review app.

  python3 scripts/review_server.py [port]      (default 8777)

Serves ontology/registry/review_app.html at /  and persists decisions:
  GET  /decisions -> ontology/registry/decisions.json (or {})
  POST /save      -> writes decisions.json (atomic, with .bak of previous)
"""
import json, sys, shutil
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

MAPJS = Path(__file__).resolve().parent.parent
APP = MAPJS / "ontology/registry/review_app.html"
DEC = MAPJS / "ontology/registry/decisions.json"


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else body.encode()
        self.send_response(code)
        self.send_header("content-type", ctype)
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, APP.read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/decisions":
            self._send(200, DEC.read_text() if DEC.exists() else "{}")
        else:
            self._send(404, "{}")

    def do_POST(self):
        if self.path != "/save":
            return self._send(404, "{}")
        n = int(self.headers.get("content-length", 0))
        body = self.rfile.read(n)
        try:
            obj = json.loads(body)
            assert isinstance(obj, dict)
        except Exception:
            return self._send(400, '{"err":"bad json"}')
        if DEC.exists():
            shutil.copy(DEC, DEC.with_suffix(".json.bak"))
        tmp = DEC.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1))
        tmp.rename(DEC)
        self._send(200, '{"ok":true}')


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8777
    print(f"review app: http://localhost:{port}/")
    HTTPServer(("127.0.0.1", port), H).serve_forever()
