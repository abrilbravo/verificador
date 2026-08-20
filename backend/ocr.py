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
            
            # 2. Reducir a 1100px (justo para 500MB)
            max_dim = 1100
            if max(imagen.size) > max_dim:
                ratio = max_dim / max(imagen.size)
                new_size = (int(imagen.size[0] * ratio), int(imagen.size[1] * ratio))
                imagen = imagen.resize(new_size, Image.LANCZOS)
                print(f"📐 Redimensionada a: {imagen.size}")
            
            # 3. Contraste agresivo para definir letras
            from PIL import ImageOps, ImageEnhance
            imagen = ImageOps.autocontrast(imagen, cutoff=5)
            imagen = ImageEnhance.Contrast(imagen).enhance(1.8)
            
            # 4. Tesseract
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
        """Extrae datos del texto usando regex - optimizado para tablas ERP"""
        texto = self.texto
        lineas = [l.strip() for l in texto.split('\n') if l.strip()]
        
        patron_remito = re.compile(r'REMITO\s*(\d{5,6})', re.IGNORECASE)
        match = patron_remito.search(texto)
        if match:
            self.datos["remito"] = match.group(1)
        
        patron_orden = re.compile(r'ORDEN\s*(\d{7,8})', re.IGNORECASE)
        match = patron_orden.search(texto)
        if match:
            self.datos["orden"] = match.group(1)
        
        patron_siniestro = re.compile(r'SINIESTRO\s*(\d{2,3}[\s\-\.]?\d{1,2}[\s\-\.]?\d{4,7})', re.IGNORECASE)
        match = patron_siniestro.search(texto)
        if match:
            self.datos["siniestro"] = match.group(1).replace(' ', '').replace('.', '-')
        
        patron_modelo = re.compile(r'MODELO\s*(.+?)(?=\s*PATENTE|\s*$)', re.IGNORECASE | re.DOTALL)
        match = patron_modelo.search(texto)
        if match:
            self.datos["modelo"] = match.group(1).strip()
        
        patron_patente = re.compile(r'PATENTE\s*([A-Z0-9]+)', re.IGNORECASE)
        match = patron_patente.search(texto)
        if match:
            self.datos["patente"] = match.group(1).upper()
        
        patron_codigo_linea = re.compile(r'([A-Z0-9]{2,4}(?:\s*-\s*[A-Z0-9]{1,6}){1,5})')
        patron_precio_linea = re.compile(r'(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})')
        
        repuestos = []
        for linea in lineas:
            cod_match = patron_codigo_linea.search(linea)
            if not cod_match:
                continue
            
            codigo = cod_match.group(1).replace(' ', '').replace('--', '-').upper()
            
            partes = codigo.split('-')
            if len(partes) < 2 or len(codigo) < 6:
                continue
            
            skip_words = ['REMITO', 'ORDEN', 'SINIESTRO', 'MODELO', 'PATENTE', 'CENTRAL', 'DESCRIPCION',
                          'COMPROBANTE', 'NUMERO', 'IMPRESION', 'FECHA', 'TIPO', 'VENTA', 'GRUPO',
                          'CTA', 'DIA', 'MES', 'ANIO', 'SISTEMA', 'CIRCUITO', 'CARGAR', 'CONSULTA',
                          'COMPROBANTES', 'VER', 'RECUPERAR', 'GENERAR', 'RESERVA', 'CONFIRMAR',
                          'CANCELAR', 'SALIR', 'NUEVO', 'BAJO', 'LIMIT', 'DEMANDA', 'STOCK',
                          'ORGANIZACION', 'EMPRESA', 'USUARIO', 'TERMINAL', 'GESTION', 'CORREDOR',
                          'PERCEPCION', 'ZONA', 'COTIZACION', 'GRAVADO', 'IVA', 'EXENTO',
                          'DESC', 'REC', 'IMPUESTOS', 'PASANTES', 'PERFIL', 'LISTON',
                          'SIN', 'CON', 'CTA', 'DCTO', 'DESCUENTO']
            
            code_parts = [p for p in partes if not p.isdigit() and len(p) > 1]
            if any(sw in ''.join(code_parts).upper() for sw in skip_words):
                continue
            
            precios_en_linea = patron_precio_linea.findall(linea)
            
            precio_num = 0.0
            precio_str = "0"
            if precios_en_linea:
                precio_num = self._limpiar_precio_arg(precios_en_linea[-1])
                precio_str = str(precio_num) if precio_num > 0 else "0"
            
            cant_match = re.search(r'(\d+[,\.]\d{2})\s', linea[cod_match.end():])
            cantidad = "1.00"
            if cant_match:
                cantidad = cant_match.group(1).replace(',', '.')
            
            repuestos.append({
                "codigo": codigo,
                "descripcion": "",
                "nombre": "",
                "cantidad": cantidad,
                "precio": precio_str,
                "precio_num": precio_num,
                "precio_sin_iva": round(precio_num / 1.21, 2) if precio_num > 0 else 0
            })
        
        if not repuestos:
            patron_codigo_simple = re.compile(r'([A-Z0-9]{2,4}-[A-Z0-9]{1,6}(?:-[A-Z0-9]{1,6}){0,4})')
            codigos_raw = patron_codigo_simple.findall(texto)
            patron_precio_simple = re.compile(r'(\d{1,3}(?:\.\d{3})*,\d{2})')
            precios_raw = patron_precio_simple.findall(texto)
            
            codigos_filtrados = []
            for c in codigos_raw:
                partes = c.split('-')
                if len(partes) >= 2 and len(c) >= 6:
                    c_upper = c.upper()
                    if not any(sw in c_upper for sw in skip_words):
                        codigos_filtrados.append(c_upper)
            
            for i, codigo in enumerate(codigos_filtrados):
                precio_num = 0.0
                precio_str = "0"
                if i < len(precios_raw):
                    precio_num = self._limpiar_precio_arg(precios_raw[i])
                    precio_str = str(precio_num) if precio_num > 0 else "0"
                repuestos.append({
                    "codigo": codigo,
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
