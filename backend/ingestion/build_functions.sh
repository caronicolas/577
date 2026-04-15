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

BASE_DEPS="psycopg httpx tenacity"

mkdir -p "$OUT_DIR"

build_zip() {
  local name="$1"       # nom du fichier handler (sans .py)
  local srcdir="$2"     # répertoire source contenant $name.py
  local extra_deps="${3:-}"  # dépendances supplémentaires optionnelles
  local workdir="$TMP_DIR/$name"

  echo "==> Building $name.zip"
  rm -f "$OUT_DIR/$name.zip"
  mkdir -p "$workdir"

  # Code source de la fonction
  cp "$srcdir/$name.py" "$workdir/$name.py"

  # Dépendances pip installées à plat dans le ZIP
  # shellcheck disable=SC2086
  pip3 install $BASE_DEPS $extra_deps --target "$workdir" --quiet --disable-pip-version-check

  # Suppression des fichiers inutiles pour alléger le ZIP
  find "$workdir" -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
  find "$workdir" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

  (cd "$workdir" && zip -r "$OUT_DIR/$name.zip" . -x "*.pyc" -x "*.pyo") > /dev/null

  echo "    -> $OUT_DIR/$name.zip ($(du -sh "$OUT_DIR/$name.zip" | cut -f1))"
}

BLUESKY_DIR="$REPO_ROOT/backend/ingestion/bluesky"
GOUV_DIR="$REPO_ROOT/backend/ingestion/gouv"

build_zip "scrutins"    "$INGESTION_DIR"
build_zip "organes"     "$INGESTION_DIR"
build_zip "deputes"     "$INGESTION_DIR"
build_zip "agenda"      "$INGESTION_DIR"
build_zip "amendements" "$INGESTION_DIR"
build_zip "post_agenda"       "$BLUESKY_DIR"
build_zip "post_commissions" "$BLUESKY_DIR"
build_zip "datan"       "$GOUV_DIR"

rm -rf "$TMP_DIR"
echo "Done."
