# backend/database_supabase.py
import os
import psycopg2
import json
from datetime import datetime

# Conexión a Supabase usando el pooler (puerto 6543, aws-0-sa-east-1.pooler.supabase.com).
# El host directo db.<ref>.supabase.co (puerto 5432) NO funciona desde Render (red inalcanzable).
# No se usa la variable DATABASE_URL de Render porque en el deploy apuntaba al host directo
# y tiraba "Network is unreachable"; acá se fuerza el pooler que ya está verificado.
DATABASE_URL = "postgresql://app_user.livkbbxiopwlzninzlmb:abril2008kawaii@aws-0-sa-east-1.pooler.supabase.com:6543/postgres?sslmode=require"


class Database:
    def __init__(self):
        self._conn = None
        self._cursor = None
        self._error = None

    def conectar(self):
        """Conecta de forma diferida. Devuelve True si hay conexión activa."""
        if self._conn is not None:
            return True

        database_url = DATABASE_URL
        try:
            self._conn = psycopg2.connect(database_url, connect_timeout=5)
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
        """Crear tabla si no existe (por si acaso). Si el rol no tiene permiso
        para crear (Supabase pooler), solo informa y sigue."""
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
            print(f"Error creando tabla (puede no tener permiso): {e}")
            self._conn.rollback()

    def guardar_verificacion(self, datos):
        """Guardar una verificación en la base de datos"""
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
            id_guardado = self._cursor.fetchone()[0]
            return id_guardado

        except Exception as e:
            print(f"Error guardando verificación: {e}")
            self._conn.rollback()
            return None

    def obtener_historial(self, limite=100):
        """Obtener historial de verificaciones"""
        if not self.conectar():
            return []
        try:
            query = """
                SELECT id, fecha, hora, usuario, cliente, remito, orden,
                       siniestro, patente, modelo, estado, errores,
                       coincidencia, tiempo
                FROM historial
                ORDER BY created_at DESC
                LIMIT %s
            """
            self._cursor.execute(query, (limite,))
            resultados = self._cursor.fetchall()

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
        vacio = {
            'total': 0,
            'con_errores': 0,
            'correctas': 0,
            'promedio_coincidencia': 0,
            'top_clientes': []
        }
        if not self.conectar():
            return vacio

        try:
            stats = {}

            self._cursor.execute("SELECT COUNT(*) FROM historial")
            stats['total'] = self._cursor.fetchone()[0]

            self._cursor.execute(
                "SELECT COUNT(*) FROM historial WHERE estado = 'Con errores'"
            )
            stats['con_errores'] = self._cursor.fetchone()[0]

            self._cursor.execute(
                "SELECT COUNT(*) FROM historial WHERE estado = 'Correcto'"
            )
            stats['correctas'] = self._cursor.fetchone()[0]

            self._cursor.execute(
                "SELECT AVG(coincidencia) FROM historial WHERE coincidencia > 0"
            )
            avg = self._cursor.fetchone()[0]
            stats['promedio_coincidencia'] = round(avg, 2) if avg else 0

            self._cursor.execute("""
                SELECT cliente, COUNT(*) as total
                FROM historial
                GROUP BY cliente
                ORDER BY total DESC
                LIMIT 5
            """)
            stats['top_clientes'] = self._cursor.fetchall()

            return stats

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
