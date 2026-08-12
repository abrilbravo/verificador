# util_funciones.py

import os
import getpass
from datetime import datetime


def formatear_siniestro(siniestro):
    """
    Convierte un siniestro al formato que usa ADTR.
    Ejemplo: "1034416499" -> "103-4-416499"
    """
    if not siniestro:
        return ""
    
    # Si ya tiene guiones, devolverlo igual
    if "-" in siniestro:
        return siniestro
    
    # Limpiar el número (quitar espacios, etc)
    siniestro = siniestro.strip()
    
    # Si es un número de 10 dígitos
    if len(siniestro) == 10 and siniestro.isdigit():
        return f"{siniestro[:3]}-{siniestro[3:4]}-{siniestro[4:]}"
    
    return siniestro


def sacar_iva(precio):
    """Saca el IVA de un precio (21%). Si es $1 o menos (precio de referencia),
    no se le saca el IVA."""
    try:
        if isinstance(precio, str):
            precio = precio.replace('.', '').replace(',', '.')
        precio = float(precio)
        if precio <= 1:
            return round(precio, 2)
        return round(precio / 1.21, 2)
    except:
        return 0.0


def copiar_portapapeles(texto):
    """Copiar texto al portapapeles"""
    try:
        # En Windows
        import subprocess
        subprocess.run(['clip'], input=texto.encode('utf-8'), check=True)
        return True
    except:
        try:
            # Alternativa usando tkinter
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            root.clipboard_clear()
            root.clipboard_append(texto)
            root.destroy()
            return True
        except:
            return False


def obtener_usuario():
    """Obtener nombre de usuario del sistema"""
    try:
        return getpass.getuser()
    except:
        return "Usuario"


def obtener_fecha_hora():
    """Obtener fecha y hora actual formateada"""
    ahora = datetime.now()
    return {
        "fecha": ahora.strftime("%d/%m/%Y"),
        "hora": ahora.strftime("%H:%M"),
        "timestamp": ahora.strftime("%Y-%m-%d %H:%M:%S")
    }


def limpiar_precio(precio_str):
    """Limpiar un string de precio para convertirlo a número"""
    if not precio_str:
        return 0.0
    
    precio_str = precio_str.replace('$', '').replace(' ', '')
    
    if not precio_str or precio_str == "0":
        return 0.0
    
    if ',' in precio_str and '.' in precio_str:
        if precio_str.rindex(',') > precio_str.rindex('.'):
            precio_str = precio_str.replace('.', '').replace(',', '.')
        else:
            precio_str = precio_str.replace(',', '')
    elif ',' in precio_str:
        precio_str = precio_str.replace(',', '.')
    
    try:
        return float(precio_str)
    except:
        return 0.0


def formatear_precio(precio):
    try:
        return f"${precio:,.2f}"
    except:
        return "$0.00"