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

def actualizar_horario(id_horario, id_dia, hora_entrada, hora_salida):
    conexion = None
    cursor = None
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        query = """
            UPDATE horarios_docentes 
            SET id_dia = %s, hora_entrada = %s, hora_salida = %s 
            WHERE id_horario = %s
        """
        cursor.execute(query, (id_dia, hora_entrada, hora_salida, id_horario))
        conexion.commit()
    finally:
        if cursor: cursor.close()
        if conexion and conexion.is_connected(): conexion.close()

# --- FUNCIONES PARA IMPORTACIÓN MASIVA (usadas por importador.py) ---
def obtener_todos_los_horarios():
    """Todos los horarios de todos los docentes en una sola consulta (para importación masiva)."""
    conexion = None
    cursor = None
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor(dictionary=True)
        cursor.execute(
            """SELECT id_horario, id_profesor, id_dia,
                      TIME_FORMAT(hora_entrada, '%H:%i') AS hora_entrada,
                      TIME_FORMAT(hora_salida, '%H:%i') AS hora_salida
               FROM horarios_docentes"""
        )
        return cursor.fetchall()
    finally:
        if cursor: cursor.close()
        if conexion and conexion.is_connected(): conexion.close()

def aplicar_cambios(docentes):
    """
    ÚNICA puerta de escritura para cambios masivos: la usan tanto la importación desde
    Excel como las acciones en bloque del CRUD, así ambos comparten reglas y transacción.

    `docentes` es una lista de dicts ya revisados y confirmados por el usuario:
        id: int o None (None = crear)   nombre, area, tipo: str
        actualizar: bool (True = ya existía y cambia Área/Tipo)
        turnos: [(id_dia, hora_entrada, hora_salida), ...]  a insertar
        quitar: [id_horario, ...]  a eliminar
    Todo ocurre en UNA transacción: o se aplica completo o no se aplica nada.
    Insertar es idempotente (si el turno ya existe no se duplica), por lo que un doble clic
    o una vista previa vieja no ensucian la base. Devuelve lo que realmente pasó.
    """
    stats = {"docentes_creados": 0, "docentes_actualizados": 0, "turnos_agregados": 0, "turnos_quitados": 0}
    conexion = None
    cursor = None
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        conexion.start_transaction()

        for d in docentes:
            if d["id"] is None:
                cursor.execute(
                    "INSERT INTO profesores (nombre, area, tipo) VALUES (%s, %s, %s)",
                    (d["nombre"], d["area"], d["tipo"])
                )
                d["id"] = cursor.lastrowid
                stats["docentes_creados"] += 1
            elif d["actualizar"]:
                cursor.execute(
                    "UPDATE profesores SET area = %s, tipo = %s WHERE id_profesor = %s",
                    (d["area"], d["tipo"], d["id"])
                )
                stats["docentes_actualizados"] += 1

            for id_horario in d.get("quitar", []):
                cursor.execute("DELETE FROM horarios_docentes WHERE id_horario = %s", (id_horario,))
                stats["turnos_quitados"] += cursor.rowcount

            for id_dia, hora_entrada, hora_salida in d.get("turnos", []):
                cursor.execute(
                    """INSERT INTO horarios_docentes (id_profesor, id_dia, hora_entrada, hora_salida)
                       SELECT %s, %s, %s, %s FROM DUAL
                       WHERE NOT EXISTS (SELECT 1 FROM horarios_docentes
                                         WHERE id_profesor = %s AND id_dia = %s AND hora_entrada = %s AND hora_salida = %s)""",
                    (d["id"], id_dia, hora_entrada, hora_salida, d["id"], id_dia, hora_entrada, hora_salida)
                )
                stats["turnos_agregados"] += cursor.rowcount

        conexion.commit()
        return stats
    except Exception:
        if conexion and conexion.is_connected(): conexion.rollback()
        raise
    finally:
        if cursor: cursor.close()
        if conexion and conexion.is_connected(): conexion.close()

def eliminar_profesores_en_bloque(ids):
    """
    Elimina varios docentes respetando la integridad referencial.
    No depende de que exista ON DELETE CASCADE: borra explícitamente sus horarios y luego al docente.
    Cada docente va en su propio SAVEPOINT: si otra parte del sistema lo referencia (p. ej. su
    historial de asistencias) la base lo rechaza, se deshace SOLO ese docente y se reporta.
    Devuelve (eliminados: [id], bloqueados: {id: motivo}).
    """
    eliminados, bloqueados = [], {}
    conexion = None
    cursor = None
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        conexion.start_transaction()

        for id_profesor in ids:
            cursor.execute("SAVEPOINT eliminar_docente")
            try:
                cursor.execute("DELETE FROM horarios_docentes WHERE id_profesor = %s", (id_profesor,))
                cursor.execute("DELETE FROM profesores WHERE id_profesor = %s", (id_profesor,))
                if cursor.rowcount:
                    eliminados.append(id_profesor)
                cursor.execute("RELEASE SAVEPOINT eliminar_docente")
            except mysql.connector.IntegrityError:
                cursor.execute("ROLLBACK TO SAVEPOINT eliminar_docente")
                bloqueados[id_profesor] = "tiene registros asociados en otras partes del sistema (por ejemplo, asistencias)"

        conexion.commit()
        return eliminados, bloqueados
    except Exception:
        if conexion and conexion.is_connected(): conexion.rollback()
        raise
    finally:
        if cursor: cursor.close()
        if conexion and conexion.is_connected(): conexion.close()