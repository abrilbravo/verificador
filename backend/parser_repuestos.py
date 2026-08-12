# backend/parser_repuestos.py
# Parser robusto de repuestos a partir del texto de los reportes.
#
# Soporta bloques como:
#   Inspec: (Importado de insp. n° 2) Rep: 3C8853856F GRU -
#   Inspec: (Importado de insp. n° 1) Rep: 2H0807184A+2h0807183a-a-
#   Inspec: (Importado de insp. n° 1) Rep: 5U08536651NN -
#   Inspec: cromo (Importado de insp. n° 1) Rep: Viene
#   con la rejilla IZQ. -
#   PRECIO: 29,601.00
#   NOMBRE DE PIEZA: JGO COMPLETO DE SOPORTE
#
# Reglas:
#   - El código es lo que va después de "Rep:" (se ignora el texto anterior).
#   - Las filas pueden tener o no el campo "Inspec:" (se dividen por "Rep:").
#   - Si hay varios repuestos juntos separados por "+", el precio se divide
#     por la cantidad de repuestos y el resultado (sin IVA) se asigna a cada uno.
#   - Los sufijos separados por espacio (GRU, 9B9, 041, 1NN, ...) se conservan
#     como "-SUFIJO", aunque estén seguidos de una fecha (Fe Estimada).
#   - Se eliminan fechas (DD-MM-AAAA) que la columna "Fe Estimada" deja dentro
#     del texto de "Rep:", restos de casillas "-a-/-x-/-o-" y conectores "x".
#   - Si después de "Rep:" no hay un código, se incluye igualmente la descripción
#     con su precio y nombre de pieza.

import re

IVA = 0.21

PATRON_CODIGO = re.compile(r'[A-Z0-9]{9,}')
PATRON_CODIGO_DIGITO = re.compile(r'[0-9][A-Z0-9]{8,}')
_PATRON_CAMPO = r'(?:PRECIO|NOMBRE(?:\s+DE\s+PIEZA)?|CANT\w*|IMP\w*|TOTAL|CONFORME|Fecha\s*\S*)'


def limpiar_precio(texto):
    """Convierte un precio (string o número) a float. Soporta 29,601.00 y 12.345,67."""
    if texto is None:
        return 0.0
    t = re.sub(r'[^\d,.]', '', str(texto))
    t = t.replace(',', '.')
    partes = t.split('.')
    if len(partes) > 2:
        t = ''.join(partes[:-1]) + '.' + partes[-1]
    try:
        return float(t)
    except:
        return 0.0


