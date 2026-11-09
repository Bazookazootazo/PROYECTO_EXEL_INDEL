import os
import calendar
from bisect import bisect_right
from datetime import datetime, date, timedelta
import customtkinter as ctk
from tkinter import filedialog, messagebox
import mysql.connector

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.drawing.image import Image as OpenpyxlImage

from utilerias.paleta_colores import colores, fuentes
from utilerias.messagebox_variados import mostrar_advertencia, mostrar_error, mostrar_exito, mostrar_pregunta

# Minutos de tolerancia
TOLERANCIA_MIN = 10

# Dos horarios de un mismo día separados por menos de estos minutos cuentan como un solo horario continuo
HUECO_MINIMO_MIN = 60


def _a_hora(valor):
    """MySQL entrega TIME como timedelta; se convierte a hora del día."""
    return (datetime.min + valor).time() if isinstance(valor, timedelta) else valor


def _minutos(hora):
    return hora.hour * 60 + hora.minute + hora.second / 60


def agrupar_turnos(turnos):
    unidos = []
    for entrada, salida in sorted((_a_hora(e), _a_hora(s)) for e, s in turnos):
        if unidos and _minutos(entrada) - _minutos(unidos[-1][1]) < HUECO_MINIMO_MIN:
            unidos[-1] = (unidos[-1][0], max(unidos[-1][1], salida))
        else:
            unidos.append((entrada, salida))
    return unidos


