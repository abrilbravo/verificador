# ocr.py - Versión con RapidOCR (no necesita Tesseract)

import re
from rapidocr import RapidOCR
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import PDF_CONFIG
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

        CORTE = (
            r'CHASIS|CONTACTO|BUENOS\s+AIRES|LA\s+REJA|ROSARIO|CÓRDOBA|MENDOZA'
            r'|PATENTE|SINIESTRO|ORDEN|REMITO|TOTAL|TIPO\s+REQUERIMIENTO'
            r'|N[º°]?\s*PLACA|TEL\s*:|MAIL\s*:'
        )
        modelo_match = re.search(
            rf'MODELO\s*[:]*\s*(.+?)(?=\s+(?:{CORTE})|\n|$)',
            texto_upper, re.IGNORECASE
        )
        if modelo_match:
            modelo = modelo_match.group(1).strip()
            modelo = re.sub(r'^[:\s]+', '', modelo).strip()
            self.datos["modelo"] = modelo
        else:
            modelo_match = re.search(r'(VW\s+[A-Z0-9\s/]+)', texto_upper, re.IGNORECASE)
            if modelo_match:
                self.datos["modelo"] = modelo_match.group(1).strip()

        siniestro_match = re.search(r'SINIESTRO\s*[:]*\s*N[º°]?\.?\s*:?\s*([0-9][0-9\-]*)', texto_upper, re.IGNORECASE)
        if not siniestro_match:
            siniestro_match = re.search(r'SINIESTRO\s*[:]*\s*([0-9][0-9\-]*)', texto_upper, re.IGNORECASE)
        if not siniestro_match:
            siniestro_match = re.search(r'([0-9]{3}[-][0-9][-][0-9]{6})', texto_upper)
        if siniestro_match:
            self.datos["siniestro"] = siniestro_match.group(1).strip('-')

        remito_match = re.search(r'REMITO\s*[:]*\s*([0-9\s]+)', texto_upper, re.IGNORECASE)
        if remito_match:
            self.datos["remito"] = remito_match.group(1).replace(" ", "")

        self._extraer_repuestos()

        return self.datos

    def _extraer_repuestos(self):
        repuestos = []
        vistos = set()

        siniestro = self.datos.get("siniestro", "").replace("-", "")
        orden = self.datos.get("orden", "").replace("-", "")
        patente = self.datos.get("patente", "").replace("-", "")

        def es_codigo_valido(clave):
            if not clave:
                return False
            if clave == siniestro or clave == patente:
                return False
            if clave.startswith(orden) and len(clave) <= len(orden) + 3:
                return False
            if clave.isdigit() and len(clave) in (10, 11):
                return False
            return True

        def agregar(codigo, descripcion="", nombre="", precio="0"):
            clave = re.sub(r'[^A-Z0-9]', '', codigo.upper())
            if clave and clave not in vistos and es_codigo_valido(clave):
                vistos.add(clave)
                try:
                    precio_num = float(precio)
                except:
                    precio_num = 0.0
                repuestos.append({
                    "codigo": codigo,
                    "descripcion": descripcion,
                    "nombre": nombre,
                    "cantidad": "1.00",
                    "precio": precio,
                    "precio_num": precio_num,
                    "precio_sin_iva": round(precio_num / 1.21, 2)
                })

        # 1) Bloques 'Inspec: ... Rep: ...' con PRECIO y NOMBRE DE PIEZA
        for repuesto in parsear_repuestos(self.texto):
            agregar(
                repuesto.get("codigo", ""),
                repuesto.get("descripcion", ""),
                repuesto.get("nombre", ""),
                repuesto.get("precio", "0"),
            )

        # 2) Fallback: códigos sueltos en otras líneas (solo códigos que empiezan con dígito)
        for linea in self.lineas:
            if re.search(r'Inspec\s*:', linea, re.IGNORECASE):
                continue
            for codigo in extraer_codigos(linea, patron=PATRON_CODIGO_DIGITO):
                agregar(codigo)

        self.datos["repuestos"] = repuestos