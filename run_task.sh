#!/bin/bash
# Punto de entrada único: prepara el entorno y ejecuta main.py.
# Se puede llamar directo, vía `bin/run`, o desde cron.
set -uo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="$PROJECT_DIR/automation.log"
# El venv vive fuera de iCloud (~/Documents está sincronizado y corrompe el venv)
VENV_DIR="${Y2O_VENV_DIR:-$HOME/.venvs/Y2Obsidian}"
PY="$VENV_DIR/bin/python"
STAMP="$VENV_DIR/.requirements.sha"

cd "$PROJECT_DIR" || exit 1

# --- Log rotation: evita que automation.log crezca sin límite ---
if [ -f "$LOG_FILE" ] && [ "$(wc -c < "$LOG_FILE")" -gt 1048576 ]; then
    mv "$LOG_FILE" "$LOG_FILE.1"
fi

log() { echo "$@" | tee -a "$LOG_FILE"; }

# --- Cargar variables de entorno desde .env si existe ---
if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "$PROJECT_DIR/.env"
    set +a
fi

# --- Bootstrap del venv: se crea solo si no existe o quedó corrupto ---
if [ ! -x "$PY" ]; then
    log "--- venv no encontrado en $VENV_DIR, creando... ---"
    BASE_PY="$(command -v python3.13 || command -v python3.12 || command -v python3)"
    if [ -z "$BASE_PY" ]; then
        log "ERROR: no se encontró python3 en el sistema."
        exit 1
    fi
    rm -rf "$VENV_DIR"
    "$BASE_PY" -m venv "$VENV_DIR" >>"$LOG_FILE" 2>&1 || { log "ERROR: falló la creación del venv."; exit 1; }
    rm -f "$STAMP"
    log "--- venv creado con $BASE_PY ($("$PY" -V 2>&1)) ---"
fi

# --- Instalar/actualizar dependencias solo si requirements.txt cambió ---
REQ_SHA="$(shasum -a 256 "$PROJECT_DIR/requirements.txt" | cut -d' ' -f1)"
if [ ! -f "$STAMP" ] || [ "$(cat "$STAMP")" != "$REQ_SHA" ]; then
    log "--- Instalando dependencias... ---"
    "$PY" -m pip install --quiet --upgrade pip >>"$LOG_FILE" 2>&1
    if "$PY" -m pip install --quiet -r "$PROJECT_DIR/requirements.txt" >>"$LOG_FILE" 2>&1; then
        echo "$REQ_SHA" > "$STAMP"
        log "--- Dependencias instaladas. ---"
    else
        log "ERROR: falló la instalación de dependencias (ver $LOG_FILE)."
        exit 1
    fi
fi

# --- Ejecutar ---
echo "--- Starting run at $(date) ---" >> "$LOG_FILE"

# La salida va a pantalla y al log a la vez. En cron, añade
# ">/dev/null 2>&1" a la línea del crontab para silenciar el correo.
"$PY" main.py "$@" 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE=${PIPESTATUS[0]}

echo "--- Finished run at $(date) (exit $EXIT_CODE) ---" >> "$LOG_FILE"

# --- Notificar por WhatsApp si algo falló ---
if [ $EXIT_CODE -ne 0 ] && [ -n "${WHAPI_TOKEN:-}" ] && [ -n "${WHATSAPP_TO:-}" ]; then
    LOG_TAIL=$(awk '/^--- Starting run at/{buf=""} {buf=buf $0 "\n"} END{print buf}' "$LOG_FILE")
    BODY=$("$PY" -c '
import json, sys
exit_code, log_tail = sys.argv[1], sys.argv[2]
# El último traceback gana; si no hay, se manda la cola del log
idx = log_tail.rfind("Traceback")
snippet = log_tail[idx:] if idx != -1 else log_tail
# WhatsApp corta los mensajes ~4096 chars — dejar espacio para el encabezado
snippet = snippet[-2500:]
msg = f"*Error en flujo Y2Obsidian* (exit {exit_code})\n```\n{snippet}\n```"
print(json.dumps({"to": sys.argv[3], "body": msg}))
' "$EXIT_CODE" "$LOG_TAIL" "$WHATSAPP_TO")
    curl -s -X POST "https://gate.whapi.cloud/messages/text" \
      -H "Authorization: Bearer $WHAPI_TOKEN" \
      -H "Content-Type: application/json" \
      -d "$BODY" > /dev/null
fi

exit $EXIT_CODE
