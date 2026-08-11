# ocr.py - Versión con RapidOCR (no necesita Tesseract)

import re
from rapidocr import RapidOCR
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import PDF_CONFIG

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
        self.engine = RapidOCR()

    def abrir_imagen(self, ruta_imagen):
        try:
            resultado = self.engine(ruta_imagen)

            if resultado is None or resultado.boxes is None:
                self.texto = ""
                self.lineas = []
                return False

            lineas_dict = {}
            for box, texto, score in zip(resultado.boxes, resultado.txts, resultado.scores):
                if not texto or not texto.strip():
                    continue
                y = round((box[0][1] + box[2][1]) / 2, 1)
                x = box[0][0]
                texto_limpio = texto.strip()

                encontro = False
                for y_existente in lineas_dict:
                    if abs(y - y_existente) < 8:
                        lineas_dict[y_existente].append((x, texto_limpio))
                        encontro = True
                        break
                if not encontro:
                    lineas_dict[y] = [(x, texto_limpio)]

            lineas_ordenadas = []
            for y in sorted(lineas_dict.keys()):
                partes = sorted(lineas_dict[y], key=lambda p: p[0])
                texto_linea = " ".join([p[1] for p in partes])
                lineas_ordenadas.append(texto_linea)

            self.lineas = lineas_ordenadas
            self.texto = "\n".join(lineas_ordenadas)
            print("=== TEXTO OCR ===")
            print(self.texto)
            print("=================")
            return True

        except Exception as e:
            print(f"Error al procesar imagen: {e}")
            return False

    def _normalizar_patente(self, texto):
        t = texto.upper().strip()
        t = t.replace("O", "D").replace("Q", "D")
        if re.match(r'^[A-Z]{2}[0-9]{3}[A-Z]{2}$', t):
            return t
        return None

    def extraer_datos(self):
        if not self.texto:
            return self.datos

        texto_upper = self.texto.upper()

        patente_match = re.search(r'[A-Z]{2}[0-9]{3}[A-Z]{2}', texto_upper)
        if patente_match:
            patente_raw = patente_match.group(0)
            patente_corregida = self._normalizar_patente(patente_raw)
            if patente_corregida:
                self.datos["patente"] = patente_corregida
            else:
                self.datos["patente"] = patente_raw

        orden_match = re.search(r'ORDEN\s*[:]*\s*([0-9\-]+)', texto_upper, re.IGNORECASE)
        if orden_match:
            self.datos["orden"] = orden_match.group(1)
        else:
            orden_match = re.search(r'([0-9]{3,4}[-][0-9]{3,5})', texto_upper)
            if orden_match:
                self.datos["orden"] = orden_match.group(1)

        modelo_match = re.search(r'MODELO\s*[:]*\s*(.+?)(?:\n|$)', texto_upper, re.IGNORECASE)
        if modelo_match:
            modelo = modelo_match.group(1).strip()
            modelo = re.sub(r'\s*(Perc|Desc|IVA|Descuento|I\.V\.A|Percepci|Perc\.).*', '', modelo, flags=re.IGNORECASE)
            self.datos["modelo"] = modelo.strip()
        else:
            modelo_match = re.search(r'(VW\s+[A-Z0-9\s/]+)', texto_upper, re.IGNORECASE)
            if modelo_match:
                self.datos["modelo"] = modelo_match.group(1).strip()

        siniestro_match = re.search(r'SINIESTRO\s*[:]*\s*([0-9\-]+)', texto_upper, re.IGNORECASE)
        if not siniestro_match:
            siniestro_match = re.search(r'([0-9]{3}[-][0-9][-][0-9]{6})', texto_upper)
        if siniestro_match:
            self.datos["siniestro"] = siniestro_match.group(1)

        remito_match = re.search(r'REMITO\s*[:]*\s*([0-9\s]+)', texto_upper, re.IGNORECASE)
        if remito_match:
            self.datos["remito"] = remito_match.group(1).replace(" ", "")

        self._extraer_repuestos()

        return self.datos

    def _parsear_precio(self, texto_precio):
        t = texto_precio.strip()
        t = t.replace("$", "").replace(" ", "")

        if "," in t and "." in t:
            if t.rindex(",") > t.rindex("."):
                t = t.replace(".", "").replace(",", ".")
            else:
                t = t.replace(",", "")
        elif "," in t:
            t = t.replace(",", ".")
        elif "." in t:
            partes = t.split(".")
            if len(partes) > 2:
                t = "".join(partes[:-1]) + "." + partes[-1]

        try:
            return float(t)
        except:
            return 0.0

    def _extraer_repuestos(self):
        repuestos = []
        patron_codigo = re.compile(
            r'([0-9A-Z]{2,}[-][0-9A-Z]{1,}[-][0-9A-Z]{1,}(?:[-][0-9A-Z]{1,})*)'
        )
        patron_precio = re.compile(r'(\d[\d.,]*\d)')
        patron_cantidad = re.compile(r'\b(\d+\.\d{2})\b')

        siniestro = self.datos.get("siniestro", "").replace("-", "")
        orden = self.datos.get("orden", "").replace("-", "")
        patente = self.datos.get("patente", "").replace("-", "")

        for linea in self.lineas:
            codigos = patron_codigo.findall(linea.upper())
            precios_raw = patron_precio.findall(linea)
            cantidades = patron_cantidad.findall(linea)

            precios = []
            for p in precios_raw:
                val = self._parsear_precio(p)
                if val > 100:
                    precios.append(p)

            if not codigos:
                continue

            for codigo in codigos:
                sin_guiones = codigo.replace("-", "")

                if len(sin_guiones) < 8:
                    continue
                if sin_guiones == siniestro:
                    continue
                if sin_guiones.startswith(orden) and len(sin_guiones) <= len(orden) + 3:
                    continue
                if sin_guiones == patente:
                    continue
                if len(sin_guiones) == 10 and sin_guiones.isdigit():
                    continue
                if len(sin_guiones) == 11 and sin_guiones.isdigit():
                    continue
                if re.match(r'^\d{2}[-]\d{8}[-]\d$', codigo):
                    continue

                cantidad = "1.00"
                for c in cantidades:
                    if c != "0.00":
                        cantidad = c
                        break

                precio = "0"
                if precios:
                    precio = precios[-1]

                repuestos.append({
                    "codigo": codigo,
                    "descripcion": "",
                    "cantidad": cantidad,
                    "precio": precio
                })

        vistos = set()
        repuestos_final = []
        for r in repuestos:
            clave = r["codigo"].replace("-", "")
            if clave not in vistos:
                vistos.add(clave)
                repuestos_final.append(r)

        self.datos["repuestos"] = repuestos_final
