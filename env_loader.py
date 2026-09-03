"""Carga de variables desde .env sin depender de paquetes externos.

Vive en su propio módulo para que cualquiera de los otros (que son
ejecutables sueltos para pruebas) pueda cargar la configuración por su
cuenta, no solo main.py.
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

_loaded = set()


def load_dotenv(path=None):
    """Define en os.environ las variables del archivo .env.

    No sobreescribe lo que ya venga del entorno (así un `VAR=x ./bin/run`
    o lo que exporte run_task.sh siempre gana). Es idempotente: llamarla
    dos veces sobre el mismo archivo no hace trabajo de más.
    """
    path = path or os.path.join(BASE_DIR, ".env")
    if path in _loaded or not os.path.exists(path):
        return
    _loaded.add(path)

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            key, value = _parse_line(line)
            if key and key not in os.environ:
                os.environ[key] = value


def _parse_line(line):
    """Devuelve (clave, valor) de una línea del .env, o (None, None)."""
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        return None, None

    key, _, value = line.partition("=")
    # `export VAR=...` es válido en un .env que también se hace source
    # desde bash (run_task.sh lo hace), así que hay que tolerarlo.
    key = key.strip().removeprefix("export ").strip()
    value = value.strip()

    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        # Entre comillas el contenido va literal, incluidos los '#'
        value = value[1:-1]
    else:
        # Sin comillas, un '#' inicia un comentario al final de la línea
        value = value.split(" #", 1)[0].split("\t#", 1)[0].strip()

    return (key, value) if key else (None, None)