def evaluar_horario(dia, hora_entrada, hora_salida, checadas):
    if not checadas:
        return "FI", "FI", 0

    dt_entrada_esp = datetime.combine(dia, _a_hora(hora_entrada))
    dt_salida_esp = datetime.combine(dia, _a_hora(hora_salida))
    midpoint = dt_entrada_esp + (dt_salida_esp - dt_entrada_esp) / 2

    if len(checadas) == 1:
        p = checadas[0]
        primera_ch, ultima_ch = (p, None) if p <= midpoint else (None, p)
    else:
        primera_ch, ultima_ch = checadas[0], checadas[-1]

    retardo = 0
    if primera_ch:
        primera_min = primera_ch.replace(second=0, microsecond=0)
        limite_tolerancia = dt_entrada_esp + timedelta(minutes=TOLERANCIA_MIN)
        if primera_min <= limite_tolerancia:
            val_entrada = primera_ch.strftime("%H:%M")
        else:
            retardo = int((primera_min - limite_tolerancia).total_seconds() // 60)
            val_entrada = f"{primera_ch.strftime('%H:%M')} R ({retardo}m)"
    else:
        val_entrada = "FIE"

    val_salida = ultima_ch.strftime("%H:%M") if ultima_ch else "FIS"
    return val_entrada, val_salida, retardo


def celdas_del_dia(dia, turnos, checadas):
    if not turnos:
        if not checadas:
            return [("N/A", "N/A", 0)]
        if len(checadas) > 1:
            return [(checadas[0].strftime("%H:%M"), checadas[-1].strftime("%H:%M"), 0)]
        p = checadas[0]       
        return [(p.strftime("%H:%M"), "N/A", 0) if p.hour < 12 else ("N/A", p.strftime("%H:%M"), 0)]

    horarios_dia = agrupar_turnos(turnos)
    if len(horarios_dia) == 1:
        return [evaluar_horario(dia, *horarios_dia[0], checadas)]

    inicio_dia = datetime.combine(dia, datetime.min.time())
    fronteras = [inicio_dia + timedelta(minutes=(_minutos(a[1]) + _minutos(b[0])) / 2)
                 for a, b in zip(horarios_dia, horarios_dia[1:])]
    grupos = [[] for _ in horarios_dia]
    for p in checadas:
        grupos[bisect_right(fronteras, p)].append(p)
    return [evaluar_horario(dia, entrada, salida, grupo) for (entrada, salida), grupo in zip(horarios_dia, grupos)]


class VentanaSeleccionQuincenaDialog(ctk.CTkToplevel):
    def __init__(self, parent, fecha_inicial_actual=None):
        super().__init__(parent)
        self.parent = parent
        self.title("Seleccionar Inicio de Quincena (15 días)")
        self.geometry("460x520")
        self.configure(fg_color=colores.BG_VENTANA)
        self.resizable(False, False)

        self.focus()
        self.grab_set()

        hoy = datetime.now().date()
        self.fecha_inicio_sel = fecha_inicial_actual if fecha_inicial_actual else date(hoy.year, hoy.month, 1)
        self.fecha_fin_sel = self.fecha_inicio_sel + timedelta(days=14)

        self.anio_vista = self.fecha_inicio_sel.year
        self.mes_vista = self.fecha_inicio_sel.month

        self.resultado_inicio = None
        self.resultado_fin = None

        self._crear_interfaz()
        self.actualizar_calendario()

    def _crear_interfaz(self):
        main_frame = ctk.CTkFrame(master=self, fg_color=colores.BG_PANEL, corner_radius=15)
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)

        lbl_titulo = ctk.CTkLabel(master=main_frame, text="Selección de Quincena Personalizada", font=fuentes.titulo(size=18), text_color=colores.TEXTO_PRIMARIO)
        lbl_titulo.pack(anchor="w", padx=20, pady=(15, 3))

        lbl_sub = ctk.CTkLabel(master=main_frame, text="Haz clic en cualquier día para iniciar el lapso de 15 días.", font=fuentes.cuerpo(size=12), text_color=colores.TEXTO_SECUNDARIO)
        lbl_sub.pack(anchor="w", padx=20, pady=(0, 10))

        self.info_box = ctk.CTkFrame(master=main_frame, fg_color=colores.BG_PANEL_ALT, corner_radius=10)
        self.info_box.pack(fill="x", padx=20, pady=(0, 10))

        self.lbl_rango_txt = ctk.CTkLabel(master=self.info_box, text="", font=fuentes.seccion(size=13), text_color=colores.TEXTO_PRIMARIO)
        self.lbl_rango_txt.pack(pady=8)

        nav_frame = ctk.CTkFrame(master=main_frame, fg_color="transparent")
        nav_frame.pack(fill="x", padx=20, pady=5)

        btn_prev = ctk.CTkButton(master=nav_frame, text="◀ Mes Ant.", width=90, fg_color=colores.NEUTRO, hover_color=colores.NEUTRO_HOVER, command=self.mes_anterior)
        btn_prev.pack(side="left")

        self.lbl_mes_anio = ctk.CTkLabel(master=nav_frame, text="", font=fuentes.seccion(size=15), text_color=colores.TEXTO_PRIMARIO)
        self.lbl_mes_anio.pack(side="left", expand=True)

        btn_next = ctk.CTkButton(master=nav_frame, text="Mes Sig. ▶", width=90, fg_color=colores.NEUTRO, hover_color=colores.NEUTRO_HOVER, command=self.mes_siguiente)
        btn_next.pack(side="right")

        self.cal_frame = ctk.CTkFrame(master=main_frame, fg_color=colores.BG_PANEL_ALT, corner_radius=10)
        self.cal_frame.pack(fill="both", expand=True, padx=20, pady=10)

        btn_action_frame = ctk.CTkFrame(master=main_frame, fg_color="transparent")
        btn_action_frame.pack(fill="x", padx=20, pady=(5, 15))
        btn_action_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(master=btn_action_frame, text="Cancelar", fg_color=colores.NEUTRO, hover_color=colores.NEUTRO_HOVER, height=38, command=self.destroy).grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.btn_aceptar = ctk.CTkButton(master=btn_action_frame, text="Confirmar Quincena", fg_color=colores.EXITO, hover_color=colores.EXITO_HOVER, height=38, command=self.confirmar)
        self.btn_aceptar.grid(row=0, column=1, sticky="ew", padx=(5, 0))

    def mes_anterior(self):
        if self.mes_vista == 1:
            self.mes_vista = 12
            self.anio_vista -= 1
        else:
            self.mes_vista -= 1
        self.actualizar_calendario()

    def mes_siguiente(self):
        hoy = datetime.now().date()
        if self.anio_vista > hoy.year or (self.anio_vista == hoy.year and self.mes_vista >= hoy.month):
            return
        if self.mes_vista == 12:
            self.mes_vista = 1
            self.anio_vista += 1
        else:
            self.mes_vista += 1
        self.actualizar_calendario()

    def seleccionar_dia(self, d_obj):
        self.fecha_inicio_sel = d_obj
        self.fecha_fin_sel = d_obj + timedelta(days=14)
        self.actualizar_calendario()

    def actualizar_calendario(self):
        meses_es = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        self.lbl_mes_anio.configure(text=f"{meses_es[self.mes_vista]} {self.anio_vista}")

        self.lbl_rango_txt.configure(
            text=f"Lapso: {self.fecha_inicio_sel.strftime('%d/%m/%Y')}  ➔  {self.fecha_fin_sel.strftime('%d/%m/%Y')} (15 Días)"
        )

        for widget in self.cal_frame.winfo_children():
            widget.destroy()

        dias_sem = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        for col_idx, d_str in enumerate(dias_sem):
            lbl = ctk.CTkLabel(master=self.cal_frame, text=d_str, font=fuentes.seccion(size=11), text_color=colores.TEXTO_SECUNDARIO, width=45)
            lbl.grid(row=0, column=col_idx, padx=2, pady=2)

        hoy = datetime.now().date()
        if self.fecha_fin_sel > hoy:
            self.btn_aceptar.configure(state="disabled", fg_color=colores.TEXTO_TENUE)
        else:
            self.btn_aceptar.configure(state="normal", fg_color=colores.EXITO)

        matriz_cal = calendar.monthcalendar(self.anio_vista, self.mes_vista)
        for r_idx, semana in enumerate(matriz_cal, start=1):
            for c_idx, dia_val in enumerate(semana):
                if dia_val == 0:
                    lbl_dia = ctk.CTkLabel(master=self.cal_frame, text="", width=45, height=30)
                else:
                    d_obj = date(self.anio_vista, self.mes_vista, dia_val)
                    en_rango = self.fecha_inicio_sel <= d_obj <= self.fecha_fin_sel
                    es_inicio = (d_obj == self.fecha_inicio_sel)
                    es_futuro = d_obj > hoy

                    if es_futuro:
                        fg_color = "transparent"
                        text_color = colores.TEXTO_TENUE
                        state = "disabled"
                    elif es_inicio:
                        fg_color = "#2E7D32"
                        text_color = "#FFFFFF"
                        state = "normal"
                    elif en_rango:
                        fg_color = colores.ACENTO if not (d_obj.weekday() >= 5) else "#7B5B1B"
                        text_color = "#FFFFFF"
                        state = "normal"
                    else:
                        fg_color = colores.BG_VENTANA
                        text_color = colores.TEXTO_PRIMARIO
                        state = "normal"

                    btn_dia = ctk.CTkButton(
                        master=self.cal_frame,
                        text=str(dia_val),
                        width=42,
                        height=30,
                        corner_radius=6,
                        fg_color=fg_color,
                        text_color=text_color,
                        state=state,
                        font=fuentes.cuerpo(size=12),
                        command=lambda d=d_obj: self.seleccionar_dia(d)
                    )
                    btn_dia.grid(row=r_idx, column=c_idx, padx=2, pady=2)

        self.resultado_inicio = self.fecha_inicio_sel
        self.resultado_fin = self.fecha_fin_sel

    def confirmar(self):
        hoy = datetime.now().date()
        if self.resultado_fin > hoy:
            mostrar_advertencia("Fecha Inválida", "El lapso de 15 días no puede terminar en una fecha posterior al día actual.", master=self)
            return
        self.destroy()

    def obtener_fechas(self):
        return self.resultado_inicio, self.resultado_fin


