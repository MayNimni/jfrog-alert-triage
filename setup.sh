#!/usr/bin/env bash
# Sets everything up and runs the triage, in one command:
#   bash setup.sh YOUR_GEMINI_KEY
# Safe to run again; later runs can skip the key (it's saved in .env).
set -e
cd "$(dirname "$0")"

if ! python3 -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null; then
  echo "Python 3.11+ is required. Install it from https://www.python.org/downloads/ and run this again."
  exit 1
fi

if [ -n "$1" ]; then
  echo "GOOGLE_API_KEY=$1" > .env
fi
if ! grep -q '^GOOGLE_API_KEY=.\+' .env 2>/dev/null; then
  echo "Missing Gemini API key. Get a free one at https://aistudio.google.com/apikey and run:"
  echo "  bash setup.sh YOUR_GEMINI_KEY"
  exit 1
fi

if [ ! -d .venv ]; then
  echo "Creating .venv..."
  python3 -m venv .venv
fi
echo "Installing dependencies..."
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt

echo "Running tests..."
.venv/bin/pytest -q

echo "Running the triage on all alerts (one Gemini call per alert, takes a minute or two)..."
.venv/bin/python main.py

echo
echo "Done. Results: output/results.json  Report: output/report.html"
if command -v open >/dev/null; then
  open output/report.html
fi
