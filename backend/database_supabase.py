# backend/database_supabase.py
import os
import psycopg2
import json
from datetime import datetime

# La URL de la base se toma de la variable de entorno DATABASE_URL
# (configurada en Render / en la máquina local). NUNCA escribir la
# contraseña en el código.
DATABASE_URL = os.environ.get("DATABASE_URL", "")


class Database:
    def __init__(self):
        self._conn = None
        self._cursor = None
        self._error = None

    def conectar(self):
        if self._conn is not None:
            return True
        try:
            self._conn = psycopg2.connect(DATABASE_URL, connect_timeout=5)
            self._conn.autocommit = False
            self._cursor = self._conn.cursor()
            self._crear_tablas()
            self._conn.rollback()
            self._error = None
            return True
        except Exception as e:
            print(f"[Database] No se pudo conectar a la base: {e}")
            self._error = str(e)
            self._conn = None
            self._cursor = None
            return False

    def _crear_tablas(self):
        try:
            self._cursor.execute("""
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
            self._conn.commit()
        except Exception as e:
            print(f"Error creando tabla: {e}")
            self._conn.rollback()

    def guardar_verificacion(self, datos):
        if not self.conectar():
            return None
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
            self._cursor.execute(query, valores)
            self._conn.commit()
            return self._cursor.fetchone()[0]
        except Exception as e:
            print(f"Error guardando verificación: {e}")
            self._conn.rollback()
            return None

    def obtener_historial(self, limite=100):
        if not self.conectar():
            return []
        try:
            self._cursor.execute("""
                SELECT id, fecha, hora, usuario, cliente, remito, orden,
                       siniestro, patente, modelo, estado, errores,
                       coincidencia, tiempo
                FROM historial
                ORDER BY created_at DESC
                LIMIT %s
            """, (limite,))
            historial = []
            for row in self._cursor.fetchall():
                historial.append({
                    'id': row[0], 'fecha': row[1], 'hora': row[2],
                    'usuario': row[3], 'cliente': row[4], 'remito': row[5],
                    'orden': row[6], 'siniestro': row[7], 'patente': row[8],
                    'modelo': row[9], 'estado': row[10], 'errores': row[11],
                    'coincidencia': row[12], 'tiempo': row[13]
                })
            return historial
        except Exception as e:
            print(f"Error obteniendo historial: {e}")
            return []

    def obtener_estadisticas(self):
        vacio = {'total': 0, 'con_errores': 0, 'correctas': 0, 'promedio_coincidencia': 0, 'top_clientes': []}
        if not self.conectar():
            return vacio
        try:
            self._cursor.execute("SELECT COUNT(*) FROM historial")
            total = self._cursor.fetchone()[0]
            self._cursor.execute("SELECT COUNT(*) FROM historial WHERE estado = 'Con errores'")
            con_errores = self._cursor.fetchone()[0]
            self._cursor.execute("SELECT COUNT(*) FROM historial WHERE estado = 'Correcto'")
            correctas = self._cursor.fetchone()[0]
            self._cursor.execute("SELECT AVG(coincidencia) FROM historial WHERE coincidencia > 0")
            avg = self._cursor.fetchone()[0]
            return {
                'total': total, 'con_errores': con_errores, 'correctas': correctas,
                'promedio_coincidencia': round(avg, 2) if avg else 0, 'top_clientes': []
            }
        except Exception as e:
            print(f"Error obteniendo estadísticas: {e}")
            return vacio

    def cerrar(self):
        try:
            if self._cursor:
                self._cursor.close()
            if self._conn:
                self._conn.close()
        except:
            pass
        self._conn = None
        self._cursor = None