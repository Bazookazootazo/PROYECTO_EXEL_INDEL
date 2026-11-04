import csv
import io
import os
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, time
from difflib import SequenceMatcher, get_close_matches
import pandas as pd

from gestion_docente.catalogos import (AREAS, CAMPOS, DIAS, DIAS_CORTO, DIAS_NO_ADMITIDOS, ETIQUETAS,
                                     INDICE_AREAS, INDICE_TIPOS, INDICE_TURNOS, NOMBRE_DIA, TIPOS, TURNOS,
                                     normalizar, resolver)
from utilerias import database as db

# ───────────────────────────── Horas y días ─────────────────────────────

_HORA = r"\d{1,2}(?:[:.h]?\d{2})?(?::\d{2})?(?:\s*[ap]\.?\s*m\.?)?"
_RE_HORA = re.compile(r"(\d{1,2})(?:[:.h]?(\d{2}))?(?::\d{2})?(?:\s*([ap])\.?\s*m\.?)?\s*(?:hrs?\.?|hs\.?|h)?")
_RE_RANGO = re.compile(rf"({_HORA})\s*(?:-|–|—|a|al|hasta|to)\s*({_HORA})", re.I)
_RE_PARECE_HORA = re.compile(r"\d\s*[:h]\s*\d|\d\s*[ap]\.?\s*m\b|^0\.\d{4,}$", re.I)


def parse_hora(valor):
    """Devuelve 'HH:MM' o None. Acepta 7, 7:00, 07:00:00, 0700, 7am, 7:30 pm, 19 hrs, horas de Excel."""
    if isinstance(valor, (datetime, time)):
        return f"{valor.hour:02d}:{valor.minute:02d}"
    s = str(valor).strip().lower()
    if not s:
        return None
    m = re.search(r"\d{4}-\d{2}-\d{2}[ t](\d{1,2}):(\d{2})", s)          # fecha+hora de Excel
    if m:
        return f"{int(m.group(1)):02d}:{m.group(2)}"
    if re.fullmatch(r"0\.\d{4,}", s):                                     # fracción de día de Excel
        minutos = round(float(s) * 1440)
        return f"{minutos // 60:02d}:{minutos % 60:02d}"
    m = _RE_HORA.fullmatch(s)
    if not m:
        return None
    h, mi, ampm = int(m.group(1)), int(m.group(2) or 0), m.group(3)
    if ampm == "p" and h < 12:
        h += 12
    elif ampm == "a" and h == 12:
        h = 0
    return f"{h:02d}:{mi:02d}" if h < 24 and mi < 60 else None


def parse_rangos(valor):
    """'07:00-12:00 y 14:00 a 16:00' -> [('07:00','12:00'), ('14:00','16:00')]"""
    rangos = []
    for a, b in _RE_RANGO.findall(str(valor)):
        ha, hb = parse_hora(a), parse_hora(b)
        if ha and hb:
            rangos.append((ha, hb))
    return rangos


_DIAS_TXT = {normalizar(n): i for n, i in {**DIAS, **DIAS_NO_ADMITIDOS}.items()}


def _dia(token):
    if len(token) < 2:
        return None
    for nombre, i in _DIAS_TXT.items():                                   # lu, mar, mie, miercoles...
        if nombre.startswith(token):
            return i
    if len(token) >= 5:
        cerca = get_close_matches(token, list(_DIAS_TXT), n=1, cutoff=0.8)   # "miercols"
        if cerca:
            return _DIAS_TXT[cerca[0]]
    return None


def parse_dias(valor):
    """'Lunes' -> [1]; 'Lun-Vie' / 'Lunes a Viernes' -> [1..5]; 'Lunes, Miércoles y Viernes' -> [1,3,5]"""
    s = normalizar(re.sub(r"[-–—]", " a ", str(valor)))
    m = re.fullmatch(r"(?:de\s+)?([a-z]{2,})\s+(?:a|al|hasta)\s+([a-z]{2,})", s)
    if m:
        ini, fin = _dia(m.group(1)), _dia(m.group(2))
        if ini and fin and ini <= fin:
            return list(range(ini, fin + 1))
    dias = []
    for token in s.split():
        d = _dia(token)
        if d and d not in dias:
            dias.append(d)
    return dias


