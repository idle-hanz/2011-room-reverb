#!/usr/bin/env bash
# Linux/mac helper (box / WSL). Windows users: double-click "Launch Tweak App.bat"
cd "$(dirname "$0")"
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
  .venv/bin/pip install --upgrade pip
  .venv/bin/pip install -r requirements.txt
fi
exec .venv/bin/python tweak_app.py
