# comparador.py - MEJORADO

import time
import re


class ComparadorRemitos:
    def __init__(self):
        self.resultado = {
            "coincidencia": 0,
            "errores": [],
            "tiempo": 0,
            "total_repuestos": 0,
            "coincidencias": 0
        }
    
    def comparar(self, datos_pdf, datos_ocr):
        inicio = time.time()
        
        errores = []
        coincidencias = 0
        
        campos = ["patente", "orden", "siniestro"]
        for campo in campos:
            valor_pdf = datos_pdf.get(campo, "").strip()
            valor_ocr = datos_ocr.get(campo, "").strip()
            
            if valor_pdf and valor_ocr:
                pdf_limpio = self._limpiar(valor_pdf)
                ocr_limpio = self._limpiar(valor_ocr)
                
                if pdf_limpio == ocr_limpio or pdf_limpio in ocr_limpio or ocr_limpio in pdf_limpio:
                    coincidencias += 1
                else:
                    errores.append({
                        "tipo": "Dato incorrecto",
                        "campo": campo.upper(),
                        "esperado": valor_pdf,
                        "encontrado": valor_ocr
                    })
            elif valor_pdf and not valor_ocr:
                errores.append({
                    "tipo": "Dato no detectado",
                    "campo": campo.upper(),
                    "esperado": valor_pdf,
                    "encontrado": "No detectado por OCR"
                })
        
        # Comparación de modelo mejorada
        modelo_pdf = datos_pdf.get("modelo", "").strip()
        modelo_ocr = datos_ocr.get("modelo", "").strip()
        if modelo_pdf and modelo_ocr:
            # Normalizar ambos modelos: solo letras, números, espacios y /
            mp = re.sub(r'[^A-Z0-9\s/]', '', modelo_pdf.upper()).strip()
            mo = re.sub(r'[^A-Z0-9\s/]', '', modelo_ocr.upper()).strip()
            # Eliminar espacios extra
            mp = re.sub(r'\s+', ' ', mp)
            mo = re.sub(r'\s+', ' ', mo)
            # Comparar versión corta del modelo (primeros 30 caracteres máximo)
            mp_corto = mp[:30]
            mo_corto = mo[:30]
            if mp == mo or mp in mo or mo in mp or mp_corto == mo_corto:
                coincidencias += 1
            else:
                errores.append({
                    "tipo": "Dato incorrecto",
                    "campo": "MODELO",
                    "esperado": modelo_pdf,
                    "encontrado": modelo_ocr
                })
        elif modelo_pdf and not modelo_ocr:
            errores.append({
                "tipo": "Dato no detectado",
                "campo": "MODELO",
                "esperado": modelo_pdf,
                "encontrado": "No detectado"
            })
        
        # Comparación de repuestos
        pdf_repuestos = {self._norm(r.get("codigo", "")): r.get("codigo", "") for r in datos_pdf.get("repuestos", [])}
        ocr_repuestos = {self._norm(r.get("codigo", "")): r.get("codigo", "") for r in datos_ocr.get("repuestos", [])}
        
        for cod_norm, cod_original_pdf in pdf_repuestos.items():
            if cod_norm in ocr_repuestos:
                coincidencias += 1
            else:
                encontrado = False
                for cod_norm_ocr in ocr_repuestos.keys():
                    if self._codes_match(cod_norm, cod_norm_ocr):
                        encontrado = True
                        coincidencias += 1
                        break
                
                if not encontrado:
                    errores.append({
                        "tipo": "Repuesto faltante",
                        "codigo": cod_original_pdf,
                        "esperado": cod_original_pdf,
                        "encontrado": "No encontrado en ADTR"
                    })
        
        total_items = len(campos) + len(pdf_repuestos)
        if total_items > 0:
            porcentaje = min((coincidencias / total_items) * 100, 100)
        else:
            porcentaje = 0
        
        self.resultado = {
            "coincidencia": round(porcentaje, 1),
            "errores": errores,
            "tiempo": round(time.time() - inicio, 2),
            "total_repuestos": len(pdf_repuestos),
            "coincidencias": coincidencias,
            "total_items": total_items
        }
        
        return self.resultado
    
    def _limpiar(self, texto):
        t = texto.upper().strip()
        t = t.lstrip(":").lstrip("-").lstrip(" ")
        t = re.sub(r'\s+', ' ', t)
        return t.strip()
    
    def _norm(self, codigo):
        return codigo.upper().replace(" ", "").replace("-", "").replace("_", "").replace(".", "")
    
    def _codes_match(self, c1, c2):
        if not c1 or not c2:
            return False
        
        def normalize(codigo):
            return codigo.upper().replace(" ", "").replace("-", "").replace("_", "").replace(".", "")
        
        norm1 = normalize(c1)
        norm2 = normalize(c2)
        
        return norm1 == norm2
    
    def obtener_resumen(self):
        return {
            "errores_encontrados": len(self.resultado["errores"]),
            "tiempo_analisis": self.resultado["tiempo"],
            "coincidencia": self.resultado["coincidencia"],
            "total_repuestos": self.resultado["total_repuestos"]
        }