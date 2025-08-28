import sqlite3
import json
from datetime import datetime

# Nombre del archivo de la base de datos
DATABASE_NAME = 'historial.db'


def init_db():
    """
    Inicializa la base de datos y crea la tabla 'historial' si no existe.
    """
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()

        # Crear la tabla si no existe
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

        conn.commit()
        print("Base de datos inicializada correctamente.")
    except sqlite3.Error as e:
        print(f"Error al inicializar la base de datos: {e}")
    finally:
        if conn:
            conn.close()


def add_record(material, objetos, confianza, estado_envio):
    """
    Añade un nuevo registro a la tabla 'historial'.

    Args:
        material (str): El material clasificado ('plástico', 'orgánico', 'metal', 'null').
        objetos (list): Una lista de diccionarios con los objetos detectados.
        confianza (float): El nivel de confianza del objeto principal.
        estado_envio (str): El estado del envío al Arduino ('PENDIENTE', 'ENVIADO', 'ERROR').

    Returns:
        int: El ID del registro insertado, o None si hubo un error.
    """
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()

        fecha_actual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Convertimos la lista de objetos a una cadena JSON para almacenarla
        objetos_json = json.dumps(objetos)

        cursor.execute('''
            INSERT INTO historial (fecha, material, objetos_detectados, confianza, estado_envio)
            VALUES (?, ?, ?, ?, ?)
        ''', (fecha_actual, material, objetos_json, confianza, estado_envio))

        conn.commit()
        last_id = cursor.lastrowid
        print(f"Registro añadido con ID: {last_id}")
        return last_id
    except sqlite3.Error as e:
        print(f"Error al añadir registro a la base de datos: {e}")
        return None
    finally:
        if conn:
            conn.close()


def update_record_status(record_id, nuevo_estado):
    """
    Actualiza el estado de envío de un registro específico.

    Args:
        record_id (int): El ID del registro a actualizar.
        nuevo_estado (str): El nuevo estado ('ENVIADO', 'ERROR').
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
        print(f"Estado del registro {record_id} actualizado a {nuevo_estado}.")
    except sqlite3.Error as e:
        print(f"Error al actualizar el estado del registro: {e}")
    finally:
        if conn:
            conn.close()


def get_history(limit=20):
    """
    Obtiene los últimos registros del historial.

    Args:
        limit (int): El número máximo de registros a obtener.

    Returns:
        list: Una lista de diccionarios, donde cada diccionario representa un registro.
    """
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        # Devolver filas como diccionarios para facilitar su uso en Flask
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM historial ORDER BY id DESC LIMIT ?', (limit,))

        rows = cursor.fetchall()
        # Convertir las filas a una lista de diccionarios estándar
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Error al obtener el historial: {e}")
        return []
    finally:
        if conn:
            conn.close()


# Para ejecutar la inicialización directamente desde la terminal
if __name__ == '__main__':
    init_db()
