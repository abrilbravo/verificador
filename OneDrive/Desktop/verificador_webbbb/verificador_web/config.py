# config.py
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

APP_NAME = "Verificador Inteligente de Remitos"
APP_VERSION = "3.0.0"
APP_ICON = os.path.join(BASE_DIR, "assets", "vw_logo.ico")
APP_LOGO = os.path.join(BASE_DIR, "assets", "vw_logo.png")

FONT_DIR = os.path.join(BASE_DIR, "assets")

FONT_VW_TEXT = os.path.join(FONT_DIR, "VWTextRegular.otf")
FONT_VW_TEXT_BOLD = os.path.join(FONT_DIR, "VWTextBold.otf")
FONT_VW_HEAD = os.path.join(FONT_DIR, "VWHeadRegular.otf")
FONT_VW_HEAD_BOLD = os.path.join(FONT_DIR, "VWHeadBold.otf")

COLORES = {
    "fondo": "#F5F7FA",
    "menu": "#1A1A2E",
    "menu_hover": "#16213E",
    "menu_seleccionado": "#2D3A6B",
    "azul": "#2F80ED",
    "azul_hover": "#1A6BC4",
    "verde": "#27AE60",
    "rojo": "#E74C3C",
    "naranja": "#F39C12",
    "texto": "#2C3E50",
    "texto_secundario": "#7F8C8D",
    "borde": "#D5D8DC",
}

PDF_CONFIG = {
    "cliente_buscar": "Federación Patronal Seguros S.A.",
    "orden_buscar": r"N[º°]?\.?\s*Orden:\s*([0-9]+)",
    "siniestro_buscar": r"SINIESTRO\s*([0-9\-]+)",
    "patente_buscar": r"PATENTE\s*([A-Z0-9]+)",
    "modelo_buscar": r"MODELO\s*(.+?)(?=\n|$)",
    "total_buscar": r"TOTAL\s*([0-9,\.]+)"
}

IVA = 0.21
DB_NAME = "historial.db"