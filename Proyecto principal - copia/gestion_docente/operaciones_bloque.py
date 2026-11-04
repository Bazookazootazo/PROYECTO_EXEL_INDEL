"""
Operaciones en bloque del CRUD (selección múltiple).

Regla de oro: aquí solo viven los cambios HOMOGÉNEOS (la misma orden para todos los
seleccionados). Lo heterogéneo (horarios distintos por persona) se hace con la importación
desde Excel. Ambos mundos escriben por la misma puerta: database.aplicar_cambios().

Cada operación sigue el mismo ciclo que la importación:
    planificar_*()  ->  Plan (vista previa, NO toca la base)  ->  aplicar(plan)  (una transacción)
"""
import logging
import os
from collections import defaultdict
from dataclasses import dataclass, field
from logging.handlers import RotatingFileHandler
from utilerias import database as db
from gestion_docente.catalogos import NOMBRE_DIA
from gestion_docente.importador import parse_hora, texto_turno

# ───────────────────────────── Bitácora ─────────────────────────────
# Cada operación (y cada error, con su traza completa) queda registrada para poder rastrear qué pasó.

log = logging.getLogger("gestion_docente")
if not log.handlers:
    log.setLevel(logging.INFO)
    try:
        _h = RotatingFileHandler(os.path.join(os.path.dirname(os.path.abspath(__file__)), "bitacora.log"),
                                 maxBytes=500_000, backupCount=2, encoding="utf-8")
        _h.setFormatter(logging.Formatter("%(asctime)s  %(levelname)s  %(message)s"))
        log.addHandler(_h)
    except OSError:                       # carpeta de solo lectura: la app sigue funcionando sin bitácora
        log.addHandler(logging.NullHandler())


class ErrorOperacion(Exception):
    """Error ya traducido a un mensaje comprensible para el usuario."""


def traducir_error(e):
    errno = getattr(e, "errno", None)
    if errno in (2003, 2006, 2013, 2055):
        return "Se perdió la conexión con la base de datos. Verifica que MySQL (XAMPP) esté encendido e inténtalo de nuevo."
    if errno in (1205, 1213):
        return "La base de datos estaba ocupada con otra operación. Inténtalo de nuevo en unos segundos."
    if errno == 1451:
        return "Hay registros de otras partes del sistema que dependen de lo que se intentó eliminar."
    if errno == 1452:
        return "Alguno de los docentes seleccionados ya no existe (¿lo eliminó otra persona?). Actualiza la lista e inténtalo de nuevo."
    return f"Ocurrió un problema inesperado: {e}"


# ───────────────────────────── Modelo ─────────────────────────────

@dataclass
class Linea:
    icono: str
    texto: str
    detalle: list = field(default_factory=list)       # nombres / explicaciones
    nivel: str = "ok"                                 # ok | info | aviso (aviso = algo NO se aplicará)
    lista: bool = False                               # True = mostrar el detalle uno por línea


@dataclass
class Plan:
    accion: str
    lineas: list = field(default_factory=list)
    payload: list = field(default_factory=list)       # para database.aplicar_cambios
    nombres: dict = field(default_factory=dict)       # {id: nombre} (acción "eliminar")
    cambios: int = 0
    resumen: str = ""                                 # frase corta del impacto (para confirmar)
    error: str = ""                                   # falta/errónea alguna captura: impide aplicar

    @property
    def aplicable(self):
        return not self.error and self.cambios > 0

    @property
    def avisos(self):
        return [ln for ln in self.lineas if ln.nivel == "aviso"]


@dataclass
class Resultado:
    titulo: str
    mensaje: str
    parcial: bool = False                             # True si algo de lo pedido NO se aplicó


def _nombre(p):
    return p["nombre"].title()


def cargar_horarios(profesores):
    """{id_profesor: [horarios]} solo de los docentes dados (una sola consulta)."""
    ids = {p["id_profesor"] for p in profesores}
    por_prof = defaultdict(list)
    for h in db.obtener_todos_los_horarios():
        if h["id_profesor"] in ids:
            por_prof[h["id_profesor"]].append(h)
    return por_prof


def _entrada_payload(p, **extra):
    return {"id": p["id_profesor"], "nombre": p["nombre"], "area": p["area"], "tipo": p["tipo"],
            "actualizar": False, "turnos": [], "quitar": [], **extra}


# ───────────────────────────── Turnos: validación y detección de choques ─────────────────────────────

def validar_turno(entrada, salida):
    """Normaliza lo tecleado ('7', '0700', '07:00') a ('07:00', '12:00'). ValueError con mensaje claro si no sirve."""
    if not str(entrada).strip() or not str(salida).strip():
        raise ValueError("Ingresa la hora de entrada y de salida (Ej: 08:00 y 16:00).")
    e, s = parse_hora(entrada), parse_hora(salida)
    if not e or not s:
        raise ValueError(f"La hora «{entrada if not e else salida}» no es válida. Usa el formato 24 horas, por ejemplo 07:00.")
    if e >= s:
        raise ValueError(f"La salida ({s}) debe ser posterior a la entrada ({e}).")
    return e, s


