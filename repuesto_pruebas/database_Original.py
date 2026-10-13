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
    """
    Convierte cualquier texto a minúsculas, elimina espacios extra,
    quita acentos y reemplaza guiones bajos por espacios.
    Ejemplo: 'Hora_Entrada ' -> 'hora entrada' / 'Miércoles' -> 'miercoles'
    """
    if pd.isna(texto):
        return ""
    texto = str(texto).strip().lower().replace("_", " ")
    # Eliminar acentos
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    return texto

def procesar_carga_masiva(ruta_archivo, tipo_carga):
    # Diccionarios de mapeo flexible (claves en texto normalizado sin acentos/mayúsculas)
    DIAS_MAPPING = {
        "lunes": 1, "martes": 2, "miercoles": 3, "jueves": 4, "viernes": 5
    }
    
    AREAS_MAP = {
        normalizar_texto(a): a for a in [
            'Tecnologías de la Información', 'Mecatrónica', 
            'Administración', 'Recursos Humanos', 'Ciencias Básicas', 'Departamento de Prueba'
        ]
    }
    
    TIPOS_MAP = {
        normalizar_texto(t): t for t in ['Tiempo Completo', 'Asignatura']
    }

    conexion = None
    cursor = None
    try:
        # 1. Leer archivo
        df = pd.read_csv(ruta_archivo) if ruta_archivo.endswith('.csv') else pd.read_excel(ruta_archivo)
        
        # 2. Normalizar nombres de columnas (Acepta 'Hora Entrada', 'hora_entrada', 'HORA ENTRADA', etc.)
        columnas_originales = {col: normalizar_texto(col) for col in df.columns}
        df.rename(columns=columnas_originales, inplace=True)
        
        # Mapeo de columnas requeridas normalizadas
        req_docente = ['nombre', 'area', 'tipo']
        req_horario = ['nombre', 'dia', 'hora entrada', 'hora salida']
        
        if tipo_carga == "Docente": columnas_necesarias = req_docente
        elif tipo_carga == "Horario": columnas_necesarias = req_horario
        else: columnas_necesarias = list(set(req_docente + req_horario))
            
        for col in columnas_necesarias:
            if col not in df.columns:
                return False, f"Falta la columna '{col.title()}' en el archivo."

        # 3. PRE-VALIDACIÓN FLEXIBLE Y TOLERANTE
        errores = []
        patron_hora = r"^([01]?[0-9]|2[0-3]):[0-5][0-9](:[0-5][0-9])?$"
        
        for i, fila in df.iterrows():
            f_num = i + 2 # Número de fila en Excel
            
            if tipo_carga in ["Docente", "Ambos"]:
                area_norm = normalizar_texto(fila.get('area', ''))
                tipo_norm = normalizar_texto(fila.get('tipo', ''))
                
                if area_norm not in AREAS_MAP:
                    errores.append(f"Fila {f_num}: Área '{fila.get('area')}' no reconocida.")
                if tipo_norm not in TIPOS_MAP:
                    errores.append(f"Fila {f_num}: Tipo '{fila.get('tipo')}' no reconocido.")
                    
            if tipo_carga in ["Horario", "Ambos"]:
                dia_norm = normalizar_texto(fila.get('dia', ''))
                h_in = str(fila.get('hora entrada', '')).strip()
                h_out = str(fila.get('hora salida', '')).strip()
                
                if dia_norm not in DIAS_MAPPING:
                    errores.append(f"Fila {f_num}: Día '{fila.get('dia')}' inválido (Solo Lunes a Viernes).")
                if not re.match(patron_hora, h_in):
                    errores.append(f"Fila {f_num}: Hora Entrada inválida ({h_in}). Usa HH:MM.")
                if not re.match(patron_hora, h_out):
                    errores.append(f"Fila {f_num}: Hora Salida inválida ({h_out}). Usa HH:MM.")

        if errores:
            return False, "Errores de validación:\n" + "\n".join(errores[:5]) + ("\n..." if len(errores) > 5 else "")

        # 4. INSERCIÓN Y ACTUALIZACIÓN EN BASE DE DATOS
        conexion = obtener_conexion()
        cursor = conexion.cursor(dictionary=True)
        conexion.start_transaction()
        
        # Obtener mapa de profesores existentes
        cursor.execute("SELECT id_profesor, LOWER(nombre) as nombre_lower, area, tipo FROM profesores")
        mapa_prof = {row['nombre_lower']: row for row in cursor.fetchall()}
        
        # --- PROCESAR DOCENTES (UPSERT) ---
        if tipo_carga in ["Docente", "Ambos"]:
            profesores_unicos = df[['nombre', 'area', 'tipo']].drop_duplicates(subset=['nombre'])
            for _, fila in profesores_unicos.iterrows():
                n_norm = str(fila['nombre']).strip().lower()
                area_real = AREAS_MAP[normalizar_texto(fila['area'])]
                tipo_real = TIPOS_MAP[normalizar_texto(fila['tipo'])]
                
                if n_norm in mapa_prof:
                    # Si ya existe, actualiza su Área/Tipo si cambiaron
                    actual = mapa_prof[n_norm]
                    if actual['area'] != area_real or actual['tipo'] != tipo_real:
                        cursor.execute(
                            "UPDATE profesores SET area = %s, tipo = %s WHERE id_profesor = %s",
                            (area_real, tipo_real, actual['id_profesor'])
                        )
                else:
                    # Crear nuevo docente con formato limpio
                    nombre_formateado = str(fila['nombre']).strip().title()
                    cursor.execute(
                        "INSERT INTO profesores (nombre, area, tipo) VALUES (%s, %s, %s)",
                        (nombre_formateado, area_real, tipo_real)
                    )
                    mapa_prof[n_norm] = {'id_profesor': cursor.lastrowid, 'area': area_real, 'tipo': tipo_real}
                    
        # --- PROCESAR HORARIOS (SMART MERGE / APPEND) ---
        if tipo_carga in ["Horario", "Ambos"]:
            for _, fila in df.iterrows():
                n_norm = str(fila['nombre']).strip().lower()
                if n_norm not in mapa_prof:
                    raise Exception(f"El profesor '{fila['nombre']}' no existe. Sube 'Ambos' o regístralo primero.")
                    
                id_prof = mapa_prof[n_norm]['id_profesor']
                id_dia = DIAS_MAPPING[normalizar_texto(fila['dia'])]
                
                h_in = str(fila['hora entrada']).strip()
                if len(h_in) == 5: h_in += ":00"
                h_out = str(fila['hora salida']).strip()
                if len(h_out) == 5: h_out += ":00"

                # Insertar solo si la combinación no existe exactamente igual
                cursor.execute("""
                    SELECT id_horario FROM horarios_docentes 
                    WHERE id_profesor = %s AND id_dia = %s AND hora_entrada = %s AND hora_salida = %s
                """, (id_prof, id_dia, h_in, h_out))
                
                if not cursor.fetchone():
                    cursor.execute(
                        "INSERT INTO horarios_docentes (id_profesor, id_dia, hora_entrada, hora_salida) VALUES (%s, %s, %s, %s)", 
                        (id_prof, id_dia, h_in, h_out)
                    )

        conexion.commit()
        return True, f"Carga de '{tipo_carga}' procesada correctamente."
        
    except Exception as e:
        if conexion and conexion.is_connected():
            conexion.rollback()
        return False, f"Fallo al procesar: {str(e)}"
    finally:
        if cursor: cursor.close()
        if conexion and conexion.is_connected(): conexion.close()