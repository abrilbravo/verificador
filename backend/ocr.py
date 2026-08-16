# backend/ocr.py - Versión con PyTesseract (más liviano)

import re
import os
import sys
import subprocess
import tempfile

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

# Intentar importar PyTesseract
try:
    import pytesseract
    from PIL import Image
    PYTESSERACT_DISPONIBLE = True
    print("✅ PyTesseract disponible")
except ImportError:
    PYTESSERACT_DISPONIBLE = False
    print("❌ PyTesseract no instalado")

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
        """Extrae texto usando Tesseract (más liviano)"""
        try:
            if not PYTESSERACT_DISPONIBLE:
                print("❌ PyTesseract no disponible")
                return False

            print("=== Usando PyTesseract OCR ===")
            
            # Abrir la imagen con PIL
            imagen = Image.open(ruta_imagen)
            
            # Reducir tamaño para ahorrar RAM
            max_dim = 1200
            if max(imagen.size) > max_dim:
                imagen.thumbnail((max_dim, max_dim))
                print(f"📐 Imagen redimensionada a: {imagen.size}")
            
            # Extraer texto con Tesseract
            texto_completo = pytesseract.image_to_string(imagen, lang='spa')
            
            if not texto_completo.strip():
                print("⚠️ No se encontró texto en la imagen")
                return False

            print(f"✅ Texto extraído: {len(texto_completo)} caracteres")
            
            # Procesar el texto
            self.recibir_texto(texto_completo)
            self._extraer_datos_desde_texto()
            
            print(f"=== DATOS EXTRAÍDOS ===")
            print(f"Patente: {self.datos['patente']}")
            print(f"Orden: {self.datos['orden']}")
            print(f"Siniestro: {self.datos['siniestro']}")
            print(f"Modelo: {self.datos['modelo']}")
            print(f"Remito: {self.datos['remito']}")
            print(f"Repuestos: {len(self.datos['repuestos'])}")
            
            return True

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"❌ Error en OCR: {e}")
            return False

    def recibir_texto(self, texto):
        self.texto = texto
        self.lineas = [l for l in texto.split("\n") if l.strip()]
        return True

    def _extraer_datos_desde_texto(self):
        """Extrae datos del texto usando regex"""
        texto = self.texto
        
        patron_remito = re.compile(r'REMITO\s*(\d{5,6})', re.IGNORECASE)
        match = patron_remito.search(texto)
        if match:
            self.datos["remito"] = match.group(1)
        
        patron_orden = re.compile(r'ORDEN\s*(\d{7,8})', re.IGNORECASE)
        match = patron_orden.search(texto)
        if match:
            self.datos["orden"] = match.group(1)
        
        patron_siniestro = re.compile(r'SINIESTRO\s*(\d{2,3}-\d{1,2}-\d{5,7})', re.IGNORECASE)
        match = patron_siniestro.search(texto)
        if match:
            self.datos["siniestro"] = match.group(1)
        
        patron_modelo = re.compile(r'MODELO\s*([A-Z0-9\s]+?)(?=\s+[A-Z]{2,3}\d{3}|$)', re.IGNORECASE)
        match = patron_modelo.search(texto)
        if match:
            self.datos["modelo"] = match.group(1).strip()
        
        patron_patente = re.compile(r'\b([A-Z]{2,3}\d{3}[A-Z]{0,2})\b')
        match = patron_patente.search(texto)
        if match:
            self.datos["patente"] = match.group(1)
        
        patron_codigo = re.compile(r'\b([A-Z0-9]{2,3}-[A-Z0-9]{3}-[A-Z0-9]{3,4}-[A-Z0-9]*(?:\s*-[A-Z0-9]+)?)\b')
        codigos = patron_codigo.findall(texto)
        
        patron_precio = re.compile(r'(\d{1,3}(?:,\d{3})*\.\d{2})')
        precios = patron_precio.findall(texto)
        
        repuestos = []
        for i, codigo in enumerate(codigos):
            if i < len(precios):
                codigo_limpio = codigo.replace("-", "").replace(" ", "")
                precio_limpio = precios[i].replace(",", "")
                
                repuestos.append({
                    "codigo": codigo_limpio,
                    "descripcion": "",
                    "nombre": "",
                    "cantidad": "1.00",
                    "precio": precio_limpio,
                    "precio_num": float(precio_limpio),
                    "precio_sin_iva": round(float(precio_limpio) / 1.21, 2)
                })
        
        self.datos["repuestos"] = repuestos
        print(f"✅ {len(repuestos)} repuestos encontrados")

    def extraer_datos(self):
        return self.datos