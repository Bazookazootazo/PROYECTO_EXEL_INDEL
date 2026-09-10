import mysql.connector

# Configuración de conexión a MySQL en XAMPP
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'control_asistencia',
    'port': 3306
}

def obtener_conexion():
    """Establece conexión con MySQL."""
    return mysql.connector.connect(**DB_CONFIG)

# --- FUNCIONES PARA PROFESORES ---

def agregar_profesor(nombre, area):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("INSERT INTO profesores (nombre, area) VALUES (%s, %s)", (nombre, area))
    conexion.commit()
    id_creado = cursor.lastrowid
    cursor.close()
    conexion.close()
    return id_creado

def obtener_profesores():
    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    cursor.execute("SELECT * FROM profesores ORDER BY nombre ASC")
    profesores = cursor.fetchall()
    cursor.close()
    conexion.close()
    return profesores

def eliminar_profesor(id_profesor):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM profesores WHERE id_profesor = %s", (id_profesor,))
    conexion.commit()
    cursor.close()
    conexion.close()

# --- FUNCIONES PARA HORARIOS ---

def agregar_horario(id_profesor, id_dia, hora_entrada, hora_salida):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    query = """
        INSERT INTO horarios_docentes (id_profesor, id_dia, hora_entrada, hora_salida)
        VALUES (%s, %s, %s, %s)
    """
    cursor.execute(query, (id_profesor, id_dia, hora_entrada, hora_salida))
    conexion.commit()
    cursor.close()
    conexion.close()

def obtener_horarios_profesor(id_profesor):
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
    horarios = cursor.fetchall()
    cursor.close()
    conexion.close()
    return horarios

def eliminar_horario(id_horario):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM horarios_docentes WHERE id_horario = %s", (id_horario,))
    conexion.commit()
    cursor.close()
    conexion.close()