def revisar_turno(existentes, id_dia, entrada, salida):
    """Compara un turno nuevo con lo que el docente ya tiene: ('nuevo'|'repetido'|'traslape', turno_existente|None)."""
    choque = None
    for h in existentes:
        if h["id_dia"] != id_dia:
            continue
        if (h["hora_entrada"], h["hora_salida"]) == (entrada, salida):
            return "repetido", h
        if h["hora_entrada"] < salida and h["hora_salida"] > entrada:
            choque = choque or h
    return ("traslape", choque) if choque else ("nuevo", None)

# ───────────────────────────── Planificadores (puros: no tocan la base) ─────────────────────────────

# En operaciones_bloque.py

def planificar_datos(profesores, area=None, tipo=None, turno=None):
    plan = Plan("datos")
    if not area and not tipo and not turno:
        plan.error = "Elige al menos un valor nuevo (Área, Tipo o Turno)."
        return plan

    cambios, sin_cambio = defaultdict(list), []
    for p in profesores:
        nueva_area = area or p["area"]
        nuevo_tipo = tipo or p["tipo"]
        nuevo_turno = turno or p.get("turno", "Matutino")
        
        if (nueva_area, nuevo_tipo, nuevo_turno) == (p["area"], p["tipo"], p.get("turno", "Matutino")):
            sin_cambio.append(_nombre(p))
            continue
            
        if nueva_area != p["area"]:
            cambios[f"Área: {p['area']} → {nueva_area}"].append(_nombre(p))
        if nuevo_tipo != p["tipo"]:
            cambios[f"Tipo: {p['tipo']} → {nuevo_tipo}"].append(_nombre(p))
        if nuevo_turno != p.get("turno", "Matutino"):
            cambios[f"Turno: {p.get('turno', 'Matutino')} → {nuevo_turno}"].append(_nombre(p))
            
        plan.payload.append(_entrada_payload(p, area=nueva_area, tipo=nuevo_tipo, turno=nuevo_turno, actualizar=True))

    for etiqueta, nombres in cambios.items():
        plan.lineas.append(Linea("🔄", f"{etiqueta}  ({len(nombres)})", nombres))
    if sin_cambio:
        plan.lineas.append(Linea("✅", f"{len(sin_cambio)} ya tienen esos valores (sin cambio)", sin_cambio, "info"))
    plan.cambios = len(plan.payload)
    plan.resumen = f"Se actualizarán {plan.cambios} docente(s)."
    return plan


def planificar_asignacion(profesores, horarios, dias, entrada, salida, permitir_traslape=False):
    plan = Plan("asignar")
    if not dias:
        plan.error = "Marca al menos un día."
        return plan
    try:
        entrada, salida = validar_turno(entrada, salida)
    except ValueError as e:
        plan.error = str(e)
        return plan

    agregar, repetidos, choques = defaultdict(list), [], []
    for p in profesores:
        for dia in sorted(dias):
            estado, existente = revisar_turno(horarios.get(p["id_profesor"], []), dia, entrada, salida)
            if estado == "repetido":
                repetidos.append(f"{_nombre(p)} — {NOMBRE_DIA[dia]}")
                continue
            if estado == "traslape":
                choques.append(f"{_nombre(p)} — {NOMBRE_DIA[dia]}: ya tiene {existente['hora_entrada']}–{existente['hora_salida']}")
                if not permitir_traslape:
                    continue
            agregar[p["id_profesor"]].append((dia, entrada, salida))

    por_id = {p["id_profesor"]: p for p in profesores}
    for id_prof, turnos in agregar.items():
        plan.payload.append(_entrada_payload(por_id[id_prof], turnos=turnos))
    n_turnos = sum(len(t) for t in agregar.values())

    if n_turnos:
        dias_txt = ", ".join(NOMBRE_DIA[d] for d in sorted(dias))
        plan.lineas.append(Linea("➕", f"Se agregará {entrada}–{salida} ({dias_txt}) a {len(agregar)} docente(s): {n_turnos} turno(s)",
                                 [_nombre(por_id[i]) for i in agregar]))
    if choques:
        if permitir_traslape:
            plan.lineas.append(Linea("⚠️", f"Se agregarán aunque se traslapan con otro turno ({len(choques)})", choques, "info", lista=True))
        else:
            plan.lineas.append(Linea("⚠️", f"No se agregarán por traslape con otro turno ({len(choques)})", choques, "aviso", lista=True))
    if repetidos:
        plan.lineas.append(Linea("✅", f"Ya tenían ese turno ({len(repetidos)})", repetidos, "info", lista=True))
    plan.cambios = n_turnos
    plan.resumen = f"Se agregarán {n_turnos} turno(s) a {len(agregar)} docente(s)."
    return plan


