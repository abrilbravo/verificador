# pdf.py
import pdfplumber
import re

class LectorPDF:
    def __init__(self):
        self.texto = ""
        self.datos = {
            "cliente": "",
            "orden": "",
            "siniestro": "",
            "modelo": "",
            "patente": "",
            "repuestos": [],
            "total": "0"
        }

    def abrir(self, ruta_pdf):
        self.texto = ""
        try:
            with pdfplumber.open(ruta_pdf) as pdf:
                for pagina in pdf.pages:
                    texto = pagina.extract_text()
                    if texto:
                        self.texto += texto + "\n"
            print("=== TEXTO PDF ===")
            print(self.texto[:500])  # Mostrar primeras líneas para debug
            print("=================")
            return True
        except Exception as e:
            print(f"Error al abrir PDF: {e}")
            return False

    def buscar(self, patron):
        if not self.texto:
            return ""
        resultado = re.search(patron, self.texto, re.IGNORECASE)
        if resultado:
            return resultado.group(1).strip()
        return ""

    def extraer_datos(self):
        self.datos["cliente"] = self.buscar(r"Federación?\s*Patronal\s*Seguros")

        self.datos["orden"] = self.buscar(r"N[°º]\s*Orden:\s*([0-9]+)")
        if not self.datos["orden"]:
            self.datos["orden"] = self.buscar(r"Orden:\s*([0-9]+)")
        if not self.datos["orden"]:
            self.datos["orden"] = self.buscar(r"N[º°]\s*([0-9]+)")
        if not self.datos["orden"]:
            # Buscar en el formato del PDF: "Nº Orden: 6077073"
            orden_match = re.search(r'N[º°]\s*Orden:\s*([0-9]+)', self.texto)
            if orden_match:
                self.datos["orden"] = orden_match.group(1)

        self.datos["siniestro"] = self.buscar(r"SINIESTRO\s*[:]*\s*([0-9\-]+)")
        if not self.datos["siniestro"]:
            siniestro_match = re.search(r'([0-9]{3}[-][0-9][-][0-9]{6})', self.texto)
            if siniestro_match:
                self.datos["siniestro"] = siniestro_match.group(1)

        self.datos["patente"] = self.buscar(r"PATENTE\s*[:]*\s*([A-Z0-9]+)")
        if not self.datos["patente"]:
            patente_match = re.search(r'\b([A-Z]{2}[0-9]{3}[A-Z]{2})\b', self.texto)
            if patente_match:
                self.datos["patente"] = patente_match.group(1)

        self.datos["modelo"] = self.buscar(r"MODELO\s*[:]*\s*(.+?)(?:\n|$)")
        if not self.datos["modelo"]:
            modelo_match = re.search(r'(VW\s+[A-Z0-9\s/]+)', self.texto, re.IGNORECASE)
            if modelo_match:
                self.datos["modelo"] = modelo_match.group(1).strip()

        # Buscar total
        total_match = re.search(r'TOTAL\s*[:]*\s*([0-9,\.]+)', self.texto)
        if total_match:
            self.datos["total"] = total_match.group(1)

        self.extraer_repuestos()

        return self.datos

    def _parsear_precio(self, texto_precio):
        """Convertir string de precio a float"""
        if not texto_precio:
            return 0.0
        
        t = texto_precio.strip()
        t = t.replace("$", "").replace(" ", "").replace("'", "")
        
        # Si tiene punto y coma (formato argentino: 13.140,00)
        if "," in t and "." in t:
            # Si el punto está antes de la coma, es formato argentino
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

    def formatear_codigo(self, codigo):
        """Formatear código de repuesto al formato estándar"""
        if not codigo:
            return ""

        codigo = codigo.strip().upper()
        
        # Eliminar -a- o -a al final (variantes)
        codigo = re.sub(r'-A$', '', codigo)
        codigo = re.sub(r'-A-$', '', codigo)
        codigo = re.sub(r'--$', '', codigo)
        
        # Eliminar fechas al final (ej: --14-08-2026 o -14-08-2026)
        codigo = re.sub(r'--\d{2}-\d{2}-\d{4}$', '', codigo)
        codigo = re.sub(r'-\d{2}-\d{2}-\d{4}$', '', codigo)
        
        # Limpiar espacios
        codigo = re.sub(r'\s+', '', codigo)
        
        # Si ya tiene formato correcto (3-3-3-1 o similar)
        if re.match(r'^[A-Z0-9]{2,4}-[A-Z0-9]{2,4}-[A-Z0-9]{2,4}-[A-Z0-9]{1,2}$', codigo):
            return codigo
        
        # Si tiene guiones pero no en formato correcto
        if '-' in codigo:
            partes = [p for p in codigo.split('-') if p]
            if len(partes) >= 3:
                # Intentar formatear
                parte1 = partes[0] if len(partes[0]) >= 3 else partes[0]
                parte2 = partes[1] if len(partes[1]) >= 3 else partes[1]
                parte3 = partes[2] if len(partes[2]) >= 3 else partes[2]
                parte4 = partes[3] if len(partes) > 3 else ""
                if parte4:
                    return f"{parte1}-{parte2}-{parte3}-{parte4}"
                return f"{parte1}-{parte2}-{parte3}"
        
        # Código sin guiones - intentar formatear
        if len(codigo) >= 8:
            # Buscar patrón: 5Z0807183B -> 5Z0-807-183-B
            if len(codigo) == 10:
                return f"{codigo[:3]}-{codigo[3:6]}-{codigo[6:9]}-{codigo[9:]}"
            elif len(codigo) == 11:
                return f"{codigo[:3]}-{codigo[3:6]}-{codigo[6:9]}-{codigo[9:]}"
            elif len(codigo) >= 12:
                return f"{codigo[:3]}-{codigo[3:6]}-{codigo[6:9]}-{codigo[9:]}"
        
        return codigo

    def extraer_repuestos(self):
        """Extraer repuestos del texto del PDF"""
        repuestos = []
        codigos_encontrados = set()
        
        # Buscar líneas que contengan códigos de repuesto
        # Patrón: Rep: 5Z0807183B-a- - 14-08-2026
        # O también: Rep: 5U0959455C-a- - 14-08-2026
        
        lineas = self.texto.split('\n')
        
        for i, linea in enumerate(lineas):
            # Buscar líneas con "Rep:" o "Rp:"
            if 'Rep:' not in linea and 'Rp:' not in linea:
                continue
            
            # Buscar el código del repuesto
            codigo_match = re.search(r'[Rr]ep:\s*([A-Z0-9\-]+)', linea)
            if not codigo_match:
                # Intentar con otro patrón
                codigo_match = re.search(r'[Rr]p:\s*([A-Z0-9\-]+)', linea)
            
            if not codigo_match:
                continue
            
            codigo_raw = codigo_match.group(1).strip()
            codigo_formateado = self.formatear_codigo(codigo_raw)
            
            # Buscar precio en la misma línea
            precio = "0"
            
            # Patrón para precios: números con puntos y comas
            # Ej: 13,140.00 o 13.140,00
            precios = re.findall(r'([0-9]{1,3}(?:[.,][0-9]{3})*[.,][0-9]{2})', linea)
            
            if precios:
                # Tomar el último precio (suele ser el precio unitario)
                precio = precios[-1]
            else:
                # Buscar en líneas siguientes
                for offset in range(1, 4):
                    if i + offset < len(lineas):
                        siguiente = lineas[i + offset]
                        precios_sig = re.findall(r'([0-9]{1,3}(?:[.,][0-9]{3})*[.,][0-9]{2})', siguiente)
                        if precios_sig:
                            precio = precios_sig[-1]
                            break
            
            # También buscar cantidad
            cantidad = "1"
            cant_match = re.search(r'\b(\d+)\s*[xX]\s*', linea)
            if cant_match:
                cantidad = cant_match.group(1)
            
            # Buscar descripción (entre el código y el precio)
            descripcion = ""
            # Intentar extraer descripción de la línea
            # Formato: "RD 500 - GUIA DE PARAGOLPES IZC" o similar
            desc_match = re.search(r'[A-Z]{2}\s+\d+\s*[-]\s*(.+?)(?:\s+\d|$)', linea)
            if desc_match:
                descripcion = desc_match.group(1).strip()
            
            # Verificar que no sea un código duplicado
            clave = codigo_formateado.replace("-", "")
            if clave and clave not in codigos_encontrados and len(clave) >= 6:
                codigos_encontrados.add(clave)
                
                # Parsear precio
                precio_float = self._parsear_precio(precio)
                
                repuestos.append({
                    "codigo": codigo_formateado,
                    "descripcion": descripcion,
                    "cantidad": cantidad,
                    "precio": str(precio_float) if precio_float > 0 else "0"
                })
                
                print(f"✅ Repuesto encontrado: {codigo_formateado} - ${precio_float}")
        
        self.datos["repuestos"] = repuestos
        print(f"📊 Total repuestos encontrados: {len(repuestos)}")
        return repuestos

    def imprimir(self):
        print("\n" + "="*60)
        print("DATOS EXTRAIDOS DEL PDF")
        print("="*60)
        print(f"CLIENTE: {self.datos.get('cliente')}")
        print(f"ORDEN: {self.datos.get('orden')}")
        print(f"SINIESTRO: {self.datos.get('siniestro')}")
        print(f"PATENTE: {self.datos.get('patente')}")
        print(f"MODELO: {self.datos.get('modelo')}")
        print(f"TOTAL: ${self.datos.get('total')}")
        print("\nREPUESTOS ENCONTRADOS:")
        print("-"*60)
        for r in self.datos.get("repuestos", []):
            print(f"  {r.get('codigo')} - ${r.get('precio')}")
        print("="*60)

    def ver_texto_crudo(self):
        print("\n" + "="*60)
        print("TEXTO CRUDO DEL PDF")
        print("="*60)
        print(self.texto)
        print("="*60)