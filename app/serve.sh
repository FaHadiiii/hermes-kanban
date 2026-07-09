#!/usr/bin/env bash
# Serve the generated dashboard locally. Run: bash serve.sh
cd "$(dirname "$0")"
python3 generate.py
echo "Serving on http://127.0.0.1:8000 -- open public/index.html (localhost only)"
exec python3 -m http.server 8000 --bind 127.0.0.1 --directory ../public