def turnos_en_seleccion(profesores, horarios):
    """[(clave, [docentes con ese turno])] ordenado por día y hora; clave = (id_dia, entrada, salida)."""
    por_turno = defaultdict(list)
    for p in profesores:
        for h in horarios.get(p["id_profesor"], []):
            por_turno[(h["id_dia"], h["hora_entrada"], h["hora_salida"])].append(_nombre(p))
    return sorted(por_turno.items())


def planificar_quitar(profesores, horarios, claves):
    plan = Plan("quitar")
    if not claves:
        plan.error = "Marca al menos un turno para quitar."
        return plan

    por_turno = defaultdict(list)
    for p in profesores:
        ids = []
        for h in horarios.get(p["id_profesor"], []):
            clave = (h["id_dia"], h["hora_entrada"], h["hora_salida"])
            if clave in claves:
                ids.append(h["id_horario"])
                por_turno[clave].append(_nombre(p))
        if ids:
            plan.payload.append(_entrada_payload(p, quitar=ids))

    for clave in sorted(por_turno):
        plan.lineas.append(Linea("✂️", f"{texto_turno(clave)}  ({len(por_turno[clave])} docente(s))", por_turno[clave]))
    plan.cambios = sum(len(d["quitar"]) for d in plan.payload)
    plan.resumen = f"Se eliminarán {plan.cambios} turno(s) de {len(plan.payload)} docente(s)."
    return plan


def planificar_eliminar(profesores, horarios):
    plan = Plan("eliminar")
    plan.nombres = {p["id_profesor"]: _nombre(p) for p in profesores}
    turnos = sum(len(horarios.get(p["id_profesor"], [])) for p in profesores)
    plan.lineas.append(Linea("🗑", f"Se eliminarán {len(profesores)} docente(s)",
                             [f"{_nombre(p)} — {len(horarios.get(p['id_profesor'], []))} turno(s)" for p in profesores], lista=True))
    if turnos:
        plan.lineas.append(Linea("✂️", f"Se eliminarán también sus {turnos} turno(s) de horario", [], "info"))
    plan.lineas.append(Linea("ℹ️", "Si algún docente tiene registros en otras partes del sistema (por ejemplo, asistencias) "
                                   "no se eliminará, y se te indicará cuál.", [], "info"))
    plan.cambios = len(profesores)
    plan.resumen = f"Se eliminarán {len(profesores)} docente(s) y {turnos} turno(s)."
    return plan

# ───────────────────────────── Aplicar ─────────────────────────────

def _notas_omitidos(plan):
    notas = []
    for ln in plan.avisos:
        notas.append(f"• {ln.texto}")
        notas += [f"     – {d}" for d in ln.detalle[:6]]
        if len(ln.detalle) > 6:
            notas.append(f"     – … y {len(ln.detalle) - 6} más")
    return notas


def aplicar(plan):
    """Ejecuta el plan (una transacción) y devuelve un Resultado con exactamente lo que pasó."""
    try:
        if plan.accion == "eliminar":
            eliminados, bloqueados = db.eliminar_profesores_en_bloque(list(plan.nombres))
            partes = [f"✅ {len(eliminados)} docente(s) eliminado(s)."] if eliminados else []
            notas = [f"• {plan.nombres[i]} — {motivo}; no se eliminó." for i, motivo in bloqueados.items()]
            log.info("eliminar docentes=%s eliminados=%s bloqueados=%s", list(plan.nombres), eliminados, bloqueados)
            if not eliminados:
                partes = ["No se eliminó ningún docente."]
            return _resultado("Eliminación de docentes", partes, notas)

        stats = db.aplicar_cambios(plan.payload)
        log.info("accion=%s docentes=%s stats=%s", plan.accion, [d["id"] for d in plan.payload], stats)
    except Exception as e:
        log.exception("fallo en acción en bloque '%s' (docentes: %s)", plan.accion, [d.get("id") for d in plan.payload] or list(plan.nombres))
        raise ErrorOperacion(traducir_error(e)) from e

    partes = {
        "datos": [f"✅ {stats['docentes_actualizados']} docente(s) actualizado(s)."],
        "asignar": [f"✅ {stats['turnos_agregados']} turno(s) agregado(s)."],
        "quitar": [f"✅ {stats['turnos_quitados']} turno(s) quitado(s)."],
    }[plan.accion]
    titulo = {"datos": "Datos actualizados", "asignar": "Turno asignado", "quitar": "Turnos quitados"}[plan.accion]
    return _resultado(titulo, partes, _notas_omitidos(plan))


def _resultado(titulo, partes, notas):
    mensaje = "\n".join(partes)
    if notas:
        mensaje += "\n\nNo se aplicó a:\n" + "\n".join(notas)
    return Resultado(titulo, mensaje, parcial=bool(notas))