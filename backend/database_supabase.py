# backend/database_supabase.py
import os
import psycopg2
import json
from datetime import datetime

class Database:
    def __init__(self):
        # Usar DATABASE_URL desde variables de entorno
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            # Fallback para desarrollo local (si quieres)
            database_url = "postgresql://app_user:abril2008%40kawaii@db.livkbbxiopwlzninzlmb.supabase.co:5432/postgres"
        
        self.conn = psycopg2.connect(database_url)
        self.cursor = self.conn.cursor()
        self._crear_tablas()
    
    def _crear_tablas(self):
        """Crear tabla si no existe (por si acaso)"""
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS historial (
                    id SERIAL PRIMARY KEY,
                    fecha TEXT NOT NULL,
                    hora TEXT NOT NULL,
                    usuario TEXT NOT NULL,
                    cliente TEXT NOT NULL,
                    remito TEXT,
                    orden TEXT,
                    siniestro TEXT,
                    patente TEXT,
                    modelo TEXT,
                    estado TEXT NOT NULL,
                    errores INTEGER DEFAULT 0,
                    coincidencia REAL DEFAULT 0,
                    tiempo REAL DEFAULT 0,
                    detalles TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            self.conn.commit()
        except Exception as e:
            print(f"Error creando tabla: {e}")
    
    def guardar_verificacion(self, datos):
        """Guardar una verificación en la base de datos"""
        try:
            detalles = datos.get('detalles', {})
            if isinstance(detalles, dict):
                detalles = json.dumps(detalles, ensure_ascii=False)
            
            query = """
                INSERT INTO historial 
                (fecha, hora, usuario, cliente, remito, orden, siniestro, 
                 patente, modelo, estado, errores, coincidencia, tiempo, detalles)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """
            
            valores = (
                datos.get('fecha', datetime.now().strftime('%d/%m/%Y')),
                datos.get('hora', datetime.now().strftime('%H:%M')),
                datos.get('usuario', 'Sistema'),
                datos.get('cliente', 'Sin cliente'),
                datos.get('remito', ''),
                datos.get('orden', ''),
                datos.get('siniestro', ''),
                datos.get('patente', ''),
                datos.get('modelo', ''),
                datos.get('estado', 'Correcto'),
                datos.get('errores', 0),
                datos.get('coincidencia', 0),
                datos.get('tiempo', 0),
                detalles
            )
            
            self.cursor.execute(query, valores)
            self.conn.commit()
            id_guardado = self.cursor.fetchone()[0]
            return id_guardado
            
        except Exception as e:
            print(f"Error guardando verificación: {e}")
            self.conn.rollback()
            return None
    
    def obtener_historial(self, limite=100):
        """Obtener historial de verificaciones"""
        try:
            query = """
                SELECT id, fecha, hora, usuario, cliente, remito, orden, 
                       siniestro, patente, modelo, estado, errores, 
                       coincidencia, tiempo
                FROM historial
                ORDER BY created_at DESC
                LIMIT %s
            """
            self.cursor.execute(query, (limite,))
            resultados = self.cursor.fetchall()
            
            historial = []
            for row in resultados:
                historial.append({
                    'id': row[0],
                    'fecha': row[1],
                    'hora': row[2],
                    'usuario': row[3],
                    'cliente': row[4],
                    'remito': row[5],
                    'orden': row[6],
                    'siniestro': row[7],
                    'patente': row[8],
                    'modelo': row[9],
                    'estado': row[10],
                    'errores': row[11],
                    'coincidencia': row[12],
                    'tiempo': row[13]
                })
            return historial
            
        except Exception as e:
            print(f"Error obteniendo historial: {e}")
            return []
    
    def obtener_estadisticas(self):
        """Obtener estadísticas de las verificaciones"""
        try:
            stats = {}
            
            self.cursor.execute("SELECT COUNT(*) FROM historial")
            stats['total'] = self.cursor.fetchone()[0]
            
            self.cursor.execute(
                "SELECT COUNT(*) FROM historial WHERE estado = 'Con errores'"
            )
            stats['con_errores'] = self.cursor.fetchone()[0]
            
            self.cursor.execute(
                "SELECT COUNT(*) FROM historial WHERE estado = 'Correcto'"
            )
            stats['correctas'] = self.cursor.fetchone()[0]
            
            self.cursor.execute(
                "SELECT AVG(coincidencia) FROM historial WHERE coincidencia > 0"
            )
            avg = self.cursor.fetchone()[0]
            stats['promedio_coincidencia'] = round(avg, 2) if avg else 0
            
            self.cursor.execute("""
                SELECT cliente, COUNT(*) as total 
                FROM historial 
                GROUP BY cliente 
                ORDER BY total DESC 
                LIMIT 5
            """)
            stats['top_clientes'] = self.cursor.fetchall()
            
            return stats
            
        except Exception as e:
            print(f"Error obteniendo estadísticas: {e}")
            return {
                'total': 0,
                'con_errores': 0,
                'correctas': 0,
                'promedio_coincidencia': 0,
                'top_clientes': []
            }
    
    def cerrar(self):
        try:
            self.cursor.close()
            self.conn.close()
        except:
            pass