"""
Catálogos de la institución: única fuente de verdad para Áreas, Tipos y Días.

Cada entrada lleva sus alias (otras formas en que la gente suele escribirla).
Para que el importador reconozca algo nuevo basta agregarlo aquí; el formulario
de docentes y la plantilla de Excel se actualizan solos.
"""
import re
import unicodedata
from difflib import get_close_matches

AREAS = {
    "Tecnologías de la Información": ["ti", "tic", "tics", "sistemas", "informatica", "computacion", "sistemas computacionales"],
    "Mecatrónica": [],
    "Administración": ["admin", "administrativa", "administrativo"],
    "Recursos Humanos": ["rh", "rrhh", "capital humano"],
    "Ciencias Básicas": ["basicas", "ciencias", "matematicas", "fisica", "quimica"],
    "Departamento de Prueba": ["prueba", "depto de prueba"],
}

TIPOS = {
    "Tiempo Completo": ["tc", "ptc", "completo", "planta", "de planta", "full time"],
    "Asignatura": ["pa", "por asignatura", "por horas", "hora clase", "horas clase", "eventual", "part time"],
}

DIAS = {"Lunes": 1, "Martes": 2, "Miércoles": 3, "Jueves": 4, "Viernes": 5}
DIAS_NO_ADMITIDOS = {"Sábado": 6, "Domingo": 7}      # se reconocen para avisar con claridad
DIAS_CORTO = {1: "Lun", 2: "Mar", 3: "Mié", 4: "Jue", 5: "Vie"}
NOMBRE_DIA = {i: n for n, i in {**DIAS, **DIAS_NO_ADMITIDOS}.items()}

# Nombres con los que suelen titularse las columnas de un archivo.
CAMPOS = {
    "nombre": ["nombre", "nombre completo", "docente", "profesor", "maestro", "catedratico", "empleado", "nombre del docente"],
    "area": ["area", "departamento", "depto", "carrera", "division", "academia"],
    "tipo": ["tipo", "tipo de docente", "tipo de contrato", "categoria", "contratacion", "nombramiento"],
    "dia": ["dia", "dias", "dia de la semana", "dia semana"],
    "entrada": ["entrada", "hora entrada", "hora de entrada", "hora inicio", "inicio", "desde"],
    "salida": ["salida", "hora salida", "hora de salida", "hora fin", "fin", "hasta", "termino"],
    "horario": ["horario", "turno", "hora", "horas"],
}
ETIQUETAS = {
    "nombre": "Nombre", "area": "Área", "tipo": "Tipo", "dia": "Día",
    "entrada": "Entrada", "salida": "Salida", "horario": "Horario (07:00-12:00)",
}


def normalizar(texto):
    """Minúsculas, sin acentos ni signos: 'Miércoles.' -> 'miercoles'."""
    if texto is None or (isinstance(texto, float) and texto != texto):
        return ""
    s = unicodedata.normalize("NFD", str(texto).lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def _indice(catalogo):
    return {normalizar(n): canon for canon, alias in catalogo.items() for n in (canon, *alias)}


INDICE_AREAS = _indice(AREAS)
INDICE_TIPOS = _indice(TIPOS)


def resolver(valor, indice):
    """
    Traduce lo que escribió el usuario a una entrada del catálogo.
    Devuelve (canónico, seguro): seguro=False cuando fue una interpretación
    aproximada (typo o texto que contiene el nombre) y conviene confirmarla.
    Si no reconoce nada devuelve (None, False).
    """
    nv = normalizar(valor)
    if not nv:
        return None, False
    if nv in indice:
        return indice[nv], True
    for clave in sorted(indice, key=len, reverse=True):          # "Carrera de Mecatrónica"
        if len(clave) >= 4 and re.search(rf"\b{re.escape(clave)}\b", nv):
            return indice[clave], False
    if len(nv) >= 4:
        cerca = get_close_matches(nv, list(indice), n=1, cutoff=0.8)   # typos: "Mecatrnica"
        if cerca:
            return indice[cerca[0]], False
    return None, False