def texto_turno(turno):
    dia, entrada, salida = turno
    return f"{DIAS_CORTO.get(dia, NOMBRE_DIA.get(dia, dia))} {entrada}–{salida}"


def inferir_turno(turnos):
    """Matutino / Vespertino / Mixto según las horas de sus turnos; None si no hay horario."""
    if not turnos:
        return None
    manana = any(entrada < "14:00" for _, entrada, _ in turnos)
    tarde = any(salida > "14:00" for _, _, salida in turnos)
    return "Mixto" if manana and tarde else "Matutino" if manana else "Vespertino"


# ───────────────────────────── Lectura de archivos ─────────────────────────────

def _leer_csv(ruta):
    texto = ""
    for codificacion in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            with open(ruta, newline="", encoding=codificacion) as f:
                texto = f.read()
            break
        except UnicodeDecodeError:
            continue
    try:
        sep = csv.Sniffer().sniff(texto[:5000], delimiters=",;\t|").delimiter
    except csv.Error:
        sep = ","
    filas = list(csv.reader(io.StringIO(texto), delimiter=sep))
    ancho = max((len(f) for f in filas), default=0)
    return pd.DataFrame([f + [""] * (ancho - len(f)) for f in filas])


def leer_hojas(ruta):
    """Lee únicamente las hojas con datos reales, descartando pestañas auxiliares u ocultas."""
    if os.path.splitext(ruta)[1].lower() in (".csv", ".txt", ".tsv"):
        return {"Datos": _leer_csv(ruta)}
        
    hojas = pd.read_excel(ruta, sheet_name=None, header=None, dtype=str, keep_default_na=False)
    
    hojas_excluidas = {"ejemplo", "valores válidos", "valores validos", "plantilla", "instrucciones", "ayuda"}
    hojas_filtradas = {}
    
    for nombre, df in hojas.items():
        if df.empty:
            continue
        if any(exc in normalizar(nombre) for exc in hojas_excluidas):
            continue
        hojas_filtradas[nombre] = df
        
    return hojas_filtradas if hojas_filtradas else {n: df for n, df in hojas.items() if not df.empty}


@dataclass
class Tabla:
    hoja: str
    encabezados: list
    filas: list          # list[list[str]]
    fila0: int           # número (1-based) de la primera fila de datos en el archivo

    @property
    def sin_encabezado(self):
        return self.fila0 == 1


def _puntos(nh):
    """Qué tanto se parece un encabezado normalizado a cada campo -> [(puntos, campo)]."""
    if not nh:
        return []
    palabras, salida = set(nh.split()), []
    for campo, sinonimos in CAMPOS.items():
        mejor = 0
        for s in sinonimos:
            ps = set(s.split())
            if nh == s:
                mejor = 1.0
                break
            if ps <= palabras:
                mejor = max(mejor, 0.9 - 0.01 * len(palabras - ps))        # más específico gana
            elif len(nh) >= 4 and SequenceMatcher(None, nh, s).ratio() >= 0.85:
                mejor = max(mejor, 0.8)
        if mejor:
            salida.append((mejor, campo))
    return salida


def _dia_de_encabezado(texto):
    dias = parse_dias(texto)
    return dias[0] if len(dias) == 1 and dias[0] <= 5 and len(normalizar(texto).split()) <= 2 else None


def _parece_dato(fila):
    return any(c and (_RE_PARECE_HORA.search(c) or parse_dias(c)) for c in fila)


def _fila_encabezado(filas):
    """Índice de la fila que parece encabezado (ignora títulos previos); None si el archivo no trae encabezados."""
    mejor, mejor_pts = None, 0
    for i, fila in enumerate(filas[:15]):
        pts = sum(1 for c in fila if _puntos(normalizar(c)))
        dias = sum(1 for c in fila if _dia_de_encabezado(c))
        pts += dias if dias >= 2 else 0
        if pts > mejor_pts:
            mejor, mejor_pts = i, pts
    if mejor is not None and (mejor_pts >= 2 or not _parece_dato(filas[mejor])):
        return mejor
    return None


