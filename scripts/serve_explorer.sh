#!/usr/bin/env bash
# Serve the Torah Map concept explorer locally (works fully offline — no CDNs).
#   ./scripts/serve_explorer.sh   then open  http://127.0.0.1:8890/explorer.html
# Rebuild the data bundle first if the graph changed:  python3 scripts/build_explorer_data.py
set -e
cd "$(dirname "$0")/../ontology/graph"
[ -f explorer_data.json ] || { echo "run: python3 scripts/build_explorer_data.py first"; exit 1; }
PORT="${1:-8890}"
echo "Torah Map explorer: http://127.0.0.1:${PORT}/explorer.html  (Ctrl-C to stop)"
exec python3 -m http.server "$PORT" --bind 127.0.0.1
