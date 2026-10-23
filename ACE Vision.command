#!/bin/bash
# Lanceur ACE Vision : démarre le serveur local si besoin, puis ouvre Safari.
cd "$(dirname "$0")" || exit 1
export PATH="/opt/homebrew/bin:$PATH"  # Finder n'a pas le PATH de Homebrew
URL="http://127.0.0.1:8765"

if ! curl -fs "$URL/" >/dev/null 2>&1; then
  mkdir -p data
  nohup uv run python -m ace >> data/server.log 2>&1 &
  for _ in $(seq 1 20); do
    curl -fs "$URL/" >/dev/null 2>&1 && break
    sleep 0.5
  done
  if ! curl -fs "$URL/" >/dev/null 2>&1; then
    tail -n 20 data/server.log
    osascript -e 'display alert "ACE Vision n’a pas démarré" message "Voir data/server.log pour le détail. Vérifiez que uv est installé (brew install uv)."' >/dev/null 2>&1
    exit 1
  fi
fi
open -a Safari "$URL"
