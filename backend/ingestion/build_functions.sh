#!/usr/bin/env bash
# Package chaque fonction d'ingestion avec ses dépendances Python.
# Produit : infra/functions/scrutins.zip et infra/functions/deputes.zip
#
# Usage :
#   cd backend
#   bash ingestion/build_functions.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
INGESTION_DIR="$REPO_ROOT/backend/ingestion/assemblee"
OUT_DIR="$REPO_ROOT/infra/functions"
TMP_DIR="$(mktemp -d)"

DEPS="psycopg httpx tenacity"

mkdir -p "$OUT_DIR"

build_zip() {
  local name="$1"          # scrutins | deputes
  local workdir="$TMP_DIR/$name"

  echo "==> Building $name.zip"
  rm -f "$OUT_DIR/$name.zip"
  mkdir -p "$workdir"

  # Code source de la fonction
  cp "$INGESTION_DIR/$name.py" "$workdir/$name.py"
  cp -r "$INGESTION_DIR/../" "$workdir/ingestion"
  find "$workdir/ingestion" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

  # Dépendances pip installées à plat dans le ZIP
  pip3 install $DEPS --target "$workdir" --quiet --disable-pip-version-check

  # Suppression des fichiers inutiles pour alléger le ZIP
  find "$workdir" -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
  find "$workdir" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

  (cd "$workdir" && zip -r "$OUT_DIR/$name.zip" . -x "*.pyc" -x "*.pyo") > /dev/null

  echo "    -> $OUT_DIR/$name.zip ($(du -sh "$OUT_DIR/$name.zip" | cut -f1))"
}

build_zip "scrutins"
build_zip "deputes"
build_zip "agenda"
build_zip "amendements"

rm -rf "$TMP_DIR"
echo "Done."