def _construir_tabla(hoja, raw):
    filas = [[str(c).strip() for c in fila] for fila in raw.fillna("").values.tolist()]
    h = _fila_encabezado(filas)
    encabezado, datos, fila0 = (filas[h], filas[h + 1:], h + 2) if h is not None else ([""] * raw.shape[1], filas, 1)
    conservar = [i for i in range(len(encabezado)) if encabezado[i] or any(f[i] for f in datos)]
    nombres, usados = [], defaultdict(int)
    for i in conservar:
        base = encabezado[i] or f"Columna {i + 1}"
        usados[base] += 1
        nombres.append(base if usados[base] == 1 else f"{base} ({usados[base]})")
    return Tabla(hoja, nombres, [[f[i] for i in conservar] for f in datos], fila0)


# ───────────────────────────── Detección de columnas ─────────────────────────────

def _detectar_mapeo(t, cols_dia):
    """{campo: índice de columna}. Primero por título; lo que falte, por el contenido."""
    m = {}
    candidatos = sorted(((p, i, c) for i, h in enumerate(t.encabezados) if i not in cols_dia
                         for p, c in _puntos(normalizar(h))), reverse=True)
    for _, i, campo in candidatos:
        if campo not in m and i not in m.values():
            m[campo] = i

    libres = lambda: [i for i in range(len(t.encabezados)) if i not in m.values() and i not in cols_dia]

    def fraccion(i, pred):
        vals = [f[i] for f in t.filas[:300] if f[i]]
        return sum(1 for v in vals if pred(v)) / len(vals) if vals else 0

    def mejor_columna(pred, minimo=0.7):
        pool = [(fraccion(i, pred), -i) for i in libres()]
        return -max(pool)[1] if pool and max(pool)[0] >= minimo else None

    if "turno" in m and "horario" not in m and fraccion(m["turno"], lambda v: bool(parse_rangos(v))) >= 0.7:
        m["horario"] = m.pop("turno")                                     # «Turno» = 07:00-12:00

    if not cols_dia and "dia" not in m:
        i = mejor_columna(lambda v: bool(parse_dias(v)))
        if i is not None:
            m["dia"] = i
    horas = [i for i in libres() if fraccion(i, lambda v: bool(_RE_PARECE_HORA.search(v)) and parse_hora(v)) >= 0.7]
    for campo in ("entrada", "salida"):
        if campo not in m and horas:
            m[campo] = horas.pop(0)
    if "horario" not in m and "entrada" not in m and "salida" not in m:
        i = mejor_columna(lambda v: bool(parse_rangos(v)))
        if i is not None:
            m["horario"] = i
    for campo, indice in (("area", INDICE_AREAS), ("tipo", INDICE_TIPOS), ("turno", INDICE_TURNOS)):
        if campo not in m:
            i = mejor_columna(lambda v: resolver(v, indice)[0] is not None)
            if i is not None:
                m[campo] = i
    if "nombre" not in m:
        i = mejor_columna(lambda v: len(v.split()) >= 2 and not any(ch.isdigit() for ch in v), 0.6)
        if i is None:                                                     # lista de nombres de una sola palabra
            i = mejor_columna(lambda v: re.sub(r"[ .,]", "", v).isalpha() and not parse_dias(v), 0.6)
        if i is not None:
            m["nombre"] = i
    return m


# ───────────────────────────── Resultado del análisis ─────────────────────────────

@dataclass
class Fila:
    n: int
    nombre: str
    area: str
    tipo: str
    turno: str
    turnos: list
    errores: list


@dataclass
class Decision:
    """Algo dudoso que el usuario puede confirmar o corregir con un desplegable."""
    clave: str
    titulo: str
    detalle: str
    opciones: list       # [(valor, etiqueta)]
    valor: str
    afectados: int = 0