class VentanaExcepcionesDialog(ctk.CTkToplevel):
    def __init__(self, parent, fecha_inicio, fecha_fin, lista_docentes, excepciones_actuales):
        super().__init__(parent)
        self.parent = parent
        self.title("Asignar Días Libres o Circunstancias")
        self.geometry("600x480")
        self.configure(fg_color=colores.BG_VENTANA)
        self.resizable(False, False)

        self.focus()
        self.grab_set()

        self.excepciones = list(excepciones_actuales) 
        self.lista_docentes = ["(Global - Todos los docentes)"] + [d['nombre'] for d in lista_docentes]

        self.dias_disponibles = []
        curr = fecha_inicio
        while curr <= fecha_fin:
            if curr.weekday() < 5: 
                self.dias_disponibles.append(curr.strftime('%d/%m/%Y'))
            curr += timedelta(days=1)

        self._crear_interfaz()

    def _crear_interfaz(self):
        main_frame = ctk.CTkFrame(master=self, fg_color=colores.BG_PANEL, corner_radius=15)
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)

        lbl_titulo = ctk.CTkLabel(master=main_frame, text="Gestión de Excepciones y Días Libres", font=fuentes.titulo(size=18), text_color=colores.TEXTO_PRIMARIO)
        lbl_titulo.pack(anchor="w", padx=20, pady=(20, 10))

        form_frame = ctk.CTkFrame(master=main_frame, fg_color=colores.BG_PANEL_ALT, corner_radius=10)
        form_frame.pack(fill="x", padx=20, pady=10, ipady=10)

        lbl_doc = ctk.CTkLabel(master=form_frame, text="Docente:", font=fuentes.seccion(size=12), text_color=colores.TEXTO_PRIMARIO)
        lbl_doc.grid(row=0, column=0, sticky="w", padx=15, pady=(10, 2))
        self.cb_docente = ctk.CTkComboBox(master=form_frame, values=self.lista_docentes, width=250, height=32)
        self.cb_docente.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 10))
        self.cb_docente.set(self.lista_docentes[0])

        lbl_fec = ctk.CTkLabel(master=form_frame, text="Fecha (Días hábiles del periodo):", font=fuentes.seccion(size=12), text_color=colores.TEXTO_PRIMARIO)
        lbl_fec.grid(row=0, column=1, sticky="w", padx=15, pady=(10, 2))
        
        if self.dias_disponibles:
            self.cb_fecha = ctk.CTkComboBox(master=form_frame, values=self.dias_disponibles, width=180, height=32)
            self.cb_fecha.set(self.dias_disponibles[0])
        else:
            self.cb_fecha = ctk.CTkComboBox(master=form_frame, values=["No hay días hábiles"], width=180, height=32)
            self.cb_fecha.set("No hay días hábiles")
        self.cb_fecha.grid(row=1, column=1, sticky="ew", padx=15, pady=(0, 10))

        lbl_mot = ctk.CTkLabel(master=form_frame, text="Circunstancia / Motivo (ej. Descanso, Permiso):", font=fuentes.seccion(size=12), text_color=colores.TEXTO_PRIMARIO)
        lbl_mot.grid(row=2, column=0, columnspan=2, sticky="w", padx=15, pady=(5, 2))
        
        motivos_sugeridos = ["Descanso", "Permiso", "Comisión", "Incapacidad", "Atención Médica"]
        self.cb_motivo = ctk.CTkComboBox(master=form_frame, values=motivos_sugeridos, width=460, height=32)
        self.cb_motivo.grid(row=3, column=0, columnspan=2, sticky="ew", padx=15, pady=(0, 10))
        self.cb_motivo.set("Descanso")

        btn_agregar = ctk.CTkButton(master=form_frame, text="➕ Agregar Excepción", fg_color=colores.EXITO, hover_color=colores.EXITO_HOVER, command=self.agregar_excepcion, height=32)
        btn_agregar.grid(row=4, column=0, columnspan=2, padx=15, pady=10)

        lbl_lista = ctk.CTkLabel(master=main_frame, text="Excepciones Registradas:", font=fuentes.seccion(size=12), text_color=colores.TEXTO_PRIMARIO)
        lbl_lista.pack(anchor="w", padx=20, pady=(10, 2))

        self.txt_lista = ctk.CTkTextbox(master=main_frame, height=110, font=fuentes.monoespaciada(size=11))
        self.txt_lista.pack(fill="x", padx=20, pady=(0, 10))
        self.actualizar_texto_lista()

        btn_cerrar = ctk.CTkButton(master=main_frame, text="Guardar y Cerrar", fg_color=colores.ACENTO, hover_color=colores.ACENTO_HOVER, command=self.destroy, height=36)
        btn_cerrar.pack(pady=(0, 10))

    def agregar_excepcion(self):
        docente = self.cb_docente.get()
        fecha = self.cb_fecha.get()
        motivo = self.cb_motivo.get().strip()

        if not fecha or fecha == "No hay días hábiles":
            mostrar_advertencia("Advertencia", "No hay fechas disponibles para seleccionar.", master=self)
            return
        if not motivo:
            mostrar_advertencia("Advertencia", "Escribe o selecciona un motivo.", master=self)
            return

        item = (docente, fecha, motivo)
        if item not in self.excepciones:
            self.excepciones.append(item)
            self.actualizar_texto_lista()

    def actualizar_texto_lista(self):
        self.txt_lista.configure(state="normal")
        self.txt_lista.delete("1.0", "end")
        
        texto_lineas = []
        for doc, fec, mot in self.excepciones:
            if doc == "(Global - Todos los docentes)":
                texto_lineas.append(f"{fec} : {mot}")
            else:
                texto_lineas.append(f"{doc} | {fec} : {mot}")
        
        self.txt_lista.insert("1.0", "\n".join(texto_lineas))
        self.txt_lista.configure(state="disabled")

    def obtener_resultado(self):
        texto_lineas = []
        for doc, fec, mot in self.excepciones:
            if doc == "(Global - Todos los docentes)":
                texto_lineas.append(f"{fec}: {mot}")
            else:
                texto_lineas.append(f"{doc} | {fec}: {mot}")
        return "\n".join(texto_lineas)


