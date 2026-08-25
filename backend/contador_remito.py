# backend/contador_remito.py
# Contador automatico de numeros de remito.
#
# - Se incrementa en 1 cada vez que se carga un nuevo PDF.
# - Persiste el ultimo numero en data/remito_counter.json.
# - Es seguro ante usos simultaneos (lock por carpeta + lock de hilos),
#   asi dos personas generando remitos a la vez nunca obtienen el mismo
#   numero.
# - El numero inicial se puede configurar con la variable de entorno
#   REMITO_INICIAL (por defecto 0, o sea el primer remito es el 1).

import json
import os
import threading
import time

_LOCK_HILOS = threading.Lock()

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_DIR = os.path.join(_BASE_DIR, "data")
_RUTA_JSON = os.path.join(_DATA_DIR, "remito_counter.json")
_RUTA_LOCK = os.path.join(_DATA_DIR, "remito_counter.lock")

_REMITO_INICIAL = 0
try:
    _REMITO_INICIAL = int(os.environ.get("REMITO_INICIAL", 0))
except (TypeError, ValueError):
    _REMITO_INICIAL = 0


def _leer_contador():
    try:
        with open(_RUTA_JSON, "r", encoding="utf-8") as f:
            datos = json.load(f)
            return int(datos.get("ultimo", _REMITO_INICIAL))
    except (OSError, ValueError, TypeError):
        return _REMITO_INICIAL


def _guardar_contador(valor):
    os.makedirs(_DATA_DIR, exist_ok=True)
    tmp = _RUTA_JSON + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"ultimo": valor}, f)
    os.replace(tmp, _RUTA_JSON)


def _bloquear(timeout=5.0):
    """Lock entre procesos usando creacion atomica de carpeta."""
    inicio = time.time()
    while True:
        try:
            os.makedirs(_RUTA_LOCK)
            return
        except FileExistsError:
            if time.time() - inicio > timeout:
                # Lock trabado (ej. corte de luz): forzar liberacion
                try:
                    os.rmdir(_RUTA_LOCK)
                except OSError:
                    pass
                inicio = time.time()
            time.sleep(0.01)


def _desbloquear():
    try:
        os.rmdir(_RUTA_LOCK)
    except OSError:
        pass


def obtener_remito_actual():
    """Devuelve el ultimo numero de remito entregado (no incrementa)."""
    with _LOCK_HILOS:
        return _leer_contador()


def siguiente_remito():
    """Incrementa el contador en 1 y devuelve el nuevo numero de remito."""
    with _LOCK_HILOS:
        _bloquear()
        try:
            valor = _leer_contador() + 1
            _guardar_contador(valor)
            return valor
        finally:
            _desbloquear()


def fijar_remito(valor):
    """Fija manualmente el contador (para correcciones administrativas)."""
    valor = int(valor)
    with _LOCK_HILOS:
        _bloquear()
        try:
            _guardar_contador(valor)
            return valor
        finally:
            _desbloquear()