@dataclass
class DocenteImp:
    nombre: str
    id: int = None
    estado: str = "existente"       # nuevo | actualiza | existente | omitido
    area: str = ""
    tipo: str = ""
    turno: str = ""
    cambios: list = field(default_factory=list)
    turnos_nuevos: list = field(default_factory=list)
    turnos_quitar: list = field(default_factory=list)      # [(turno, id_horario)]
    turnos_iguales: int = 0
    avisos: list = field(default_factory=list)
    nota: str = ""


@dataclass
class Resultado:
    docentes: list = field(default_factory=list)
    decisiones: list = field(default_factory=list)
    omitidas: list = field(default_factory=list)
    problema: str = ""
    turnos_ausentes: int = 0
    _idx: dict = field(default_factory=dict, repr=False)

    def _cuenta(self, estado):
        return sum(1 for d in self.docentes if d.estado == estado)

    nuevos = property(lambda s: s._cuenta("nuevo"))
    actualizados = property(lambda s: s._cuenta("actualiza"))
    omitidos = property(lambda s: s._cuenta("omitido"))
    turnos_nuevos = property(lambda s: sum(len(d.turnos_nuevos) for d in s.docentes))
    turnos_quitados = property(lambda s: sum(len(d.turnos_quitar) for d in s.docentes))
    turnos_iguales = property(lambda s: sum(d.turnos_iguales for d in s.docentes))
    cambios = property(lambda s: s.nuevos + s.actualizados + s.turnos_nuevos + s.turnos_quitados)


_TITULOS = {"dr", "dra", "ing", "inga", "lic", "licda", "mtro", "mtra", "mc", "m", "c", "prof", "profa", "arq",
            "maestro", "maestra", "doctor", "doctora", "ingeniero", "licenciado"}


def clave_nombre(nombre):
    """Igual para 'Pérez López, Juan' que para 'Dr. juan  perez lopez': sin acentos, títulos, mayúsculas ni orden."""
    palabras = [p for p in normalizar(nombre).split() if p not in _TITULOS]
    return " ".join(sorted(palabras or normalizar(nombre).split()))


def _formato_nombre(nombre):
    nombre = " ".join(nombre.split())
    return nombre.title() if nombre.islower() or nombre.isupper() else nombre


# ───────────────────────────── Importación ─────────────────────────────