class VentanaGenerarReporte(ctk.CTkToplevel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

        self.title("Generación de Reportes Quincenales - Control de Acceso")
        self.configure(fg_color=colores.BG_VENTANA)

        self.state('zoomed')
        self.resizable(True, True)

        self.focus()
        self.lift()

        self.excepciones_texto_guardado = ""

        hoy = datetime.now()
        self.fecha_inicio_sel = date(hoy.year, hoy.month, 1)
        self.fecha_fin_sel = self.fecha_inicio_sel + timedelta(days=14)

        self._crear_interfaz()
        self.cargar_areas()

    @staticmethod
    def obtener_conexion_bd():
        return mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="control_asistencia"
        )

    def cargar_areas(self):
        try:
            conn = self.obtener_conexion_bd()
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT a.id_area, a.nombre FROM areas a JOIN profesores p ON p.id_area = a.id_area WHERE a.nombre IS NOT NULL AND a.nombre != '' ORDER BY a.nombre ASC")
            filas = cursor.fetchall()
            areas = [f[1] for f in filas]
            #self.mapa_areas = {f['nombre']: f['id_area'] for f in filas}
            #areas = list(self.mapa_areas.keys())

            if areas:
                self.cb_area.configure(values=areas)
                self.cb_area.set(areas[0])
            else:
                self.cb_area.configure(values=["Sin áreas registradas"])
                self.cb_area.set("Sin áreas registradas")

            cursor.close()
            conn.close()
        except Exception as e:
            mostrar_error("Error BD", f"No se pudieron cargar las áreas:\n{e}", master=self)

    @staticmethod
    def parsear_excepciones(texto_excepciones):
        excepciones_globales = {} 
        excepciones_docente = {}  
        
        if not texto_excepciones:
            return excepciones_globales, excepciones_docente
            
        lineas = texto_excepciones.strip().split('\n')
        for linea in lineas:
            linea = linea.strip()
            if not linea:
                continue
            parts = linea.split('|') if '|' in linea else [linea]
            if len(parts) == 2:
                docente_filtro = parts[0].strip().lower()
                resto = parts[1].strip()
            else:
                docente_filtro = None
                resto = parts[0].strip()
                
            if ':' in resto:
                fecha_str, circunstancia = resto.split(':', 1)
                fecha_str = fecha_str.strip()
                circunstancia = circunstancia.strip()
                try:
                    f_obj = datetime.strptime(fecha_str, '%d/%m/%Y').date()
                    if docente_filtro:
                        excepciones_docente[(docente_filtro, f_obj)] = circunstancia
                    else:
                        excepciones_globales[f_obj] = circunstancia
                except ValueError:
                    continue
        return excepciones_globales, excepciones_docente

    def abrir_selector_quincena(self):
        dialog = VentanaSeleccionQuincenaDialog(self, self.fecha_inicio_sel)
        self.wait_window(dialog)
        if dialog.resultado_inicio and dialog.resultado_fin:
            self.fecha_inicio_sel = dialog.resultado_inicio
            self.fecha_fin_sel = dialog.resultado_fin
            self.lbl_periodo_val.configure(
                text=f"Del {self.fecha_inicio_sel.strftime('%d/%m/%Y')} al {self.fecha_fin_sel.strftime('%d/%m/%Y')} (15 Días)",
                text_color=colores.TEXTO_PRIMARIO
            )

    def abrir_dialogo_excepciones(self):
        area_seleccionada = self.cb_area.get().strip()
        fecha_inicio = self.fecha_inicio_sel
        fecha_fin = self.fecha_fin_sel

        try:
            conn = self.obtener_conexion_bd()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""SELECT p.id_profesor, p.nombre FROM profesores p JOIN areas a ON p.id_area = a.id_area WHERE a.nombre = %s ORDER BY p.nombre ASC""", (area_seleccionada,))
            docentes = cursor.fetchall()
            cursor.close()
            conn.close()
        except Exception:
            docentes = []

        excepciones_actuales = []
        for linea in self.excepciones_texto_guardado.strip().split('\n'):
            if ':' in linea:
                partes = linea.split(':')
                f_s = partes[0].strip()
                m_s = partes[1].strip()
                if '|' in f_s:
                    doc_s, fec_s = f_s.split('|')
                    excepciones_actuales.append((doc_s.strip(), fec_s.strip(), m_s))
                else:
                    excepciones_actuales.append(("(Global - Todos los docentes)", f_s, m_s))

        dialog = VentanaExcepcionesDialog(self, fecha_inicio, fecha_fin, docentes, excepciones_actuales)
        self.wait_window(dialog)
        self.excepciones_texto_guardado = dialog.obtener_resultado()
        
        if self.excepciones_texto_guardado.strip():
            self.lbl_estado_excepciones.configure(text=f"✅ {len(self.excepciones_texto_guardado.splitlines())} excepción(es) asignada(s).", text_color=colores.EXITO)
        else:
            self.lbl_estado_excepciones.configure(text="Sin excepciones asignadas.", text_color=colores.TEXTO_SECUNDARIO)

    def cargar_datos_reporte(self, area, fecha_inicio, fecha_fin, solo_asignatura=False):
        conn = self.obtener_conexion_bd()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT p.id_profesor, p.nombre 
                FROM profesores p 
                JOIN areas a ON p.id_area = a.id_area 
                WHERE a.nombre = %s 
                ORDER BY p.nombre ASC
            """, (area,))
            docentes = cursor.fetchall()
            if not docentes:
                return [], {}, {}

            ids = [d['id_profesor'] for d in docentes]
            marcadores = ",".join(["%s"] * len(ids))

            horarios = {}
            cursor.execute(f"SELECT id_profesor, id_dia, hora_entrada, hora_salida FROM horarios_docentes "
                           f"WHERE id_profesor IN ({marcadores}) ORDER BY id_horario", ids)
            for fila in cursor.fetchall():
                horarios.setdefault((fila['id_profesor'], fila['id_dia']), []).append((fila['hora_entrada'], fila['hora_salida']))

            checadas_por_dia = {}
            cursor.execute(f"SELECT id_profesor, fecha_hora FROM checadas "
                           f"WHERE id_profesor IN ({marcadores}) AND fecha_hora BETWEEN %s AND %s "
                           f"ORDER BY id_profesor, fecha_hora ASC",
                           ids + [datetime.combine(fecha_inicio, datetime.min.time()), datetime.combine(fecha_fin, datetime.max.time())])
            for fila in cursor.fetchall():
                checadas_por_dia.setdefault((fila['id_profesor'], fila['fecha_hora'].date()), []).append(fila['fecha_hora'])

            return docentes, horarios, checadas_por_dia
        finally:
            conn.close()

    def generar_excel_quincenal(self, solo_asignatura=False):
        area_seleccionada = self.cb_area.get().strip()
        if not solo_asignatura and (not area_seleccionada or area_seleccionada == "Sin áreas registradas"):
            mostrar_advertencia("Advertencia", "Selecciona un área válida.", master=self)
            return

        fecha_inicio = self.fecha_inicio_sel
        fecha_fin = self.fecha_fin_sel

        excepciones_globales, excepciones_docente = self.parsear_excepciones(self.excepciones_texto_guardado)

        if solo_asignatura:
            titulo_reporte_excel = "Control Quincenal de Asistencia - Profesores de Asignatura (Global)"
            nombre_defecto = f"Reporte_Asistencia_Profesores_de_Asignatura_{fecha_inicio.strftime('%Y%m%d')}_{fecha_fin.strftime('%Y%m%d')}.xlsx"
        else:
            titulo_reporte_excel = f"Control Quincenal de Asistencia - Área: {area_seleccionada}"
            nombre_defecto = f"Reporte_Asistencia_{area_seleccionada.replace(' ', '_')}_{fecha_inicio.strftime('%Y%m%d')}_{fecha_fin.strftime('%Y%m%d')}.xlsx"

        ruta_guardado = filedialog.asksaveasfilename(
            title="Guardar Reporte Excel",
            initialfile=nombre_defecto,
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx")],
            parent=self
        )

        if not ruta_guardado:
            return

        try:
            self.lbl_estado_texto.configure(text="Generando reporte...")
            self.lbl_estado_dot.configure(text_color=colores.ESTADO_PROCESANDO)
            self.update()

            docentes, horarios, checadas_por_dia = self.cargar_datos_reporte(area_seleccionada, fecha_inicio, fecha_fin, solo_asignatura)

            if not docentes:
                self.lbl_estado_texto.configure(text="Listo para generar reporte.")
                self.lbl_estado_dot.configure(text_color=colores.ESTADO_INACTIVO)
                msg = "No hay profesores de asignatura registrados en el sistema." if solo_asignatura else f"No hay docentes registrados en el área: {area_seleccionada}"
                mostrar_advertencia("Sin Datos", msg, master=self)
                return

            dias_quincena = []
            curr = fecha_inicio
            while curr <= fecha_fin:
                if curr.weekday() < 5:  
                    dias_quincena.append(curr)
                curr += timedelta(days=1)

            if not dias_quincena:
                mostrar_advertencia("Aviso", "No hay días laborables (lunes a viernes) en el periodo seleccionado.", master=self)
                self.lbl_estado_texto.configure(text="Listo para generar reporte.")
                self.lbl_estado_dot.configure(text_color=colores.ESTADO_INACTIVO)
                return

            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Control Quincenal"
            ws.views.sheetView[0].showGridLines = True

            ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
            ws.page_setup.paperSize = ws.PAPERSIZE_LETTER
            ws.page_setup.fitToWidth = 1
            ws.page_setup.fitToHeight = 0
            ws.sheet_properties.pageSetUpPr.fitToPage = True
            
            ws.page_margins.left = 0.3
            ws.page_margins.right = 0.3
            ws.page_margins.top = 0.4
            ws.page_margins.bottom = 0.4

            f_subtitulo = Font(name="Arial", size=9, bold=True)
            f_italic = Font(name="Arial", size=7.5, italic=True)
            f_bold = Font(name="Arial", size=7.5, bold=True)
            f_normal = Font(name="Arial", size=7)
            f_nota = Font(name="Arial", size=6.5, bold=True)

            fill_header = PatternFill(start_color="FF000000", end_color="FF000000", fill_type="solid")
            f_header = Font(name="Arial", size=6.5, bold=True, color="FFFFFFFF")
            f_sub_header = Font(name="Arial", size=5.5, bold=False, color="FFFFFFFF")

            thin_border = Border(
                left=Side(style='thin', color='000000'),
                right=Side(style='thin', color='000000'),
                top=Side(style='thin', color='000000'),
                bottom=Side(style='thin', color='000000')
            )

            align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
            align_left = Alignment(horizontal="left", vertical="center")

            total_cols = len(dias_quincena) * 2
            col_fin_letter = get_column_letter(1 + total_cols)
            col_total_letter = get_column_letter(2 + total_cols)

            ws.row_dimensions[1].height = 55

            script_dir = os.path.dirname(os.path.abspath(__file__))

            for img_name in ["logo_utn.png", "Imagen2.png"]:
                ruta_img = os.path.join(script_dir, img_name)
                if os.path.exists(ruta_img):
                    try:
                        img_utn = OpenpyxlImage(ruta_img)
                        img_utn.width = 75
                        img_utn.height = 70
                        ws.add_image(img_utn, "A1")
                        break
                    except Exception:
                        pass

            for img_name in ["logo_iso.png", "Imagen.png"]:
                ruta_img = os.path.join(script_dir, img_name)
                if os.path.exists(ruta_img):
                    try:
                        img_iso = OpenpyxlImage(ruta_img)
                        img_iso.width = 85
                        img_iso.height = 75
                        ws.add_image(img_iso, f"{col_total_letter}1")
                        break
                    except Exception:
                        pass

            ws.merge_cells(f"A1:{col_total_letter}1")
            ws["A1"] = f"UNIVERSIDAD TECNOLÓGICA DE NOGALES, SONORA\nDirección de Administración y Finanzas\nDepartamento de Recursos Humanos\n{titulo_reporte_excel}"
            ws["A1"].font = Font(name="Arial", size=8, bold=True)
            ws["A1"].alignment = align_center

            ws.merge_cells(f"A3:{col_total_letter}3")
            ws["A3"] = f"Alcance: {'Todos los Profesores de Asignatura (Global)' :<40}" if solo_asignatura else f"Área/Dirección: {area_seleccionada}"
            ws["A3"].font = f_subtitulo
            ws["A3"].alignment = align_center

            ws.merge_cells(f"A5:{col_total_letter}5")
            ws["A5"] = f"Periodo del: {fecha_inicio.strftime('%d/%m/%Y')} al {fecha_fin.strftime('%d/%m/%Y')}"
            ws["A5"].font = f_italic
            ws["A5"].alignment = align_center

            header_start_row = 7
            header_end_row = 9

            for r in range(header_start_row, header_end_row + 1):
                for c in range(1, 3 + total_cols):
                    celda = ws.cell(row=r, column=c)
                    celda.fill = fill_header
                    celda.font = f_header
                    celda.alignment = align_center
                    celda.border = thin_border

            ws.merge_cells(f"A{header_start_row}:A{header_end_row}")
            ws[f"A{header_start_row}"] = "NOMBRE"

            ws.merge_cells(f"B{header_start_row}:{col_fin_letter}{header_start_row}")
            ws["B7"] = "DÍAS HÁBILES / ENTRADAS Y SALIDAS"

            ws.merge_cells(f"{col_total_letter}{header_start_row}:{col_total_letter}{header_end_row}")
            ws[f"{col_total_letter}{header_start_row}"] = "TOTAL"

            curr_col = 2
            for d in dias_quincena:
                c1_letra = get_column_letter(curr_col)
                c2_letra = get_column_letter(curr_col + 1)

                ws.merge_cells(f"{c1_letra}8:{c2_letra}8")
                ws[f"{c1_letra}8"] = d.day
                ws[f"{c1_letra}8"].font = f_header

                ws[f"{c1_letra}9"] = "Entrada"
                ws[f"{c1_letra}9"].font = f_sub_header
                ws[f"{c2_letra}9"] = "Salida"
                ws[f"{c2_letra}9"].font = f_sub_header

                curr_col += 2

            fila_actual = 10

            def escribir_bloque(fila_ini, fila_fin, col, valor, fuente, alineacion):
                for r in range(fila_ini, fila_fin + 1):
                    ws.cell(row=r, column=col).border = thin_border
                celda = ws.cell(row=fila_ini, column=col, value=valor)
                celda.font = fuente
                celda.alignment = alineacion
                if fila_fin > fila_ini:
                    ws.merge_cells(start_row=fila_ini, start_column=col, end_row=fila_fin, end_column=col)

            hay_doble_horario = False

            for doc in docentes:
                id_prof = doc['id_profesor']
                nombre_prof = doc['nombre']
                nombre_norm = nombre_prof.strip().lower()

                por_dia = []
                for d in dias_quincena:
                    circunstancia_docente = excepciones_docente.get((nombre_norm, d))
                    circunstancia_global = excepciones_globales.get(d)

                    if circunstancia_docente:
                        celdas = [(circunstancia_docente, circunstancia_docente, 0)]
                    elif circunstancia_global:
                        celdas = [(circunstancia_global, circunstancia_global, 0)]
                    else:
                        celdas = celdas_del_dia(
                            d, horarios.get((id_prof, d.weekday() + 1), ()), checadas_por_dia.get((id_prof, d), ()))
                    por_dia.append(celdas)

                filas_doc = max(len(celdas) for celdas in por_dia)
                hay_doble_horario = hay_doble_horario or filas_doc > 1
                total_retardo_min = sum(retardo for celdas in por_dia for _, _, retardo in celdas)
                fila_fin = fila_actual + filas_doc - 1

                escribir_bloque(fila_actual, fila_fin, 1, nombre_prof, f_bold, align_left)

                col_dia = 2
                for celdas in por_dia:
                    for i, (val_entrada, val_salida, _) in enumerate(celdas):
                        f_ini = fila_actual + i
                        f_fin = f_ini if i < len(celdas) - 1 else fila_fin      
                        escribir_bloque(f_ini, f_fin, col_dia, val_entrada, f_normal, align_center)
                        escribir_bloque(f_ini, f_fin, col_dia + 1, val_salida, f_normal, align_center)
                    col_dia += 2

                escribir_bloque(fila_actual, fila_fin, col_dia, f"{total_retardo_min} min" if total_retardo_min > 0 else "0", f_bold, align_center)

                fila_actual = fila_fin + 1

            fila_actual += 2
            ws.merge_cells(f"A{fila_actual}:{col_total_letter}{fila_actual}")
            ws[f"A{fila_actual}"] = "En este Control aparecen las entradas registradas después del horario estipulado."
            ws[f"A{fila_actual}"].font = f_normal
            ws[f"A{fila_actual}"].alignment = align_center

            fila_actual += 1
            ws.merge_cells(f"A{fila_actual}:{col_total_letter}{fila_actual}")
            ws[f"A{fila_actual}"] = "Se consideran 10 minutos de TOLERANCIA solo en el registro de las Entradas, según el Contrato Colectivo de Trabajo que actualmente nos rige"
            ws[f"A{fila_actual}"].font = f_bold
            ws[f"A{fila_actual}"].alignment = align_center

            fila_actual += 1
            ws.merge_cells(f"A{fila_actual}:{col_total_letter}{fila_actual}")
            ws[f"A{fila_actual}"] = "Después de los 10 minutos de TOLERANCIA se comenzarán a contar los minutos de Retardo del Personal de UTN."
            ws[f"A{fila_actual}"].font = f_normal
            ws[f"A{fila_actual}"].alignment = align_center

            if hay_doble_horario:
                fila_actual += 1
                ws.merge_cells(f"A{fila_actual}:{col_total_letter}{fila_actual}")
                ws[f"A{fila_actual}"] = "Docentes con dos horarios en un mismo día: la primera línea corresponde al primer horario y la segunda al segundo; cada horario se evalúa por separado."
                ws[f"A{fila_actual}"].font = f_normal
                ws[f"A{fila_actual}"].alignment = align_center

            fila_actual += 2
            ws.merge_cells(f"A{fila_actual}:{col_total_letter}{fila_actual}")
            ws[f"A{fila_actual}"] = "FI = Falta Injustificada    I = Incapacidad    AM = Atención Médica    P = Permiso    C = Comisión    FIS = Salida No Registrada    FIE = Entrada No Registrada"
            ws[f"A{fila_actual}"].font = f_nota
            ws[f"A{fila_actual}"].alignment = align_center

            fila_actual += 3
            ws.cell(row=fila_actual, column=1, value="F01PGRRH02.01").font = Font(name="Arial", size=6.5, bold=True)
            ws.cell(row=fila_actual, column=1).alignment = align_left

            c_rev_col1 = get_column_letter(total_cols - 1)
            c_rev_col2 = get_column_letter(total_cols)
            c_rev_col3 = get_column_letter(total_cols + 1)
            c_rev_col4 = get_column_letter(total_cols + 2)

            ws.merge_cells(f"{c_rev_col1}{fila_actual}:{c_rev_col1}{fila_actual+1}")
            ws[f"{c_rev_col1}{fila_actual}"] = "Fecha revisión\n02/04/2025"
            ws[f"{c_rev_col1}{fila_actual}"].font = Font(name="Arial", size=5, bold=True)
            ws[f"{c_rev_col1}{fila_actual}"].alignment = align_center

            ws.merge_cells(f"{c_rev_col2}{fila_actual}:{c_rev_col3}{fila_actual+1}")
            ws[f"{c_rev_col2}{fila_actual}"] = "Hoja 1 de 1"
            ws[f"{c_rev_col2}{fila_actual}"].font = Font(name="Arial", size=5.5, bold=True)
            ws[f"{c_rev_col2}{fila_actual}"].alignment = align_center

            ws.merge_cells(f"{c_rev_col4}{fila_actual}:{c_rev_col4}{fila_actual+1}")
            ws[f"{c_rev_col4}{fila_actual}"] = "Rev. 01"
            ws[f"{c_rev_col4}{fila_actual}"].font = Font(name="Arial", size=5.5, bold=True)
            ws[f"{c_rev_col4}{fila_actual}"].alignment = align_center

            for r_idx in range(fila_actual, fila_actual + 2):
                for col_let in [c_rev_col1, c_rev_col2, c_rev_col3, c_rev_col4]:
                    ws[f"{col_let}{r_idx}"].border = thin_border
                    ws[f"{col_let}{r_idx}"].fill = fill_header
                    ws[f"{col_let}{r_idx}"].font = Font(name="Arial", size=5.5, bold=True, color="FFFFFFFF")

            ws.column_dimensions['A'].width = 22
            for col_i in range(2, 2 + total_cols + 2):
                col_letter = get_column_letter(col_i)
                ws.column_dimensions[col_letter].width = 6.0

            wb.save(ruta_guardado)

            self.lbl_estado_texto.configure(text="Reporte generado exitosamente.")
            self.lbl_estado_dot.configure(text_color=colores.ESTADO_EXITO)

            con_horario = {id_prof for id_prof, _ in horarios}
            sin_horario = [d['nombre'] for d in docentes if d['id_profesor'] not in con_horario]
            if sin_horario:
                lista = "\n".join(f"   – {n}" for n in sin_horario[:10]) + (f"\n   – … y {len(sin_horario) - 10} más" if len(sin_horario) - 10 > 0 else "")
                mostrar_advertencia(
                    "Reporte generado con observaciones",
                    f"El reporte se guardó en:\n{ruta_guardado}\n\n"
                    f"Estos docentes no tienen horario registrado, por eso no se calcularon sus faltas ni retardos "
                    f"(solo aparecen sus ponchadas):\n{lista}\n\n"
                    "Regístrales su horario en «Gestión de Docentes».", master=self)
            else:
                mostrar_exito("Éxito", f"El reporte ha sido generado correctamente en:\n{ruta_guardado}", master=self)

        except Exception as err:
            self.lbl_estado_texto.configure(text="Error al generar reporte")
            self.lbl_estado_dot.configure(text_color=colores.ESTADO_ERROR)
            mostrar_error("Error", f"Fallo durante la generación del reporte:\n{err}", master=self)

    def regresar_al_menu(self):
        if self.parent:
            self.parent.wm_state('normal')
            self.parent.deiconify()
        self.destroy()

    def _crear_interfaz(self):
        main_card = ctk.CTkFrame(
            master=self,
            corner_radius=20,
            fg_color=colores.BG_PANEL,
            border_width=1,
            border_color=colores.BORDE
        )
        main_card.pack(fill="both", expand=True, padx=15, pady=15)

        franja_acento = ctk.CTkFrame(master=main_card, corner_radius=0, fg_color=colores.ACENTO, height=4)
        franja_acento.pack(fill="x", side="top")

        header_frame = ctk.CTkFrame(master=main_card, fg_color=colores.BG_PANEL_ALT, corner_radius=15, height=90, border_width=1, border_color=colores.BORDE_SUAVE)
        header_frame.pack(fill="x", padx=25, pady=(20, 15))

        icono_bg = ctk.CTkFrame(master=header_frame, fg_color="#352A12", corner_radius=14, width=58, height=58)
        icono_bg.pack(side="left", padx=(22, 15), pady=15)
        icono_bg.pack_propagate(False)

        lbl_icon = ctk.CTkLabel(master=icono_bg, text="📋", font=ctk.CTkFont(size=26))
        lbl_icon.pack(expand=True)

        title_box = ctk.CTkFrame(master=header_frame, fg_color="transparent")
        title_box.pack(side="left", fill="y", pady=15)

        lbl_titulo = ctk.CTkLabel(
            master=title_box,
            text="Generador de Reporte Personalizado de Asistencia",
            font=fuentes.titulo(size=22),
            text_color=colores.TEXTO_PRIMARIO,
        )
        lbl_titulo.pack(anchor="w")

        lbl_subtitulo = ctk.CTkLabel(
            master=title_box,
            text="Selecciona el área, define el lapso quincenal y exporta reportes por área o globales de asignatura.",
            font=fuentes.cuerpo(size=13),
            text_color=colores.TEXTO_SECUNDARIO,
        )
        lbl_subtitulo.pack(anchor="w", pady=(2, 0))

        params_frame = ctk.CTkFrame(master=main_card, fg_color=colores.BG_PANEL_ALT, corner_radius=15, border_width=1, border_color=colores.BORDE_SUAVE)
        params_frame.pack(fill="x", padx=25, pady=10, ipady=15)

        lbl_sec_params = ctk.CTkLabel(master=params_frame, text="PARÁMETROS Y LAPSO QUINCENAL (15 DÍAS)", font=fuentes.pequena(size=11), text_color=colores.TEXTO_SECUNDARIO)
        lbl_sec_params.pack(anchor="w", padx=25, pady=(15, 10))

        box_inputs = ctk.CTkFrame(master=params_frame, fg_color="transparent")
        box_inputs.pack(fill="x", padx=25)
        box_inputs.grid_columnconfigure((0, 1), weight=1, uniform="col")

        lbl_area = ctk.CTkLabel(master=box_inputs, text="Área / Dirección (Para reporte por área):", font=fuentes.seccion(size=13), text_color=colores.TEXTO_PRIMARIO)
        lbl_area.grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.cb_area = ctk.CTkComboBox(master=box_inputs, font=fuentes.cuerpo(size=13), height=38, corner_radius=8)
        self.cb_area.grid(row=1, column=0, sticky="ew", padx=(0, 10))

        lbl_periodo = ctk.CTkLabel(master=box_inputs, text="Periodo Quincenal Seleccionado (15 Días):", font=fuentes.seccion(size=13), text_color=colores.TEXTO_PRIMARIO)
        lbl_periodo.grid(row=0, column=1, sticky="w", pady=(0, 5))

        periodo_btn_frame = ctk.CTkFrame(master=box_inputs, fg_color=colores.BG_ENTRADA, corner_radius=8, height=38, border_width=1, border_color=colores.BORDE_SUAVE)
        periodo_btn_frame.grid(row=1, column=1, sticky="ew", padx=(10, 0))
        periodo_btn_frame.pack_propagate(False)

        self.lbl_periodo_val = ctk.CTkLabel(
            master=periodo_btn_frame,
            text=f"Del {self.fecha_inicio_sel.strftime('%d/%m/%Y')} al {self.fecha_fin_sel.strftime('%d/%m/%Y')} (15 Días)",
            font=fuentes.cuerpo(size=13),
            text_color=colores.TEXTO_PRIMARIO
        )
        self.lbl_periodo_val.pack(side="left", padx=12)

        btn_elegir_quincena = ctk.CTkButton(
            master=periodo_btn_frame,
            text="📅 Elegir Quincena",
            width=130,
            height=30,
            fg_color=colores.ACENTO,
            hover_color=colores.ACENTO_HOVER,
            font=fuentes.boton(size=12),
            command=self.abrir_selector_quincena
        )
        btn_elegir_quincena.pack(side="right", padx=4)

        box_btn_exc = ctk.CTkFrame(master=params_frame, fg_color="transparent")
        box_btn_exc.pack(fill="x", padx=25, pady=(18, 5))

        btn_abrir_exc = ctk.CTkButton(
            master=box_btn_exc,
            text="⚙️ Asignar Días Libres o Excepciones",
            fg_color=colores.NEUTRO,
            hover_color=colores.NEUTRO_HOVER,
            text_color=colores.TEXTO_PRIMARIO,
            font=fuentes.boton(size=13),
            corner_radius=8,
            height=38,
            command=self.abrir_dialogo_excepciones
        )
        btn_abrir_exc.pack(side="left")

        self.lbl_estado_excepciones = ctk.CTkLabel(
            master=box_btn_exc,
            text="Sin excepciones asignadas.",
            font=fuentes.cuerpo(size=12),
            text_color=colores.TEXTO_SECUNDARIO
        )
        self.lbl_estado_excepciones.pack(side="left", padx=(15, 0))

        btn_frame = ctk.CTkFrame(master=main_card, fg_color="transparent")
        btn_frame.pack(fill="x", padx=25, pady=20)
        btn_frame.grid_columnconfigure((0, 1), weight=1)

        btn_generar = ctk.CTkButton(
            master=btn_frame,
            text="📊 Exportar reporte por area",
            fg_color="#EEA942",
            hover_color="#AA7526",
            font=fuentes.boton(size=14),
            corner_radius=10,
            height=46,
            command=lambda: self.generar_excel_quincenal(solo_asignatura=False)
        )
        btn_generar.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        btn_generar_asignatura = ctk.CTkButton(
            master=btn_frame,
            text="📊  Exportar reporte de docentes de asignatura",
            fg_color="#2E7D32",
            hover_color="#1B5E20",
            font=fuentes.boton(size=14),
            corner_radius=10,
            height=46,
            command=lambda: self.generar_excel_quincenal(solo_asignatura=True)
        )
        btn_generar_asignatura.grid(row=0, column=1, sticky="ew", padx=(8, 0))

        btn_volver_frame = ctk.CTkFrame(master=main_card, fg_color="transparent")
        btn_volver_frame.pack(fill="x", padx=25, pady=(0, 15))

        btn_volver = ctk.CTkButton(
            master=btn_volver_frame,
            text="Volver al Menú Principal",
            fg_color=colores.NEUTRO,
            hover_color=colores.NEUTRO_HOVER,
            font=fuentes.boton(size=14),
            corner_radius=10,
            width=220,
            height=40,
            command=self.regresar_al_menu
        )
        btn_volver.pack(side="right")

        status_bar = ctk.CTkFrame(master=main_card, fg_color=colores.BG_ENTRADA, corner_radius=10, height=40, border_width=1, border_color=colores.BORDE_SUAVE)
        status_bar.pack(fill="x", padx=25, side="bottom", pady=(0, 20))

        self.lbl_estado_dot = ctk.CTkLabel(master=status_bar, text="●", font=ctk.CTkFont(size=16), text_color=colores.ESTADO_INACTIVO)
        self.lbl_estado_dot.pack(side="left", padx=(16, 6))

        self.lbl_estado_texto = c_lbl = ctk.CTkLabel(
            master=status_bar,
            text="Listo para generar reporte.",
            font=fuentes.cuerpo(size=12),
            text_color=colores.TEXTO_SECUNDARIO,
        )
        c_lbl.pack(side="left")


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()
    root.withdraw()
    ventana = VentanaGenerarReporte(root)
    ventana.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()