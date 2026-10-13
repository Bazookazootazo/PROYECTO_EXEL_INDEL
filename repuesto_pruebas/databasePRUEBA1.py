import mysql.connector
from mysql.connector import pooling
import pandas as pd
import re
import unicodedata

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

def obtener_o_crear_mapa_profesores(nombres_unicos):
    """Obtiene los IDs de los profesores o los crea si no existen en la BD."""
    mapa = {}
    if not nombres_unicos: return mapa
    
    conexion = None
    cursor = None
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor(dictionary=True)
        
        # 1. Buscar profesores existentes
        format_strings = ','.join(['%s'] * len(nombres_unicos))
        cursor.execute(f"SELECT id_profesor, nombre FROM profesores WHERE nombre IN ({format_strings})", tuple(nombres_unicos))
        for prof in cursor.fetchall():
            mapa[prof['nombre']] = prof['id_profesor']
            
        # 2. Identificar y crear profesores faltantes con datos genéricos
        faltantes = [nombre for nombre in nombres_unicos if nombre not in mapa]
        if faltantes:
            datos_nuevos = [(nombre, 'Área General', 'Externo') for nombre in faltantes]
            cursor.executemany("INSERT INTO profesores (nombre, area, tipo) VALUES (%s, %s, %s)", datos_nuevos)
            conexion.commit()
            
            # Recuperar nuevamente para obtener los IDs recién generados
            cursor.execute(f"SELECT id_profesor, nombre FROM profesores WHERE nombre IN ({format_strings})", tuple(nombres_unicos))
            for prof in cursor.fetchall():
                mapa[prof['nombre']] = prof['id_profesor']
                
        return mapa
    finally:
        if cursor: cursor.close()
        if conexion and conexion.is_connected(): conexion.close()

# --- FUNCIONES PARA INSERTAR Y ACTUALIZAR MASIVAMENTE  ---
def normalizar_texto(texto):
    """Limpia textos para tolerar errores de tipeo del usuario."""
    if pd.isna(texto): return ""
    texto = str(texto).strip().lower().replace("_", " ")
    texto = unicodedata.normalize('NFD', texto)
    return ''.join(c for c in texto if unicodedata.category(c) != 'Mn')

