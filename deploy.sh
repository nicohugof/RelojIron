#!/usr/bin/env bash
# Deploy de RelojIron en el Oracle. Correr DESDE el checkout git en el
# servidor (/home/ubuntu/RelojIron):
#
#   ./deploy.sh          # solo despliega si origin/main tiene commits nuevos
#   ./deploy.sh --force  # reinicia el proceso con el commit actual igual
#
# Qué hace: git fetch + fast-forward a origin/main, valida que el .py
# compile, reinicia rutina_server.py y verifica que responda antes de dar
# por buena la actualización. Si algo falla, vuelve al commit anterior y
# reinicia con ese. Nunca pisa cambios locales: si el checkout no está
# limpio, aborta sin tocar nada.
#
# Secretos: PANEL_API_URL e IPAD_API_TOKEN viven en
# /home/ubuntu/RelojIron.env en el servidor (fuera de este repo, nunca en
# git). Ver docs de acceso en nicohugof/ironcross para cómo rotarlos.
set -euo pipefail

ENV_FILE="/home/ubuntu/RelojIron.env"
LOG_FILE="/home/ubuntu/logs/rutina_server.log"
PORT=8090
FORCE=false
[ "${1:-}" = "--force" ] && FORCE=true

cd "$(dirname "$0")"
REPO_DIR="$(pwd)"

log() { echo "[deploy $(date '+%H:%M:%S')] $*"; }

if [ -n "$(git status --porcelain)" ]; then
  echo "ABORTO: el checkout tiene cambios sin commitear. No piso nada — revisalo a mano:"
  git status --short
  exit 1
fi

git fetch origin main --quiet
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" = "$REMOTE" ] && [ "$FORCE" = false ]; then
  log "ya está al día en $LOCAL, nada que hacer (usá --force para reiniciar igual)"
  exit 0
fi

ROLLBACK_COMMIT="$LOCAL"
log "actualizando $ROLLBACK_COMMIT -> $REMOTE"
git merge --ff-only origin/main

if ! python3 -m py_compile rutina_server.py; then
  log "rutina_server.py no compila, no se tocó el proceso corriendo"
  git reset --hard "$ROLLBACK_COMMIT"
  exit 1
fi

mkdir -p "$(dirname "$LOG_FILE")"
[ -f "$ENV_FILE" ] || { echo "ABORTO: falta $ENV_FILE (PANEL_API_URL / IPAD_API_TOKEN)"; exit 1; }

restart_server() {
  # Mismo path absoluto para arrancar y para matar: si difieren, pkill no
  # encuentra nada, el puerto sigue ocupado y el proceso nuevo no arranca
  # (pasó una vez al migrar a este esquema).
  pkill -f "python3 $REPO_DIR/rutina_server.py" 2>/dev/null || true
  for _ in 1 2 3 4 5; do
    ss -tln 2>/dev/null | grep -q ":$PORT " || break
    sleep 1
  done
  (
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
    nohup python3 "$REPO_DIR/rutina_server.py" >> "$LOG_FILE" 2>&1 &
    disown
  )
  sleep 2
}

log "reiniciando rutina_server.py"
restart_server

CODE=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/api/oficina" || echo "000")
if [ "$CODE" != "200" ]; then
  log "HEALTH CHECK FALLÓ (api/oficina=$CODE) — ROLLBACK a $ROLLBACK_COMMIT"
  git reset --hard "$ROLLBACK_COMMIT"
  restart_server
  CODE2=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/api/oficina" || echo "000")
  log "vuelto a $ROLLBACK_COMMIT, api/oficina ahora responde $CODE2"
  exit 1
fi

log "OK — corriendo $(git log -1 --format='%h %s')"
