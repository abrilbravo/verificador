# database.py

import sqlite3
from datetime import datetime
import json


class Database:
    def __init__(self, nombre_db="historial.db"):
        self.nombre_db = nombre_db
        self.crear_tablas()
    
    def crear_tablas(self):
        """Crear tablas si no existen"""
        with sqlite3.connect(self.nombre_db) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS verificaciones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha TEXT NOT NULL,
                    hora TEXT NOT NULL,
                    usuario TEXT NOT NULL,
                    cliente TEXT NOT NULL,
                    remito TEXT NOT NULL,
                    orden TEXT NOT NULL,
                    siniestro TEXT NOT NULL,
                    patente TEXT NOT NULL,
                    modelo TEXT NOT NULL,
                    estado TEXT NOT NULL,
                    errores INTEGER DEFAULT 0,
                    coincidencia REAL DEFAULT 0,
                    tiempo REAL DEFAULT 0,
                    detalles TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()

    def guardar_verificacion(self, datos):
        """Guardar una verificación en el historial"""
        try:
            with sqlite3.connect(self.nombre_db) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO verificaciones (
                        fecha, hora, usuario, cliente, remito, orden, 
                        siniestro, patente, modelo, estado, errores,
                        coincidencia, tiempo, detalles
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    datos.get("fecha", datetime.now().strftime("%d/%m/%Y")),
                    datos.get("hora", datetime.now().strftime("%H:%M")),
                    datos.get("usuario", "Sistema"),
                    datos.get("cliente", ""),
                    datos.get("remito", ""),
                    datos.get("orden", ""),
                    datos.get("siniestro", ""),
                    datos.get("patente", ""),
                    datos.get("modelo", ""),
                    datos.get("estado", "Pendiente"),
                    datos.get("errores", 0),
                    datos.get("coincidencia", 0),
                    datos.get("tiempo", 0),
                    json.dumps(datos.get("detalles", {}))
                ))
                
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"Error al guardar verificación: {e}")
            return None

    def obtener_historial(self, limite=100):
        """Obtener historial de verificaciones"""
        try:
            with sqlite3.connect(self.nombre_db) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, fecha, hora, usuario, cliente, remito, 
                           orden, siniestro, estado, errores, coincidencia, tiempo
                    FROM verificaciones
                    ORDER BY created_at DESC
                    LIMIT ?
                ''', (limite,))
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error al obtener historial: {e}")
            return []

    def obtener_estadisticas(self):
        """Obtener estadísticas generales"""
        try:
            with sqlite3.connect(self.nombre_db) as conn:
                cursor = conn.cursor()
                
                # Total de verificaciones
                cursor.execute("SELECT COUNT(*) FROM verificaciones")
                total = cursor.fetchone()[0]
                
                # Correctos vs errores
                cursor.execute("SELECT COUNT(*) FROM verificaciones WHERE estado = 'Correcto'")
                correctos = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM verificaciones WHERE estado = 'Con errores'")
                con_errores = cursor.fetchone()[0]
                
                # Promedio de tiempo
                cursor.execute("SELECT AVG(tiempo) FROM verificaciones")
                tiempo_promedio = cursor.fetchone()[0] or 0
                
                # Errores más frecuentes (de los detalles JSON)
                # Esto es más complejo, lo dejamos para después
                
                return {
                    "total": total,
                    "correctos": correctos,
                    "con_errores": con_errores,
                    "tiempo_promedio": round(tiempo_promedio, 2),
                    "tasa_exito": round((correctos / total * 100) if total > 0 else 0, 1)
                }
        except Exception as e:
            print(f"Error al obtener estadísticas: {e}")
            return {}