def _limpiar_texto_rep(texto):
    """Limpia el contenido del campo 'Rep:':
    - quita fechas (27-07-2026, 31-08-2026, ...) que quedan dentro del texto,
    - quita el resto de casilla '-a-/-x-/-o-' del final,
    - no toca ninguna letra del codigo (la 'x' de 2H6823033DxGRU es parte del numero de pieza y se cuenta, sea mayuscula o minuscula),
    - elimina guiones finales sueltos."""
    t = str(texto)
    t = re.sub(r'\d{1,2}-\d{1,2}-\d{4}', ' ', t)
    t = re.sub(r'-[a-zox]-[\s-]*$', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\s*-\s*$', '', t)
    return t.strip()


def formatear_codigo(codigo):
    """Formatea un código de repuesto VW a 3-3-3 (y el resto en grupos de a 3
    desde el final, regla xxx-xxx-xxx-xx-xxx).
    Ej: '3C8853856F' -> '3C8-853-856-F', '5U08536651NN' -> '5U0-853-665-1NN',
        '2H6823033DXGRU' -> '2H6-823-033-DX-GRU'."""
    codigo = re.sub(r'[^A-Z0-9]', '', str(codigo).upper())
    if len(codigo) <= 3:
        return codigo
    if len(codigo) <= 9:
        return '-'.join(codigo[i:i + 3] for i in range(0, len(codigo), 3))
    base = codigo[:9]
    resto = codigo[9:]
    if len(resto) <= 3:
        return f"{base[:3]}-{base[3:6]}-{base[6:9]}-{resto}"
    inicio = len(resto) % 3
    if inicio == 0:
        grupos = [resto[i:i + 3] for i in range(0, len(resto), 3)]
    else:
        grupos = [resto[:inicio]] + [resto[i:i + 3] for i in range(inicio, len(resto), 3)]
    return f"{base[:3]}-{base[3:6]}-{base[6:9]}-{'-'.join(grupos)}"


def _extraer_sufijo(resto):
    """Busca un sufijo corto (1-4 caracteres) al inicio de 'resto',
    siempre que detrás no queden más alfanuméricos pegados."""
    m = re.match(r'[^A-Z0-9]*([A-Z0-9]{1,4})(?:[^A-Z0-9]|$)', resto)
    if not m:
        return None
    token = m.group(1)
    if re.search(r'[A-Z0-9]', resto[m.end():]):
        return None
    return token


def extraer_codigos(texto, patron=PATRON_CODIGO_DIGITO):
    """Extrae todos los códigos de repuesto presentes en un texto.
    Si después del código hay un sufijo corto separado por espacio (GRU, 9B9,
    041, 1NN, F, ...), lo agrega como ' -SUFIJO'. Devuelve lista ya formateada."""
    resultado = []
    texto = _limpiar_texto_rep(texto).upper()
    for m in re.finditer(patron, texto):
        codigo = m.group(0)
        resto = texto[m.end():]
        sufijo = _extraer_sufijo(resto)
        if sufijo:
            resultado.append(f"{formatear_codigo(codigo)} -{sufijo}")
        else:
            resultado.append(formatear_codigo(codigo))
    return resultado


def extraer_codigo(parte):
    """Extrae el primer código de repuesto de un fragmento (o None si no hay)."""
    codigos = extraer_codigos(parte)
    return codigos[0] if codigos else None


def dividir_en_bloques(texto):
    """Divide el texto en bloques que contienen 'Rep:' (con o sin 'Inspec:').
    Cada bloque arranca al inicio de la línea del marcador."""
    if not texto or not texto.strip():
        return []
    markers = [m.start() for m in re.finditer(r'(?:Inspec\s*:|Rep\s*:)(?!\w)', texto, re.IGNORECASE)]
    if not markers:
        return [texto] if texto.strip() else []
    inicios = []
    for idx in markers:
        nl = texto.rfind('\n', 0, idx)
        inicio = nl + 1
        if not inicios or inicios[-1] != inicio:
            inicios.append(inicio)
    bloques = []
    for i, inicio in enumerate(inicios):
        fin = inicios[i + 1] if i + 1 < len(inicios) else len(texto)
        bloque = texto[inicio:fin]
        if bloque.strip():
            bloques.append(bloque)
    return bloques


def _recortar_hasta_campo(contenido):
    """Recorta el contenido de 'Rep:' hasta el próximo campo conocido (PRECIO/NOMBRE/CANT...)."""
    return re.split(
        r'\s+' + _PATRON_CAMPO + r'\s*:',
        contenido,
        maxsplit=1,
        flags=re.IGNORECASE
    )[0]


def extraer_repuestos_de_contenido(contenido, precio=0.0, nombre=""):
    """Convierte el contenido que va después de 'Rep:' en repuestos.
    Si hay varios códigos con '+', divide el precio por la cantidad."""
    contenido = _limpiar_texto_rep(contenido)
    partes = [p for p in contenido.split('+') if p.strip()]
    if not partes:
        return []

    cantidad_partes = len(partes)
    precio_unitario = round(precio / cantidad_partes, 2) if cantidad_partes > 0 and precio else precio

    repuestos = []
    for parte in partes:
        codigo = extraer_codigo(parte)
        if codigo:
            codigo_rep = codigo
            descripcion = nombre
        else:
            codigo_rep = re.sub(r'\s+', ' ', parte.strip()).upper()
            descripcion = re.sub(r'\s+', ' ', parte.strip()) if not nombre else nombre

        repuestos.append({
            'codigo': codigo_rep,
            'descripcion': descripcion,
            'nombre': nombre,
            'cantidad': '1.00',
            'precio': str(precio_unitario),
            'precio_num': precio_unitario,
            'precio_sin_iva': round(precio_unitario / (1 + IVA), 2)
        })
    return repuestos


def parsear_bloque(bloque):
    """Parsea un bloque 'Inspec: ... Rep: ...' y devuelve sus repuestos."""
    m_rep = re.search(r'Rep\s*:\s*(.*)', bloque, re.IGNORECASE | re.DOTALL)
    if not m_rep:
        return []

    contenido = m_rep.group(1)
    contenido = _recortar_hasta_campo(contenido).strip()

    precio = _extraer_precio_bloque(bloque)

    nombre = ""
    m_nombre = re.search(
        r'NOMBRE(?:\s+DE\s+PIEZA)?\s*:\s*(.*?)(?=\s+(?:PRECIO|CANT\w*|IMP\w*)\s*:|\s*$)',
        bloque,
        re.IGNORECASE | re.DOTALL
    )
    if m_nombre:
        nombre = m_nombre.group(1).strip()

    return extraer_repuestos_de_contenido(contenido, precio, nombre)


def _extraer_precio_bloque(bloque):
    """Obtiene el precio del bloque. Si hay etiqueta 'PRECIO:', la usa.
    Si no, toma el último número con formato de precio (xx.xx) que aparece en la
    fila antes de 'Inspec:'/'Rep:' (es el 'Precio Or.')."""
    m_precio = re.search(r'PRECIO\s*:\s*([0-9.,]+)', bloque, re.IGNORECASE)
    if m_precio:
        return limpiar_precio(m_precio.group(1))

    anterior = re.split(r'(?:Inspec\s*:|Rep\s*:)', bloque, maxsplit=1, flags=re.IGNORECASE)[0]
    if anterior:
        numeros = re.findall(r'\d[\d.,]*\d', anterior)
        precios = [n for n in numeros if re.search(r'[.,]\d{2}$', n)]
        if precios:
            return limpiar_precio(precios[-1])
    return 0.0


def parsear_repuestos(texto):
    """Parsea todo el texto del reporte y devuelve la lista de repuestos (sin duplicados)."""
    repuestos = []
    vistos = set()
    for bloque in dividir_en_bloques(texto):
        for repuesto in parsear_bloque(bloque):
            clave = re.sub(r'[^A-Z0-9]', '', repuesto['codigo'].upper())
            if clave and clave not in vistos:
                vistos.add(clave)
                repuestos.append(repuesto)
    return repuestos
