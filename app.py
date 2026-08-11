from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import json
from datetime import datetime
import shutil

from backend.pdf import LectorPDF
from backend.ocr import LectorOCR
from backend.comparador import ComparadorRemitos
from backend.database import Database
from backend.util_funciones import formatear_siniestro, obtener_usuario, limpiar_precio, sacar_iva, formatear_precio

app = Flask(__name__)
app.secret_key = 'vw-verificador-secret-key-2024'
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
STATIC_ASSETS = os.path.join(BASE_DIR, 'static', 'assets')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')

os.makedirs(STATIC_ASSETS, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

if os.path.exists(ASSETS_DIR) and not os.listdir(STATIC_ASSETS):
    shutil.copytree(ASSETS_DIR, STATIC_ASSETS, dirs_exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

db = Database()

@app.route('/assets/<path:filename>')
def serve_asset(filename):
    return send_from_directory(STATIC_ASSETS, filename)

@app.route('/')
def index():
    return render_template('index.html', 
                         usuario=obtener_usuario(),
                         app_name="Verificador Inteligente de Remitos",
                         version="3.0.0")

@app.route('/verificar')
def verificar():
    return render_template('verificar.html', usuario=obtener_usuario())

@app.route('/historial')
def historial():
    return render_template('historial.html', usuario=obtener_usuario())

@app.route('/estadisticas')
def estadisticas():
    return render_template('estadisticas.html', usuario=obtener_usuario())

@app.route('/api/cargar_pdf', methods=['POST'])
def cargar_pdf():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No se envió archivo'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Archivo vacío'}), 400
        
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(temp_path)
        
        lector = LectorPDF()
        lector.abrir(temp_path)
        datos = lector.extraer_datos()
        lector.extraer_repuestos()
        
        os.remove(temp_path)
        
        if datos.get('siniestro'):
            datos['siniestro'] = formatear_siniestro(datos['siniestro'])
        
        for repuesto in datos.get('repuestos', []):
            try:
                precio = repuesto.get('precio', '0')
                if isinstance(precio, str):
                    precio = precio.replace('$', '').replace(',', '.').replace(' ', '')
                repuesto['precio_num'] = float(precio) if precio else 0
                repuesto['precio_sin_iva'] = sacar_iva(repuesto['precio_num'])
            except:
                repuesto['precio_num'] = 0
                repuesto['precio_sin_iva'] = 0
        
        return jsonify({
            'success': True,
            'datos': datos,
            'repuestos': datos.get('repuestos', [])
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/cargar_imagen', methods=['POST'])
def cargar_imagen():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No se envió archivo'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Archivo vacío'}), 400
        
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(temp_path)
        
        lector = LectorOCR()
        lector.abrir_imagen(temp_path)
        datos = lector.extraer_datos()
        
        os.remove(temp_path)
        
        return jsonify({
            'success': True,
            'datos': datos,
            'repuestos': datos.get('repuestos', [])
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/verificar', methods=['POST'])
def api_verificar():
    try:
        data = request.json
        datos_pdf = data.get('datos_pdf', {})
        datos_ocr = data.get('datos_ocr', {})
        repuestos_ocr = data.get('repuestos_ocr', [])
        
        datos_ocr_completos = dict(datos_ocr)
        datos_ocr_completos['repuestos'] = repuestos_ocr
        
        comparador = ComparadorRemitos()
        resultado = comparador.comparar(datos_pdf, datos_ocr_completos)
        
        reporte = generar_reporte_detalle(datos_pdf, datos_ocr_completos, resultado)
        
        return jsonify({
            'success': True,
            'resultado': resultado,
            'reporte': reporte
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/guardar', methods=['POST'])
def guardar_verificacion():
    try:
        data = request.json
        usuario = data.get('usuario', 'Sistema')
        datos_pdf = data.get('datos_pdf', {})
        resultado = data.get('resultado', {})
        
        errores = len(resultado.get('errores', []))
        
        datos_guardar = {
            'fecha': datetime.now().strftime('%d/%m/%Y'),
            'hora': datetime.now().strftime('%H:%M'),
            'usuario': usuario,
            'cliente': datos_pdf.get('cliente', 'Sin cliente'),
            'remito': data.get('remito', ''),
            'orden': datos_pdf.get('orden', ''),
            'siniestro': datos_pdf.get('siniestro', ''),
            'patente': datos_pdf.get('patente', ''),
            'modelo': datos_pdf.get('modelo', ''),
            'estado': 'Correcto' if errores == 0 else 'Con errores',
            'errores': errores,
            'coincidencia': resultado.get('coincidencia', 0),
            'tiempo': resultado.get('tiempo', 0),
            'detalles': resultado
        }
        
        id_guardado = db.guardar_verificacion(datos_guardar)
        
        return jsonify({
            'success': True,
            'id': id_guardado,
            'mensaje': 'Verificación guardada correctamente'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/historial', methods=['GET'])
def obtener_historial():
    try:
        limite = request.args.get('limite', 100, type=int)
        historial = db.obtener_historial(limite)
        return jsonify({
            'success': True,
            'historial': historial
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/estadisticas', methods=['GET'])
def obtener_estadisticas():
    try:
        stats = db.obtener_estadisticas()
        return jsonify({
            'success': True,
            'estadisticas': stats
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def generar_reporte_detalle(datos_pdf, datos_ocr, resultado):
    reporte = {
        'problemas': [],
        'resumen': '',
        'total_errores': len(resultado.get('errores', []))
    }
    
    campos = ['patente', 'orden', 'siniestro', 'modelo']
    comparador = ComparadorRemitos()
    
    for campo in campos:
        val_pdf = datos_pdf.get(campo, '').strip()
        val_ocr = datos_ocr.get(campo, '').strip()
        
        if val_pdf and val_ocr:
            pdf_limpio = comparador._limpiar(val_pdf)
            ocr_limpio = comparador._limpiar(val_ocr)
            
            if pdf_limpio == ocr_limpio or pdf_limpio in ocr_limpio or ocr_limpio in pdf_limpio:
                reporte['problemas'].append({
                    'tipo': 'OK',
                    'campo': campo.upper(),
                    'pdf': val_pdf,
                    'ocr': val_ocr
                })
            else:
                reporte['problemas'].append({
                    'tipo': 'DIFERENTE',
                    'campo': campo.upper(),
                    'pdf': val_pdf,
                    'ocr': val_ocr
                })
        elif val_pdf and not val_ocr:
            reporte['problemas'].append({
                'tipo': 'NO DETECTADO',
                'campo': campo.upper(),
                'pdf': val_pdf,
                'ocr': 'No detectado'
            })
    
    pdf_repuestos = {r.get('codigo', '').upper().replace('-', '').replace(' ', ''): r 
                     for r in datos_pdf.get('repuestos', [])}
    ocr_repuestos = {r.get('codigo', '').upper().replace('-', '').replace(' ', ''): r 
                     for r in datos_ocr.get('repuestos', [])}
    
    for cod_pdf, rep_pdf in pdf_repuestos.items():
        if cod_pdf in ocr_repuestos:
            reporte['problemas'].append({
                'tipo': 'OK',
                'campo': 'REPUESTO',
                'pdf': rep_pdf.get('codigo', cod_pdf),
                'ocr': ocr_repuestos[cod_pdf].get('codigo', cod_pdf)
            })
        else:
            encontrado = False
            for cod_ocr in ocr_repuestos:
                if comparador._codes_match(cod_pdf, cod_ocr):
                    encontrado = True
                    reporte['problemas'].append({
                        'tipo': 'OK',
                        'campo': 'REPUESTO',
                        'pdf': rep_pdf.get('codigo', cod_pdf),
                        'ocr': ocr_repuestos[cod_ocr].get('codigo', cod_ocr)
                    })
                    break
            if not encontrado:
                reporte['problemas'].append({
                    'tipo': 'FALTA',
                    'campo': 'REPUESTO',
                    'pdf': rep_pdf.get('codigo', cod_pdf),
                    'ocr': 'No encontrado'
                })
    
    problemas_lista = [p for p in reporte['problemas'] if p['tipo'] not in ['OK']]
    if not problemas_lista:
        reporte['resumen'] = '✅ TODO OK - No se encontraron diferencias.'
    else:
        reporte['resumen'] = f'⚠️ Se encontraron {len(problemas_lista)} problema(s)'
    
    return reporte

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)