class Importacion:
    MODOS = {
        "agregar": "Agregar solo los turnos nuevos y conservar los que ya tiene",
        "reemplazar": "Reemplazar: dejar su horario igual al archivo (se eliminan los turnos que no aparezcan en él)",
    }

    def __init__(self, ruta):
        self.ruta = ruta
        self.archivo = os.path.basename(ruta)
        raw = {n: df for n, df in leer_hojas(ruta).items() if not df.empty}
        self._tablas = {n: _construir_tabla(n, df) for n, df in raw.items()}
        self._tablas = {n: t for n, t in self._tablas.items() if any(any(f) for f in t.filas)}
        if not self._tablas:
            raise ValueError("El archivo no tiene datos para importar.")
        self.modo = "agregar"
        self.actualizar_datos = True          # ¿cambiar Área/Tipo/Turno de docentes que ya existen?
        self.decisiones = {}
        self._cache = {}
        self._cargar_bd()
        self.usar_hoja(self._mejor_hoja())

    # -- datos actuales del sistema
    def _cargar_bd(self):
        self.existentes = {clave_nombre(p["nombre"]): p for p in db.obtener_profesores()}
        self.horarios_bd = defaultdict(dict)
        for h in db.obtener_todos_los_horarios():
            self.horarios_bd[h["id_profesor"]][(h["id_dia"], h["hora_entrada"], h["hora_salida"])] = h["id_horario"]

    # -- hoja y columnas
    @property
    def hojas(self):
        return list(self._tablas)

    @property
    def columnas(self):
        return self.tabla.encabezados

    def etiqueta_columna(self, i):
        """Título de la columna más un ejemplo de su contenido, para reconocerla aunque no tenga encabezado."""
        ejemplo = next((f[i] for f in self.tabla.filas if f[i]), "")
        return f"{self.tabla.encabezados[i]} · ej. {ejemplo[:18]}" if ejemplo else self.tabla.encabezados[i]

    def _cols_dia(self, t):
        return {i: _dia_de_encabezado(h) for i, h in enumerate(t.encabezados) if _dia_de_encabezado(h)}

    def _mejor_hoja(self):
        def puntaje(nombre):
            t = self._tablas[nombre]
            m = _detectar_mapeo(t, self._cols_dia(t))
            return len(m) + (10 if "nombre" in m else 0)
        return max(self._tablas, key=lambda n: (puntaje(n), -list(self._tablas).index(n)))

    def usar_hoja(self, nombre):
        self.tabla = self._tablas[nombre]
        cols = self._cols_dia(self.tabla)
        self.cols_dia = cols if len(cols) >= 2 else {}
        self.mapeo = _detectar_mapeo(self.tabla, self.cols_dia)
        self._reparsear()

    def mapear(self, campo, indice):
        """Corrección manual: usa la columna `indice` como `campo` (None = ninguna)."""
        self.mapeo.pop(campo, None)
        if indice is not None:
            self.mapeo = {c: i for c, i in self.mapeo.items() if i != indice}
            self.mapeo[campo] = indice
        self._reparsear()

    @property
    def ancho(self):
        return bool(self.cols_dia) and "dia" not in self.mapeo

    @property
    def hay_horarios(self):
        return self.ancho or any(c in self.mapeo for c in ("dia", "entrada", "salida", "horario"))

    @property
    def descripcion(self):
        if self.ancho:
            return "una columna por día (" + ", ".join(DIAS_CORTO[d] for d in self.cols_dia.values()) + ")"
        if self.hay_horarios:
            return "una fila por turno"
        return "solo lista de docentes"

    # -- interpretación fila por fila (no depende de las decisiones del usuario)
    def _reparsear(self):
        self.decisiones = {}
        t, m = self.tabla, self.mapeo
        idx_horario = list(self.cols_dia) if self.ancho else [m[c] for c in ("dia", "entrada", "salida", "horario") if c in m]
        celda = lambda fila, campo: fila[m[campo]] if campo in m else ""
        self._filas, previa = [], None
        for i, fila in enumerate(t.filas):
            if not any(fila):
                continue
            nombre, area, tipo, turno = celda(fila, "nombre"), celda(fila, "area"), celda(fila, "tipo"), celda(fila, "turno")
            if not nombre and previa and any(fila[j] for j in idx_horario):        # celdas combinadas de Excel
                nombre, area, tipo, turno = previa.nombre, area or previa.area, tipo or previa.tipo, turno or previa.turno
            turnos, errores = self._turnos(fila, celda)
            self._filas.append(Fila(i + t.fila0, nombre, area, tipo, turno, turnos, errores))
            previa = self._filas[-1]

    def _turnos(self, fila, celda):
        turnos, errores = [], []

        def agregar(dia, entrada, salida):
            if entrada >= salida:
                errores.append(f"{NOMBRE_DIA[dia]} {entrada}–{salida}: la salida debe ser posterior a la entrada")
            else:
                turnos.append((dia, entrada, salida))

        if self.ancho:
            for i, dia in self.cols_dia.items():
                if not fila[i]:
                    continue
                rangos = parse_rangos(fila[i])
                if not rangos:
                    errores.append(f"«{fila[i]}» en la columna {self.tabla.encabezados[i]} no parece un horario (ej. 07:00-12:00)")
                for a, b in rangos:
                    agregar(dia, a, b)
            return turnos, errores

        dia_raw, ent_raw, sal_raw, rango_raw = (celda(fila, c) for c in ("dia", "entrada", "salida", "horario"))
        if not any((dia_raw, ent_raw, sal_raw, rango_raw)):
            return turnos, errores
        dias = parse_dias(dia_raw) if dia_raw else []
        if not dias:
            errores.append(f"día no reconocido: «{dia_raw}»" if dia_raw else "falta el día del turno")
            return turnos, errores
        no_admitidos = [NOMBRE_DIA[d] for d in dias if d > 5]
        if no_admitidos:
            errores.append(f"{', '.join(no_admitidos)}: solo se manejan turnos de lunes a viernes")
        dias = [d for d in dias if d <= 5]
        if ent_raw or sal_raw:
            a, b = parse_hora(ent_raw), parse_hora(sal_raw)
            if not a or not b:
                malo = ent_raw if not a else sal_raw
                errores.append(f"hora no válida: «{malo}»" if malo else "falta la hora de entrada o de salida")
                return turnos, errores
            rangos = [(a, b)]
        else:
            rangos = parse_rangos(rango_raw)
            if not rangos:
                errores.append(f"no entendí el horario «{rango_raw}» (ej. 07:00-12:00)")
        for d in dias:
            for a, b in rangos:
                agregar(d, a, b)
        return turnos, errores

    # -- análisis contra la base de datos (sin escribir nada)
    def _decision(self, res, clave, titulo, detalle, opciones, sugerido):
        dec = res._idx.get(clave)
        if dec is None:
            valor = self.decisiones.get(clave, sugerido)
            if valor not in [v for v, _ in opciones]:
                valor = sugerido
            dec = res._idx[clave] = Decision(clave, titulo, detalle, opciones, valor)
            res.decisiones.append(dec)
        dec.afectados += 1
        return dec

    def _valor_catalogo(self, res, campo, raw, indice, catalogo, nuevo):
        """Área/Tipo/Turno final: reconoce alias y typos; lo dudoso o desconocido se convierte en decisión."""
        opciones = [(n, n) for n in catalogo]
        if not raw:
            if not nuevo or campo == "turno":          # el turno faltante se deduce del horario
                return None
            dec = self._decision(res, f"falta:{campo}", f"Docentes nuevos sin {ETIQUETAS.get(campo, campo.title())}",
                                 "{n} docente(s) nuevo(s) no traen este dato. Elige uno para todos o no los importes.",
                                 opciones + [("omitir", "No importar a estos docentes")], "omitir")
        else:
            canon, seguro = self._resolver(campo, raw, indice)
            if seguro:
                return canon
            detalle = (f"Interpreté «{raw}» como «{canon}» ({{n}} docente(s)). ¿Es correcto?" if canon
                       else f"No reconozco «{raw}» ({{n}} docente(s)). Elige a cuál corresponde.")
            dec = self._decision(res, f"{campo}:{normalizar(raw)}", f"{ETIQUETAS.get(campo, campo.title())} «{raw}»", detalle,
                                 opciones + [("omitir", "No usar este dato")], canon or "omitir")
        return None if dec.valor == "omitir" else dec.valor

    def _resolver(self, campo, raw, indice):
        if (campo, raw) not in self._cache:
            self._cache[(campo, raw)] = resolver(raw, indice)
        return self._cache[(campo, raw)]

    def _posible_coincidencia(self, res, clave, nombre):
        cerca = get_close_matches(clave, list(self.existentes), n=1, cutoff=0.86)
        if not cerca:
            return None
        ex = self.existentes[cerca[0]]
        dec = self._decision(res, f"sim:{clave}", f"«{nombre}» se parece a «{ex['nombre']}»",
                             "Los nombres no coinciden exactamente. ¿Es la misma persona?",
                             [("usar", f"Es la misma persona ({ex['nombre']})"), ("nuevo", "Es otra persona (crear nuevo)")], "usar")
        return ex if dec.valor == "usar" else None

    def analizar(self):
        res = Resultado()
        if "nombre" not in self.mapeo:
            res.problema = "No encontré la columna con los nombres de los docentes. Indícame cuál es en «Ajustar columnas»."
            return res

        docs = {}
        for f in self._filas:
            if not f.nombre:
                res.omitidas.append(f"Fila {f.n}: falta el nombre del docente")
                continue
            d = docs.setdefault(clave_nombre(f.nombre), {"nombre": _formato_nombre(f.nombre), "area": "", "tipo": "", "turno": "", "turnos": []})
            d["area"], d["tipo"], d["turno"] = d["area"] or f.area, d["tipo"] or f.tipo, d["turno"] or f.turno
            d["turnos"].extend(f.turnos)
            res.omitidas.extend(f"Fila {f.n}: {e}" for e in f.errores)

        agregados = defaultdict(set)
        for clave, d in docs.items():
            prof = self.existentes.get(clave) or self._posible_coincidencia(res, clave, d["nombre"])
            nuevo = prof is None
            turnos = list(dict.fromkeys(d["turnos"]))
            if nuevo or self.actualizar_datos:
                area = self._valor_catalogo(res, "area", d["area"], INDICE_AREAS, AREAS, nuevo)
                tipo = self._valor_catalogo(res, "tipo", d["tipo"], INDICE_TIPOS, TIPOS, nuevo)
                turno = self._valor_catalogo(res, "turno", d["turno"], INDICE_TURNOS, TURNOS, nuevo)
            else:
                area = tipo = turno = None
            
            di = DocenteImp(prof["nombre"] if prof else d["nombre"], prof["id_profesor"] if prof else None)
            res.docentes.append(di)

            if nuevo:
                if not area or not tipo:
                    di.estado = "omitido"
                    di.nota = f"No se importa: falta {'el Área' if not area else 'el Tipo'}" + (f" (y {len(turnos)} turno(s))" if turnos else "")
                    continue
                di.estado, di.area, di.tipo, di.turno = "nuevo", area, tipo, turno or inferir_turno(turnos) or "Matutino"
            else:
                di.area = area or prof["area"]
                di.tipo = tipo or prof["tipo"]
                di.turno = turno or prof.get("turno", "Matutino")
                
                if di.area != prof["area"]:
                    di.cambios.append(f"Área: {prof['area']} → {di.area}")
                if di.tipo != prof["tipo"]:
                    di.cambios.append(f"Tipo: {prof['tipo']} → {di.tipo}")
                if di.turno != prof.get("turno", "Matutino"):
                    di.cambios.append(f"Turno: {prof.get('turno', 'Matutino')} → {di.turno}")
                    
                di.estado = "actualiza" if di.cambios else "existente"

            actuales = self.horarios_bd.get(di.id, {})
            di.turnos_nuevos = [t for t in turnos if t not in actuales and t not in agregados[di.id]]
            agregados[di.id].update(di.turnos_nuevos)
            di.turnos_iguales = len(turnos) - len(di.turnos_nuevos)
            if turnos:
                ausentes = [(t, hid) for t, hid in actuales.items() if t not in turnos]
                res.turnos_ausentes += len(ausentes)
                if self.modo == "reemplazar":
                    di.turnos_quitar = ausentes
            quedan = sorted((set(actuales) - {t for t, _ in di.turnos_quitar}) | set(di.turnos_nuevos))
            for a, b in zip(quedan, quedan[1:]):
                if a[0] == b[0] and b[1] < a[2] and (a in di.turnos_nuevos or b in di.turnos_nuevos):
                    di.avisos.append(f"{texto_turno(a)} se traslapa con {texto_turno(b)}")

        for dec in res.decisiones:
            dec.detalle = dec.detalle.replace("{n}", str(dec.afectados))
        return res

    # -- aplicar
    def aplicar(self, res):
        docentes = [
            {"id": d.id, "nombre": d.nombre, "area": d.area, "tipo": d.tipo, "turno": d.turno,
             "actualizar": d.estado == "actualiza",
             "turnos": d.turnos_nuevos, "quitar": [hid for _, hid in d.turnos_quitar]}
            for d in res.docentes
            if d.estado in ("nuevo", "actualiza") or (d.estado == "existente" and (d.turnos_nuevos or d.turnos_quitar))
        ]
        db.aplicar_cambios(docentes)
        lineas = []
        if res.nuevos:
            lineas.append(f"✅ {res.nuevos} docente(s) nuevo(s)")
        if res.actualizados:
            lineas.append(f"🔄 {res.actualizados} docente(s) actualizado(s)")
        if res.turnos_nuevos:
            lineas.append(f"🗓 {res.turnos_nuevos} turno(s) agregado(s)")
        if res.turnos_quitados:
            lineas.append(f"➖ {res.turnos_quitados} turno(s) quitado(s)")
        return "\n".join(lineas) or "Todo estaba al día."