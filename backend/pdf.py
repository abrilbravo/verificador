# backend/pdf.py - VERSIÓN CORREGIDA

import pdfplumber
import re
from typing import Dict, List, Optional

class LectorPDF:
    def __init__(self):
        self.pdf = None
        self.texto_completo = ""
        self.datos = {}
        self.repuestos = []
        
    def abrir(self, ruta_pdf):
        """Abrir el archivo PDF"""
        self.pdf = pdfplumber.open(ruta_pdf)
        self.texto_completo = self._extraer_texto_completo()
        return self
    
    def _extraer_texto_completo(self) -> str:
        """Extraer todo el texto del PDF"""
        texto = ""
        for pagina in self.pdf.pages:
            texto += pagina.extract_text() or ""
        return texto
    
    def _limpiar_texto(self, texto: str) -> str:
        """Limpiar texto para mejor procesamiento"""
        if not texto:
            return ""
        # Reemplazar saltos de línea y espacios múltiples
        texto = texto.replace('\n', ' ').replace('\r', '')
        texto = re.sub(r'\s+', ' ', texto)
        return texto.strip()
    
    def extraer_datos(self) -> Dict:
        """Extraer los datos principales del PDF"""
        texto = self._limpiar_texto(self.texto_completo)
        
        # Buscar datos básicos
        datos = {
            'cliente': self._buscar_cliente(texto),
            'orden': self._buscar_orden(texto),
            'siniestro': self._buscar_siniestro(texto),
            'patente': self._buscar_patente(texto),
            'modelo': self._buscar_modelo(texto),
            'total': self._buscar_total(texto),
            'repuestos': []
        }
        
        self.datos = datos
        return datos
    
    def _buscar_cliente(self, texto: str) -> str:
        """Buscar el nombre del cliente"""
        patron = r"Federación Patronal Seguros S\.A\."
        match = re.search(patron, texto, re.IGNORECASE)
        return match.group(0) if match else "Cliente no encontrado"
    
    def _buscar_orden(self, texto: str) -> str:
        """Buscar número de orden"""
        patron = r"N[º°]?\.?\s*Orden:\s*([0-9]+)"
        match = re.search(patron, texto, re.IGNORECASE)
        return match.group(1) if match else ""
    
    def _buscar_siniestro(self, texto: str) -> str:
        """Buscar número de siniestro"""
        patron = r"SINIESTRO\s*([0-9\-]+)"
        match = re.search(patron, texto, re.IGNORECASE)
        return match.group(1) if match else ""
    
    def _buscar_patente(self, texto: str) -> str:
        """Buscar patente"""
        patron = r"PATENTE\s*([A-Z0-9]+)"
        match = re.search(patron, texto, re.IGNORECASE)
        return match.group(1) if match else ""
    
    def _buscar_modelo(self, texto: str) -> str:
        """Buscar modelo"""
        patron = r"MODELO\s*(.+?)(?=\n|$)"
        match = re.search(patron, texto, re.IGNORECASE)
        return match.group(1).strip() if match else ""
    
    def _buscar_total(self, texto: str) -> str:
        """Buscar total"""
        patron = r"TOTAL\s*([0-9,\.]+)"
        match = re.search(patron, texto, re.IGNORECASE)
        return match.group(1) if match else ""
    
    def extraer_repuestos(self) -> List[Dict]:
        """Extraer todos los repuestos del PDF con las correcciones"""
        texto = self._limpiar_texto(self.texto_completo)
        
        # 🔥 NUEVA ESTRATEGIA: Buscar bloques de repuestos
        # Patrón mejorado para capturar "Inspec: ... Rep: ..."
        patron_repuesto = r"Inspec:.*?Rep:\s*([^\n$]+?)(?:\s+PRECIO:\s*([0-9,\.]+))?\s*(?:-|$)"
        matches = re.finditer(patron_repuesto, texto, re.IGNORECASE)
        
        repuestos = []
        for match in matches:
            codigo_raw = match.group(1).strip()
            precio_raw = match.group(2) if match.group(2) else "0"
            
            # 🔥 CORRECCIÓN 1: Si hay múltiples códigos con '+', separarlos
            if '+' in codigo_raw:
                codigos = [c.strip() for c in codigo_raw.split('+')]
                cantidad = len(codigos)
                precio_unitario = self._calcular_precio_unitario(precio_raw, cantidad)
                
                for codigo in codigos:
                    repuesto = self._procesar_repuesto_individual(codigo, precio_unitario, match)
                    if repuesto:
                        repuestos.append(repuesto)
            else:
                # 🔥 CORRECCIÓN 2: Procesar repuesto individual
                repuesto = self._procesar_repuesto_individual(codigo_raw, precio_raw, match)
                if repuesto:
                    repuestos.append(repuesto)
        
        self.repuestos = repuestos
        self.datos['repuestos'] = repuestos
        return repuestos
    
    def _procesar_repuesto_individual(self, codigo_raw: str, precio_raw: str, match) -> Optional[Dict]:
        """Procesar un repuesto individual con todas las correcciones"""
        
        # 🔥 CORRECCIÓN 3: Formatear el código con guiones
        codigo_formateado = self._formatear_codigo(codigo_raw)
        
        # 🔥 CORRECCIÓN 4: Extraer el nombre de la pieza (si existe)
        # Buscar nombre después del código
        patron_nombre = r"(.+?)(?:\s+PRECIO:|$)"
        nombre_match = re.search(patron_nombre, codigo_raw, re.IGNORECASE)
        nombre_pieza = nombre_match.group(1).strip() if nombre_match else ""
        
        # Si el nombre está en el match original
        texto_completo = match.group(0) if match else ""
        if "NOMBRE" in texto_completo:
            patron_nombre_extra = r"NOMBRE\s*:\s*([^\n]+)"
            nombre_extra = re.search(patron_nombre_extra, texto_completo, re.IGNORECASE)
            if nombre_extra:
                nombre_pieza = nombre_extra.group(1).strip()
        
        # 🔥 CORRECCIÓN 5: Limpiar precio (quitar $ y comas)
        precio_limpio = self._limpiar_precio(precio_raw)
        
        return {
            'codigo': codigo_formateado,
            'codigo_original': codigo_raw,
            'nombre': nombre_pieza,
            'precio': precio_raw,
            'precio_num': precio_limpio,
            'precio_sin_iva': self._calcular_sin_iva(precio_limpio)
        }
    
    def _formatear_codigo(self, codigo: str) -> str:
        """Formatear el código con guiones correctamente"""
        # 🔥 CORRECCIÓN PRINCIPAL: Formato específico para códigos VW
        
        # 1. Limpiar caracteres especiales
        codigo = codigo.strip()
        codigo = re.sub(r'[^\w\-]', '', codigo)
        
        # 2. Si ya tiene guiones, devolverlo
        if '-' in codigo and not codigo.startswith('-') and not codigo.endswith('-'):
            return codigo
        
        # 3. Caso especial: códigos con terminaciones como 'NN', 'F', 'GRU'
        patron_terminacion = r'^([A-Z0-9]+)([A-Z]{2,}|GRU|F)$'
        match = re.search(patron_terminacion, codigo)
        if match:
            base = match.group(1)
            terminacion = match.group(2)
            # Formatear la base con guiones
            base_formateada = self._aplicar_guiones_base(base)
            return f"{base_formateada}-{terminacion}"
        
        # 4. Formateo estándar: agrupar en segmentos de 3 caracteres
        return self._aplicar_guiones_base(codigo)
    
    def _aplicar_guiones_base(self, codigo: str) -> str:
        """Aplicar guiones en grupos de 3 caracteres"""
        if len(codigo) <= 3:
            return codigo
        
        # Agrupar de atrás hacia adelante
        grupos = []
        for i in range(len(codigo) - 3, 0, -3):
            grupos.append(codigo[i:i+3])
        grupos.append(codigo[:len(codigo) % 3] if len(codigo) % 3 != 0 else codigo[:3])
        grupos.reverse()
        
        # Si el primer grupo no tiene 3 caracteres, ajustar
        if len(grupos[0]) < 3 and len(grupos) > 1:
            grupos[1] = grupos[0] + grupos[1]
            grupos.pop(0)
        
        return '-'.join(grupos)
    
    def _calcular_precio_unitario(self, precio_raw: str, cantidad: int) -> str:
        """Calcular el precio unitario cuando hay múltiples repuestos"""
        precio_num = self._limpiar_precio(precio_raw)
        if cantidad > 0 and precio_num > 0:
            precio_unitario = precio_num / cantidad
            # Redondear a 2 decimales
            precio_unitario = round(precio_unitario, 2)
            return str(precio_unitario)
        return precio_raw
    
    def _limpiar_precio(self, precio: str) -> float:
        """Limpiar el precio y convertirlo a float"""
        if not precio:
            return 0.0
        # Eliminar $, comas, puntos (excepto el punto decimal)
        precio = re.sub(r'[^\d,\.]', '', precio)
        # Reemplazar coma por punto (formato español)
        precio = precio.replace(',', '.')
        # Si hay más de un punto, quedarse con el último
        partes = precio.split('.')
        if len(partes) > 2:
            precio = ''.join(partes[:-1]) + '.' + partes[-1]
        try:
            return float(precio)
        except:
            return 0.0
    
    def _calcular_sin_iva(self, precio: float) -> float:
        """Calcular precio sin IVA (21%)"""
        return round(precio / 1.21, 2)
    
    def cerrar(self):
        """Cerrar el PDF"""
        if self.pdf:
            self.pdf.close()