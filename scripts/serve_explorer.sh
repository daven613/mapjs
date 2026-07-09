#!/usr/bin/env bash
# Serve the Torah Map concept explorer locally (works fully offline — no CDNs).
#   ./scripts/serve_explorer.sh   then open  http://127.0.0.1:8890/explorer.html
# Rebuild the data bundle first if the graph changed:  python3 scripts/build_explorer_data.py
# Sends no-cache headers so edits always show up on a plain reload (no stale-cache confusion).
set -e
cd "$(dirname "$0")/../ontology/graph"
[ -f explorer_data.json ] || { echo "run: python3 scripts/build_explorer_data.py first"; exit 1; }
PORT="${1:-8890}"
echo "Torah Map explorer: http://127.0.0.1:${PORT}/explorer.html  (Ctrl-C to stop)"
exec python3 -c '
import sys, http.server, socketserver
class H(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()
port = int(sys.argv[1])
socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("127.0.0.1", port), H) as s:
    s.serve_forever()
' "$PORT"
