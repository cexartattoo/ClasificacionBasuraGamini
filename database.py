# -*- coding: utf-8 -*-
"""
Módulo de Base de Datos (database.py)

Este módulo se encarga de toda la interacción con la base de datos SQLite.
Proporciona funciones para inicializar la base de datos, crear la tabla de
historial, añadir nuevos registros de clasificación y obtener el historial
para mostrarlo en la interfaz web.

La base de datos se almacena en un archivo local llamado 'historial.db'.
"""
import sqlite3
import json
from datetime import datetime

# Nombre del archivo de la base de datos
DATABASE_NAME = 'historial.db'


def _column_exists(cursor, table_name, column_name):
    """Verifica si una columna ya existe en una tabla."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [info[1] for info in cursor.fetchall()]
    return column_name in columns


def init_db():
    """
    Inicializa la base de datos.

    - Crea la tabla 'historial' si no existe.
    - Añade la columna 'respuesta_hablada' si no existe, para no perder datos.
    """
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()

        # Crear la tabla principal si no existe
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS historial (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT NOT NULL,
                material TEXT,
                objetos_detectados TEXT,
                confianza REAL,
                estado_envio TEXT NOT NULL
            )
        ''')

        # --- MODIFICACIÓN: Añadir nueva columna sin borrar la tabla ---
        # Se comprueba si la columna ya existe para evitar errores en ejecuciones futuras.
        if not _column_exists(cursor, 'historial', 'respuesta_hablada'):
            print("Añadiendo columna 'respuesta_hablada' a la base de datos...")
            cursor.execute('ALTER TABLE historial ADD COLUMN respuesta_hablada TEXT')

        conn.commit()
        print("Base de datos inicializada y verificada correctamente.")
    except sqlite3.Error as e:
        print(f"Error al inicializar la base de datos: {e}")
    finally:
        if conn:
            conn.close()


def add_record(material, objetos, confianza, estado_envio, respuesta_hablada=""):
    """
    Añade un nuevo registro de clasificación a la tabla 'historial'.

    Args:
        material (str): El material clasificado ('plástico', 'orgánico', 'metal', 'null').
        objetos (list): Una lista de diccionarios con los objetos detectados.
        confianza (float): El nivel de confianza del objeto principal (0.0 a 1.0).
        estado_envio (str): El estado del envío al Arduino ('PENDIENTE', 'ENVIADO', 'ERROR_ARDUINO', etc.).
        respuesta_hablada (str): El texto que el asistente debe decir.

    Returns:
        int: El ID del registro recién insertado, o None si ocurrió un error.
    """
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()

        fecha_actual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Convertimos la lista de objetos a una cadena JSON para poder almacenarla.
        objetos_json = json.dumps(objetos)

        cursor.execute('''
            INSERT INTO historial (fecha, material, objetos_detectados, confianza, estado_envio, respuesta_hablada)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (fecha_actual, material, objetos_json, confianza, estado_envio, respuesta_hablada))

        conn.commit()
        last_id = cursor.lastrowid
        print(f"Registro añadido a la base de datos con ID: {last_id}")
        return last_id
    except sqlite3.Error as e:
        print(f"Error al añadir registro a la base de datos: {e}")
        return None
    finally:
        if conn:
            conn.close()


def update_record_status(record_id, nuevo_estado):
    """
    Actualiza únicamente el estado de envío de un registro específico.

    Se usa para marcar si el comando se envió correctamente al Arduino o si falló.

    Args:
        record_id (int): El ID del registro que se va a actualizar.
        nuevo_estado (str): El nuevo estado ('ENVIADO', 'ERROR_ARDUINO', etc.).
    """
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE historial
            SET estado_envio = ?
            WHERE id = ?
        ''', (nuevo_estado, record_id))

        conn.commit()
        print(f"Estado del registro {record_id} actualizado a '{nuevo_estado}'.")
    except sqlite3.Error as e:
        print(f"Error al actualizar el estado del registro: {e}")
    finally:
        if conn:
            conn.close()


def get_history(limit=20):
    """
    Obtiene los últimos registros del historial para mostrarlos en la web.

    Args:
        limit (int): El número máximo de registros a devolver (por defecto, 20).

    Returns:
        list: Una lista de diccionarios, donde cada diccionario es un registro.
              La lista está ordenada del más reciente al más antiguo.
    """
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        # Devolver filas como diccionarios para que sea más fácil usarlas con JSON
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM historial ORDER BY id DESC LIMIT ?', (limit,))

        rows = cursor.fetchall()
        # Convertir las filas de tipo sqlite3.Row a diccionarios estándar de Python
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Error al obtener el historial: {e}")
        return []
    finally:
        if conn:
            conn.close()


# --- Bloque de Ejecución Principal ---
# Si ejecutas este archivo directamente (python database.py),
# se llamará a la función init_db() para preparar la base de datos.
if __name__ == '__main__':
    print("Ejecutando inicialización manual de la base de datos...")
    init_db()