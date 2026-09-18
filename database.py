import mysql.connector
from mysql.connector import pooling

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'control_asistencia',
    'port': 3306
}

# 1. Crear el Pool de Conexiones (Se ejecuta una sola vez al importar el módulo)
try:
    db_pool = mysql.connector.pooling.MySQLConnectionPool(
        pool_name="asistencia_pool",
        pool_size=5,  # 5 conexiones simultáneas es ideal para una app de escritorio
        pool_reset_session=True,
        **DB_CONFIG
    )
except Exception as e:
    print(f"Error crítico: No se pudo inicializar el Pool de Conexiones: {e}")
    db_pool = None

def obtener_conexion():
    """Obtiene una conexión activa desde el pool."""
    if db_pool is None:
        raise Exception("El pool de base de datos no está inicializado.")
    return db_pool.get_connection()

# --- FUNCIONES PARA PROFESORES ---
def agregar_profesor(nombre, area, tipo):
    conexion = None
    cursor = None
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute("INSERT INTO profesores (nombre, area, tipo) VALUES (%s, %s, %s)", (nombre, area, tipo))
        conexion.commit()
        return cursor.lastrowid
    finally:
        # El bloque finally asegura que siempre se devuelva la conexión al pool, incluso si hay error
        if cursor: cursor.close()
        if conexion and conexion.is_connected(): conexion.close()

def obtener_profesores():
    conexion = None
    cursor = None
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor(dictionary=True)
        cursor.execute("SELECT * FROM profesores ORDER BY nombre ASC")
        return cursor.fetchall()
    finally:
        if cursor: cursor.close()
        if conexion and conexion.is_connected(): conexion.close()

def actualizar_profesor(id_profesor, nombre, area, tipo):
    conexion = None
    cursor = None
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute(
            "UPDATE profesores SET nombre = %s, area = %s, tipo = %s WHERE id_profesor = %s",
            (nombre, area, tipo, id_profesor)
        )
        conexion.commit()
    finally:
        if cursor: cursor.close()
        if conexion and conexion.is_connected(): conexion.close()

def eliminar_profesor(id_profesor):
    conexion = None
    cursor = None
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute("DELETE FROM profesores WHERE id_profesor = %s", (id_profesor,))
        conexion.commit()
    finally:
        if cursor: cursor.close()
        if conexion and conexion.is_connected(): conexion.close()

# --- FUNCIONES PARA HORARIOS ---
def agregar_horario(id_profesor, id_dia, hora_entrada, hora_salida):
    conexion = None
    cursor = None
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        query = """
            INSERT INTO horarios_docentes (id_profesor, id_dia, hora_entrada, hora_salida)
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(query, (id_profesor, id_dia, hora_entrada, hora_salida))
        conexion.commit()
    finally:
        if cursor: cursor.close()
        if conexion and conexion.is_connected(): conexion.close()

def obtener_horarios_profesor(id_profesor):
    conexion = None
    cursor = None
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor(dictionary=True)
        query = """
            SELECT 
                h.id_horario,
                d.nombre_dia,
                h.id_dia,
                TIME_FORMAT(h.hora_entrada, '%H:%i') AS hora_entrada,
                TIME_FORMAT(h.hora_salida, '%H:%i') AS hora_salida
            FROM horarios_docentes h
            INNER JOIN dias_semana d ON h.id_dia = d.id_dia
            WHERE h.id_profesor = %s
            ORDER BY h.id_dia ASC, h.hora_entrada ASC
        """
        cursor.execute(query, (id_profesor,))
        return cursor.fetchall()
    finally:
        if cursor: cursor.close()
        if conexion and conexion.is_connected(): conexion.close()

def eliminar_horario(id_horario):
    conexion = None
    cursor = None
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute("DELETE FROM horarios_docentes WHERE id_horario = %s", (id_horario,))
        conexion.commit()
    finally:
        if cursor: cursor.close()
        if conexion and conexion.is_connected(): conexion.close()