def procesar_carga_masiva_inteligente(ruta_archivo):
    DIAS_MAPPING = {"lunes": 1, "martes": 2, "miercoles": 3, "jueves": 4, "viernes": 5}
    AREAS_MAP = {normalizar_texto(a): a for a in ['Tecnologías de la Información', 'Mecatrónica', 'Administración', 'Recursos Humanos', 'Ciencias Básicas', 'Departamento de Prueba']}
    TIPOS_MAP = {normalizar_texto(t): t for t in ['Tiempo Completo', 'Asignatura']}

    conexion = None
    cursor = None
    try:
        # 1. Lectura y Mapeo Automático de Columnas
        df = pd.read_csv(ruta_archivo) if ruta_archivo.endswith('.csv') else pd.read_excel(ruta_archivo)
        
        columnas_normalizadas = {col: normalizar_texto(col) for col in df.columns}
        df.rename(columns=columnas_normalizadas, inplace=True)
        cols = set(df.columns)
        
        if 'nombre' not in cols:
            return False, "El archivo debe contener obligatoriamente una columna 'Nombre'."

        # Detección de intenciones (Qué quiere hacer el usuario)
        procesar_docentes = 'area' in cols and 'tipo' in cols
        procesar_horarios = {'dia', 'hora entrada', 'hora salida'}.issubset(cols)

        if not procesar_docentes and not procesar_horarios:
            return False, "Columnas insuficientes. Agrega (Área y Tipo) para docentes, o (Día, Hora Entrada, Hora Salida) para horarios."

        # 2. Pre-validación
        errores = []
        patron_hora = r"^([01]?[0-9]|2[0-3]):[0-5][0-9](:[0-5][0-9])?$"
        
        for i, fila in df.iterrows():
            f_num = i + 2
            if procesar_docentes:
                if normalizar_texto(fila.get('area')) not in AREAS_MAP: errores.append(f"Fila {f_num}: Área desconocida.")
                if normalizar_texto(fila.get('tipo')) not in TIPOS_MAP: errores.append(f"Fila {f_num}: Tipo desconocido.")
            if procesar_horarios:
                if normalizar_texto(fila.get('dia')) not in DIAS_MAPPING: errores.append(f"Fila {f_num}: Día inválido.")
                if not re.match(patron_hora, str(fila.get('hora entrada', ''))): errores.append(f"Fila {f_num}: Hora entrada inválida.")
                if not re.match(patron_hora, str(fila.get('hora salida', ''))): errores.append(f"Fila {f_num}: Hora salida inválida.")

        if errores:
            return False, "Corrige los siguientes errores en tu archivo:\n" + "\n".join(errores[:5]) + ("\n..." if len(errores)>5 else "")

        # 3. Ejecución Transaccional Segura
        conexion = obtener_conexion()
        cursor = conexion.cursor(dictionary=True)
        conexion.start_transaction()
        
        # Diccionario para estadísticas de UX
        stats = {"docentes_nuevos": 0, "docentes_actualizados": 0, "horarios_nuevos": 0}
        
        cursor.execute("SELECT id_profesor, LOWER(nombre) as nombre_lower, area, tipo FROM profesores")
        mapa_prof = {row['nombre_lower']: row for row in cursor.fetchall()}
        
        # A. UPSERT DE DOCENTES
        if procesar_docentes:
            for _, fila in df[['nombre', 'area', 'tipo']].drop_duplicates(subset=['nombre']).iterrows():
                n_norm = str(fila['nombre']).strip().lower()
                a_real = AREAS_MAP[normalizar_texto(fila['area'])]
                t_real = TIPOS_MAP[normalizar_texto(fila['tipo'])]
                
                if n_norm in mapa_prof:
                    actual = mapa_prof[n_norm]
                    if actual['area'] != a_real or actual['tipo'] != t_real:
                        cursor.execute("UPDATE profesores SET area = %s, tipo = %s WHERE id_profesor = %s", (a_real, t_real, actual['id_profesor']))
                        stats["docentes_actualizados"] += 1
                else:
                    nombre_formateado = str(fila['nombre']).strip().title()
                    cursor.execute("INSERT INTO profesores (nombre, area, tipo) VALUES (%s, %s, %s)", (nombre_formateado, a_real, t_real))
                    # Re-consultamos el ID para compatibilidad universal de bases de datos (MySQL/PostgreSQL)
                    cursor.execute("SELECT id_profesor FROM profesores WHERE nombre = %s", (nombre_formateado,))
                    nuevo_id = cursor.fetchone()['id_profesor']
                    mapa_prof[n_norm] = {'id_profesor': nuevo_id, 'area': a_real, 'tipo': t_real}
                    stats["docentes_nuevos"] += 1

        # B. APPEND DE HORARIOS (Sin duplicar)
        if procesar_horarios:
            for _, fila in df.iterrows():
                n_norm = str(fila['nombre']).strip().lower()
                if n_norm not in mapa_prof:
                    raise Exception(f"El profesor '{fila['nombre']}' no existe. Agrega sus columnas de Área y Tipo al archivo.")
                    
                id_prof = mapa_prof[n_norm]['id_profesor']
                id_dia = DIAS_MAPPING[normalizar_texto(fila['dia'])]
                h_in = str(fila['hora entrada']).strip() + (":00" if len(str(fila['hora entrada']).strip()) == 5 else "")
                h_out = str(fila['hora salida']).strip() + (":00" if len(str(fila['hora salida']).strip()) == 5 else "")

                cursor.execute("""
                    SELECT id_horario FROM horarios_docentes 
                    WHERE id_profesor = %s AND id_dia = %s AND hora_entrada = %s AND hora_salida = %s
                """, (id_prof, id_dia, h_in, h_out))
                
                if not cursor.fetchone():
                    cursor.execute("INSERT INTO horarios_docentes (id_profesor, id_dia, hora_entrada, hora_salida) VALUES (%s, %s, %s, %s)", (id_prof, id_dia, h_in, h_out))
                    stats["horarios_nuevos"] += 1

        conexion.commit()
        
        # Construir mensaje dinámico y satisfactorio para el usuario
        msg = []
        if stats["docentes_nuevos"] > 0: msg.append(f"✅ {stats['docentes_nuevos']} docentes nuevos registrados.")
        if stats["docentes_actualizados"] > 0: msg.append(f"🔄 {stats['docentes_actualizados']} docentes actualizados.")
        if stats["horarios_nuevos"] > 0: msg.append(f"🗓 {stats['horarios_nuevos']} turnos de horario agregados.")
        if not msg: msg.append("✅ El archivo fue procesado, pero los datos ya estaban sincronizados (sin cambios).")
        
        return True, "\n".join(msg)
        
    except Exception as e:
        if conexion and conexion.is_connected(): conexion.rollback()
        return False, f"Fallo al procesar: {str(e)}"
    finally:
        if cursor: cursor.close()
        if conexion and conexion.is_connected(): conexion.close()