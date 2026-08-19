# backend/ocr.py - Tesseract optimizado para 500MB RAM

import re
import os
import sys

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

try:
    import pytesseract
    from PIL import Image, ImageFilter
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
        """Extrae texto usando Tesseract optimizado para 500MB RAM"""
        try:
            if not PYTESSERACT_DISPONIBLE:
                print("❌ PyTesseract no disponible")
                return False

            print("=== Usando PyTesseract OCR ===")
            
            imagen = Image.open(ruta_imagen)
            print(f"📐 Tamaño original: {imagen.size}")
            
            # 1. Convertir a escala de grises
            imagen = imagen.convert('L')
            
            # 2. Ecualizar contraste agresivamente
            from PIL import ImageOps
            imagen = ImageOps.autocontrast(imagen, cutoff=5)
            
            # 3. Endurecer: multiplicar contraste
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Contrast(imagen)
            imagen = enhancer.enhance(2.0)
            
            # 4. Sharpen para definir bordes de letras
            enhancer = ImageEnhance.Sharpness(imagen)
            imagen = enhancer.enhance(2.0)
            
            # 5. Tesseract con detección de tabla
            config = '--psm 6 --oem 3'
            texto_completo = pytesseract.image_to_string(imagen, lang='spa', config=config)
            
            del imagen
            
            if not texto_completo.strip():
                print("⚠️ No se encontró texto en la imagen")
                return False

            print(f"✅ Texto extraído: {len(texto_completo)} caracteres")
            print(f"--- TEXTO OCR ---\n{texto_completo}\n------------------")
            
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

    def _limpiar_precio_arg(self, texto_precio):
        """Convierte precio formato argentino: 148.264,47 -> 148264.47"""
        t = texto_precio.strip()
        t = t.replace(' ', '')
        if ',' in t:
            partes = t.split(',')
            parte_decimal = partes[-1]
            parte_entera = ''.join(partes[:-1]).replace('.', '')
            t = parte_entera + '.' + parte_decimal
        else:
            t = t.replace('.', '')
        try:
            return float(t)
        except:
            return 0.0

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
        
        patron_modelo = re.compile(r'MODELO\s*(.+?)(?=\s*PATENTE|\s*$)', re.IGNORECASE | re.DOTALL)
        match = patron_modelo.search(texto)
        if match:
            self.datos["modelo"] = match.group(1).strip()
        
        patron_patente = re.compile(r'PATENTE\s*([A-Z0-9]+)', re.IGNORECASE)
        match = patron_patente.search(texto)
        if match:
            self.datos["patente"] = match.group(1).upper()
        
        # Codigos VW: captura con guiones y sufijos separados por espacio
        # 5U0-953-455-C, 5U0-853-653-F -041, 5U0-807-221-AC-GRU, 5U0-823-186
        patron_codigo = re.compile(r'\b([A-Z0-9]{2,4}(?:-[A-Z0-9]{1,6}){1,5})\b')
        codigos_raw = patron_codigo.findall(texto)
        
        # Filtrar códigos muy cortos o que son palabras comunes
        codigos_filtrados = []
        for c in codigos_raw:
            partes = c.split('-')
            if len(partes) >= 2 and len(c) >= 6:
                codigos_filtrados.append(c)
        
        # Precios: 148.264,47 o 75.785,12 o 3.471,07 o 420.330,58
        patron_precio = re.compile(r'(\d{1,3}(?:\.\d{3})*,\d{2})')
        precios_raw = patron_precio.findall(texto)
        
        # Sin puntos de miles: 18677,69 o 3471,07
        if len(precios_raw) < len(codigos_filtrados):
            patron_precio2 = re.compile(r'(\d{4,6},\d{2})')
            precios_raw2 = patron_precio2.findall(texto)
            precios_raw.extend(precios_raw2)
        
        print(f"📋 Códigos encontrados ({len(codigos_filtrados)}): {codigos_filtrados}")
        print(f"💰 Precios encontrados ({len(precios_raw)}): {precios_raw}")
        
        # Emparejar códigos con precios (el precio va después del código)
        repuestos = []
        for i, codigo in enumerate(codigos_filtrados):
            precio_num = 0.0
            precio_str = "0"
            if i < len(precios_raw):
                precio_num = self._limpiar_precio_arg(precios_raw[i])
                precio_str = str(precio_num)
            
            repuestos.append({
                "codigo": codigo.upper(),
                "descripcion": "",
                "nombre": "",
                "cantidad": "1.00",
                "precio": precio_str,
                "precio_num": precio_num,
                "precio_sin_iva": round(precio_num / 1.21, 2) if precio_num > 0 else 0
            })
        
        self.datos["repuestos"] = repuestos
        print(f"✅ {len(repuestos)} repuestos encontrados")

    def extraer_datos(self):
        return self.datos
