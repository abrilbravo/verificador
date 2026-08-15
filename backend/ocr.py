# backend/ocr.py - Versión con Google Gemini Flash (gratis)

import re
import os
import sys
import base64
import json
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from .parser_repuestos import (
        parsear_repuestos,
        extraer_codigos,
        formatear_codigo,
        PATRON_CODIGO_DIGITO,
    )
except ImportError:
    from parser_repuestos import (
        parsear_repuestos,
        extraer_codigos,
        formatear_codigo,
        PATRON_CODIGO_DIGITO,
    )

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

PROMPT = """Analizá esta imagen de un remito o captura de pantalla del sistema ADTR de Federación Patronal Seguros.
Extraé los siguientes datos y devolvé SOLO un JSON válido, sin explicaciones ni markdown:

{
  "patente": "patente del vehículo (formato ABC123 o AB123CD)",
  "orden": "número de orden",
  "siniestro": "número de siniestro (formato 103-4-46654)",
  "modelo": "modelo del vehículo (solo marca y modelo, ej: VW FOX 1.6 TRENDLINE)",
  "remito": "número de remito si aparece",
  "repuestos": [
    {"codigo": "código del repuesto", "descripcion": "descripción", "precio": "precio numérico"}
  ]
}

Reglas importantes:
- Los códigos de repuestos tienen formato como: 5U0853677, 3C8853856F, 2H6823033D, SU0853653F, etc.
- Si hay sufijo separado por espacio (ej: 5U0853677 1NN), incluilos juntos como: 5U0-853-677- -1NN
- Si no encontrás algún campo, dejalo como string vacío
- Los repuestos son la lista de piezas con sus códigos
- Devolvé SOLO el JSON, sin ```json ni nada extra"""


class LectorOCR:
    def __init__(self):
        self.texto = ""
        self.lineas = []
        self.datos = {
            "cliente": "",
            "patente": "",
            "orden": "",
            "siniestro": "",
            "modelo": "",
            "remito": "",
            "repuestos": []
        }

    def abrir_imagen(self, ruta_imagen):
        try:
            with open(ruta_imagen, "rb") as f:
                imagen_bytes = f.read()

            imagen_b64 = base64.b64encode(imagen_bytes).decode("utf-8")

            ext = ruta_imagen.lower().split(".")[-1]
            mime_types = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
            mime_type = mime_types.get(ext, "image/jpeg")

            payload = {
                "contents": [{
                    "parts": [
                        {"text": PROMPT},
                        {"inline_data": {"mime_type": mime_type, "data": imagen_b64}}
                    ]
                }],
                "generationConfig": {"temperature": 0}
            }

            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
    GEMINI_URL,
    data=data,
    headers={
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY
    },
    method="POST"
)

            with urllib.request.urlopen(req, timeout=30) as resp:
                respuesta = json.loads(resp.read().decode("utf-8"))

            texto = respuesta["candidates"][0]["content"]["parts"][0]["text"].strip()
            texto = re.sub(r"^```json\s*", "", texto)
            texto = re.sub(r"\s*```$", "", texto)

            resultado = json.loads(texto)

            self.datos["patente"] = resultado.get("patente", "").strip()
            self.datos["orden"] = resultado.get("orden", "").strip()
            self.datos["siniestro"] = resultado.get("siniestro", "").strip()
            self.datos["modelo"] = resultado.get("modelo", "").strip()
            self.datos["remito"] = resultado.get("remito", "").strip()

            repuestos_raw = resultado.get("repuestos", [])
            repuestos = []
            vistos = set()
            for r in repuestos_raw:
                codigo = str(r.get("codigo", "")).strip()
                if not codigo:
                    continue
                clave = re.sub(r"[^A-Z0-9]", "", codigo.upper())
                if clave in vistos:
                    continue
                vistos.add(clave)
                try:
                    precio_num = float(str(r.get("precio", "0")).replace(",", ".").replace(" ", ""))
                except:
                    precio_num = 0.0
                repuestos.append({
                    "codigo": codigo,
                    "descripcion": str(r.get("descripcion", "")),
                    "nombre": str(r.get("descripcion", "")),
                    "cantidad": "1.00",
                    "precio": str(precio_num),
                    "precio_num": precio_num,
                    "precio_sin_iva": round(precio_num / 1.21, 2)
                })

            self.datos["repuestos"] = repuestos
            print(f"=== GEMINI OCR: {len(repuestos)} repuestos ===")
            for rep in repuestos:
                print(f"  {rep['codigo']}")
            return True

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Error Gemini OCR: {e}")
            return False

    def recibir_texto(self, texto):
        """Compatibilidad con versión anterior - no usado con Gemini"""
        self.texto = texto
        self.lineas = [l for l in texto.split("\n") if l.strip()]
        return True

    def extraer_datos(self):
        return self.datos