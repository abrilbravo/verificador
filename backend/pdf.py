# backend/pdf.py - VERSIÓN CORREGIDA

import pdfplumber
import re
from typing import Dict, List
try:
    from .parser_repuestos import parsear_repuestos
except ImportError:
    from parser_repuestos import parsear_repuestos

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
            'modelo': self._buscar_modelo(self.texto_completo),  # usar texto raw con saltos de línea
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
        """Buscar número de siniestro (soporta 'SINIESTRO:', 'Nº Siniestro', etc.)"""
        patrones = [
            r"SINIESTRO\s*:?\s*N[º°]?\.?\s*:?\s*([0-9][0-9\-]*)",
            r"SINIESTRO\s*:?\s*([0-9][0-9\-]*)",
            r"N[º°]?\.?\s*(?:DE\s+)?SINIESTRO\s*:?\s*([0-9][0-9\-]*)",
            r"SINISTRO\s*:?\s*([0-9][0-9\-]*)",
        ]
        for patron in patrones:
            match = re.search(patron, texto, re.IGNORECASE)
            if match:
                return match.group(1).strip('-')
        match = re.search(r'\b[0-9]{3}-[0-9]-[0-9]{6}\b', texto)
        if match:
            return match.group(0)
        return ""

    def _buscar_patente(self, texto: str) -> str:
        """Buscar patente (formato ABC123DE, ABC123, o con guiones)."""
        patrones = [
            r"PATENTE\s*:?\s*([A-Z]{2}[0-9]{3}[A-Z]{2})",
            r"PATENTE\s*:?\s*([A-Z]{3}[0-9]{3})",
            r"PATENTE\s*:?\s*([A-Z0-9]{5,7})",
        ]
        for patron in patrones:
            match = re.search(patron, texto, re.IGNORECASE)
            if match:
                return match.group(1)
        return ""
    
    def _buscar_modelo(self, texto: str) -> str:
        """Buscar modelo del vehículo.
        Usa el texto con saltos de línea para cortar exactamente al final de la línea
        donde está MODELO, antes de CHASIS u otro campo."""
        patron = r"MODELO\s*:?\s*(.+?)(?=\s*\n|\s+CHASIS\b|$)"
        match = re.search(patron, texto, re.IGNORECASE)
        if not match:
            return ""
        modelo = re.sub(r'^[:\s]+', '', match.group(1)).strip()
        return modelo
    
    def _buscar_total(self, texto: str) -> str:
        """Buscar total"""
        patron = r"TOTAL\s*([0-9,\.]+)"
        match = re.search(patron, texto, re.IGNORECASE)
        return match.group(1) if match else ""
    
    def extraer_repuestos(self) -> List[Dict]:
        """Extraer todos los repuestos del PDF (bloques 'Inspec: ... Rep: ...')"""
        repuestos = parsear_repuestos(self.texto_completo)
        self.repuestos = repuestos
        self.datos['repuestos'] = repuestos
        return repuestos
    
    def cerrar(self):
        """Cerrar el PDF"""
        if self.pdf:
            self.pdf.close()