import math
from datetime import datetime, timedelta

import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
import mysql.connector

from utilerias.paleta_colores import colores, fuentes

DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
TODAS_AREAS = "Todas las áreas"
TODOS_DOCENTES = "Todos los docentes"
TAMANOS_PAGINA = ["50", "100", "200", "500"]


class VentanaRegistroChecadas(ctk.CTkToplevel):
    """Muestra todas las checadas (ponchadas) guardadas en la tabla `checadas`.

    - Filtros por área, docente y rango de fechas.
    - Paginación hecha en MySQL (LIMIT/OFFSET), así que funciona bien aunque
      haya decenas de miles de registros: sólo se traen las filas de la página.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

        self.title("Registro de Checadas - Control de Acceso")
        self.configure(fg_color=colores.BG_VENTANA)

        # Pantalla completa (zoomed en Windows; en Linux se usa -zoomed)
        try:
            self.state('zoomed')
        except tk.TclError:
            try:
                self.attributes('-zoomed', True)
            except tk.TclError:
                pass
        self.resizable(True, True)

        self.focus()
        self.lift()

        self.pagina_actual = 1
        self.total_registros = 0
        self.tam_pagina = int(TAMANOS_PAGINA[1])
        self.profesores = []          # [{'id_profesor', 'nombre', 'area'}, ...]
        self.mapa_docentes = {}       # texto mostrado en el combo -> id_profesor

        self._crear_interfaz()
        self.cargar_filtros()
        self.buscar()

    # --- CONEXIÓN BASE DE DATOS ---
    @staticmethod
    def obtener_conexion_bd():
        return mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="control_asistencia"
        )

    # --- FILTROS ---
    def cargar_filtros(self):
        """Llena los combos de área y docente desde la tabla profesores."""
        try:
            conn = self.obtener_conexion_bd()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id_profesor, nombre, area FROM profesores ORDER BY nombre ASC")
            self.profesores = cursor.fetchall()
            cursor.close()
            conn.close()
        except Exception as e:
            messagebox.showerror("Error BD", f"No se pudieron cargar los filtros:\n{e}", parent=self)
            return

        areas = sorted({p['area'] for p in self.profesores if p['area']})
        self.cb_area.configure(values=[TODAS_AREAS] + areas)
        self.cb_area.set(TODAS_AREAS)
        self._actualizar_docentes()

    def _actualizar_docentes(self, *_):
        """Muestra en el combo de docentes sólo los del área elegida."""
        area = self.cb_area.get()
        lista = [p for p in self.profesores if area == TODAS_AREAS or p['area'] == area]

        nombres_repetidos = {}
        for p in lista:
            nombres_repetidos[p['nombre']] = nombres_repetidos.get(p['nombre'], 0) + 1

        self.mapa_docentes = {}
        for p in lista:
            texto = p['nombre']
            if nombres_repetidos[p['nombre']] > 1:
                texto = f"{p['nombre']} (ID {p['id_profesor']})"
            self.mapa_docentes[texto] = p['id_profesor']

        self.cb_docente.configure(values=[TODOS_DOCENTES] + list(self.mapa_docentes.keys()))
        self.cb_docente.set(TODOS_DOCENTES)

    @staticmethod
    def _parsear_fecha(texto, nombre_campo):
        texto = texto.strip()
        if not texto:
            return None
        try:
            return datetime.strptime(texto, "%d/%m/%Y")
        except ValueError:
            raise ValueError(f"La fecha '{nombre_campo}' no es válida. Usa el formato dd/mm/aaaa (ej. 16/12/2025).")

    def _construir_filtros_sql(self):
        """Devuelve (WHERE, parámetros) según los filtros elegidos."""
        condiciones = []
        params = []

        docente = self.cb_docente.get()
        area = self.cb_area.get()
        if docente != TODOS_DOCENTES and docente in self.mapa_docentes:
            condiciones.append("c.id_profesor = %s")
            params.append(self.mapa_docentes[docente])
        elif area != TODAS_AREAS:
            condiciones.append("p.area = %s")
            params.append(area)

        desde = self._parsear_fecha(self.ent_desde.get(), "Desde")
        hasta = self._parsear_fecha(self.ent_hasta.get(), "Hasta")
        if desde and hasta and desde > hasta:
            raise ValueError("La fecha 'Desde' no puede ser posterior a la fecha 'Hasta'.")
        if desde:
            condiciones.append("c.fecha_hora >= %s")
            params.append(desde)
        if hasta:
            condiciones.append("c.fecha_hora < %s")
            params.append(hasta + timedelta(days=1))

        where = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""
        return where, params

    # --- CONSULTA Y TABLA ---
    def buscar(self):
        """Aplica los filtros y vuelve a la primera página."""
        self.pagina_actual = 1
        self.cargar_pagina()

    def limpiar_filtros(self):
        self.cb_area.set(TODAS_AREAS)
        self._actualizar_docentes()
        self.ent_desde.delete(0, "end")
        self.ent_hasta.delete(0, "end")
        self.buscar()

    def cargar_pagina(self):
        try:
            where, params = self._construir_filtros_sql()
        except ValueError as e:
            messagebox.showwarning("Filtros no válidos", str(e), parent=self)
            return

        self._estado("Consultando checadas...", colores.ESTADO_PROCESANDO)
        self.update_idletasks()

        try:
            conn = self.obtener_conexion_bd()
            cursor = conn.cursor(dictionary=True)

            base = """
                FROM checadas c
                LEFT JOIN profesores p ON p.id_profesor = c.id_profesor
            """
            cursor.execute(f"SELECT COUNT(*) AS total {base} {where}", params)
            self.total_registros = cursor.fetchone()['total']

            total_paginas = self.total_paginas()
            if self.pagina_actual > total_paginas:
                self.pagina_actual = total_paginas
            offset = (self.pagina_actual - 1) * self.tam_pagina

            cursor.execute(
                f"""
                SELECT c.id_checada, p.nombre, p.area, c.fecha_hora
                {base} {where}
                ORDER BY c.fecha_hora DESC, c.id_checada DESC
                LIMIT %s OFFSET %s
                """,
                params + [self.tam_pagina, offset]
            )
            filas = cursor.fetchall()
            cursor.close()
            conn.close()
        except Exception as e:
            self._estado("Error al consultar", colores.ESTADO_ERROR)
            messagebox.showerror("Error BD", f"No se pudieron cargar las checadas:\n{e}", parent=self)
            return

        self._llenar_tabla(filas)
        self._actualizar_paginacion(len(filas))

        if self.total_registros:
            self._estado("Registro cargado correctamente.", colores.ESTADO_EXITO)
        else:
            self._estado("No hay checadas con los filtros seleccionados.", colores.ESTADO_INFO)

    def _llenar_tabla(self, filas):
        self.tabla.delete(*self.tabla.get_children())
        for i, f in enumerate(filas):
            fh = f['fecha_hora']
            self.tabla.insert(
                "", "end",
                values=(
                    f['id_checada'],
                    f['nombre'] or "(Docente eliminado)",
                    f['area'] or "—",
                    fh.strftime("%d/%m/%Y"),
                    DIAS_SEMANA[fh.weekday()],
                    fh.strftime("%H:%M:%S"),
                ),
                tags=("par" if i % 2 == 0 else "impar",),
            )

    def total_paginas(self):
        return max(1, math.ceil(self.total_registros / self.tam_pagina))

    def _actualizar_paginacion(self, filas_en_pagina):
        total_pag = self.total_paginas()
        if self.total_registros:
            inicio = (self.pagina_actual - 1) * self.tam_pagina + 1
            fin = inicio + filas_en_pagina - 1
            self.lbl_resumen.configure(
                text=f"Mostrando {inicio:,} – {fin:,} de {self.total_registros:,} checadas"
            )
        else:
            self.lbl_resumen.configure(text="0 checadas")

        self.lbl_pagina.configure(text=f"Página {self.pagina_actual} de {total_pag}")
        self.btn_ant.configure(state="normal" if self.pagina_actual > 1 else "disabled")
        self.btn_sig.configure(state="normal" if self.pagina_actual < total_pag else "disabled")

    def pagina_anterior(self):
        if self.pagina_actual > 1:
            self.pagina_actual -= 1
            self.cargar_pagina()

    def pagina_siguiente(self):
        if self.pagina_actual < self.total_paginas():
            self.pagina_actual += 1
            self.cargar_pagina()

    def cambiar_tamano_pagina(self, valor):
        self.tam_pagina = int(valor)
        self.buscar()

    def _estado(self, texto, color):
        self.lbl_estado_texto.configure(text=texto)
        self.lbl_estado_dot.configure(text_color=color)

    def regresar_al_menu(self):
        if self.parent:
            self.parent.wm_state('normal')
            self.parent.deiconify()
        self.destroy()

    # --- DISEÑO DE LA INTERFAZ ---
    def _configurar_estilo_tabla(self):
        try:
            esc = self._get_window_scaling()
        except Exception:
            esc = 1.0

        estilo = ttk.Style(self)
        estilo.theme_use("clam")
        estilo.configure(
            "Checadas.Treeview",
            background=colores.BG_SUPERFICIE,
            fieldbackground=colores.BG_SUPERFICIE,
            foreground=colores.TEXTO_PRIMARIO,
            rowheight=int(30 * esc),
            borderwidth=0,
            bordercolor=colores.BG_SUPERFICIE,
            lightcolor=colores.BG_SUPERFICIE,
            darkcolor=colores.BG_SUPERFICIE,
            font=(fuentes.FAMILIA, 11),
        )
        estilo.configure(
            "Checadas.Treeview.Heading",
            background=colores.NEUTRO,
            foreground=colores.TEXTO_PRIMARIO,
            relief="flat",
            borderwidth=0,
            padding=(6, int(6 * esc)),
            font=(fuentes.FAMILIA, 11, "bold"),
        )
        estilo.map("Checadas.Treeview",
                   background=[("selected", colores.COLOR_SELECCIONADO)],
                   foreground=[("selected", colores.TEXTO_PRIMARIO)])
        estilo.map("Checadas.Treeview.Heading",
                   background=[("active", colores.NEUTRO_HOVER)])

    def _crear_interfaz(self):
        main_card = ctk.CTkFrame(
            master=self, corner_radius=20, fg_color=colores.BG_PANEL,
            border_width=1, border_color=colores.BORDE
        )
        main_card.pack(fill="both", expand=True, padx=15, pady=15)

        franja = ctk.CTkFrame(master=main_card, corner_radius=0, fg_color=colores.ACENTO, height=4)
        franja.pack(fill="x", side="top")

        # Encabezado
        header = ctk.CTkFrame(master=main_card, fg_color=colores.BG_PANEL_ALT, corner_radius=15,
                              height=90, border_width=1, border_color=colores.BORDE_SUAVE)
        header.pack(fill="x", padx=25, pady=(20, 10))

        icono_bg = ctk.CTkFrame(master=header, fg_color="#2A1F46", corner_radius=14, width=58, height=58)
        icono_bg.pack(side="left", padx=(22, 15), pady=15)
        icono_bg.pack_propagate(False)
        ctk.CTkLabel(master=icono_bg, text="🕒", font=ctk.CTkFont(size=26)).pack(expand=True)

        caja_titulo = ctk.CTkFrame(master=header, fg_color="transparent")
        caja_titulo.pack(side="left", fill="y", pady=15)
        ctk.CTkLabel(master=caja_titulo, text="Registro de Checadas",
                     font=fuentes.titulo(size=22), text_color=colores.TEXTO_PRIMARIO).pack(anchor="w")
        ctk.CTkLabel(master=caja_titulo,
                     text="Consulta todas las checadas guardadas en el sistema. Filtra por área, docente o fechas.",
                     font=fuentes.cuerpo(size=13), text_color=colores.TEXTO_SECUNDARIO).pack(anchor="w", pady=(2, 0))

        # Panel de filtros
        filtros = ctk.CTkFrame(master=main_card, fg_color=colores.BG_PANEL_ALT, corner_radius=15,
                               border_width=1, border_color=colores.BORDE_SUAVE)
        filtros.pack(fill="x", padx=25, pady=6)

        ctk.CTkLabel(master=filtros, text="FILTROS", font=fuentes.pequena(size=11),
                     text_color=colores.TEXTO_SECUNDARIO).pack(anchor="w", padx=25, pady=(12, 4))

        fila = ctk.CTkFrame(master=filtros, fg_color="transparent")
        fila.pack(fill="x", padx=25, pady=(0, 15))
        fila.grid_columnconfigure((0, 1), weight=3, uniform="f")
        fila.grid_columnconfigure((2, 3), weight=2, uniform="f")
        fila.grid_columnconfigure(4, weight=0)

        def etiqueta(texto, col):
            ctk.CTkLabel(master=fila, text=texto, font=fuentes.seccion(size=13),
                         text_color=colores.TEXTO_PRIMARIO).grid(row=0, column=col, sticky="w", pady=(0, 5))

        etiqueta("Área / Dirección:", 0)
        self.cb_area = ctk.CTkComboBox(master=fila, values=[TODAS_AREAS], height=38, corner_radius=8,
                                       font=fuentes.cuerpo(size=13), state="readonly",
                                       command=self._actualizar_docentes)
        self.cb_area.grid(row=1, column=0, sticky="ew", padx=(0, 10))
        self.cb_area.set(TODAS_AREAS)

        etiqueta("Docente:", 1)
        self.cb_docente = ctk.CTkComboBox(master=fila, values=[TODOS_DOCENTES], height=38, corner_radius=8,
                                          font=fuentes.cuerpo(size=13), state="readonly")
        self.cb_docente.grid(row=1, column=1, sticky="ew", padx=5)
        self.cb_docente.set(TODOS_DOCENTES)

        etiqueta("Desde (dd/mm/aaaa):", 2)
        self.ent_desde = ctk.CTkEntry(master=fila, height=38, corner_radius=8, font=fuentes.cuerpo(size=13),
                                      placeholder_text="01/12/2025")
        self.ent_desde.grid(row=1, column=2, sticky="ew", padx=5)

        etiqueta("Hasta (dd/mm/aaaa):", 3)
        self.ent_hasta = ctk.CTkEntry(master=fila, height=38, corner_radius=8, font=fuentes.cuerpo(size=13),
                                      placeholder_text="15/12/2025")
        self.ent_hasta.grid(row=1, column=3, sticky="ew", padx=5)

        self.ent_desde.bind("<Return>", lambda e: self.buscar())
        self.ent_hasta.bind("<Return>", lambda e: self.buscar())

        botones = ctk.CTkFrame(master=fila, fg_color="transparent")
        botones.grid(row=1, column=4, sticky="e", padx=(10, 0))
        ctk.CTkButton(master=botones, text="🔍 Buscar", width=110, height=38, corner_radius=8,
                      font=fuentes.boton(size=13), fg_color=colores.ACENTO, hover_color=colores.ACENTO_HOVER,
                      text_color=colores.TEXTO_SOBRE_ACENTO, command=self.buscar).pack(side="left", padx=(0, 8))
        ctk.CTkButton(master=botones, text="Limpiar", width=90, height=38, corner_radius=8,
                      font=fuentes.boton(size=13), fg_color=colores.NEUTRO, hover_color=colores.NEUTRO_HOVER,
                      text_color=colores.TEXTO_PRIMARIO, command=self.limpiar_filtros).pack(side="left")

        # Barra inferior (se empaqueta antes que la tabla para que siempre quede visible)
        status_bar = ctk.CTkFrame(master=main_card, fg_color=colores.BG_ENTRADA, corner_radius=10, height=40,
                                  border_width=1, border_color=colores.BORDE_SUAVE)
        status_bar.pack(fill="x", padx=25, side="bottom", pady=(0, 20))

        self.lbl_estado_dot = ctk.CTkLabel(master=status_bar, text="●", font=ctk.CTkFont(size=16),
                                           text_color=colores.ESTADO_INACTIVO)
        self.lbl_estado_dot.pack(side="left", padx=(16, 6))
        self.lbl_estado_texto = ctk.CTkLabel(master=status_bar, text="Listo.", font=fuentes.cuerpo(size=12),
                                             text_color=colores.TEXTO_SECUNDARIO)
        self.lbl_estado_texto.pack(side="left")

        pie = ctk.CTkFrame(master=main_card, fg_color="transparent")
        pie.pack(fill="x", padx=25, side="bottom", pady=(10, 10))

        self.lbl_resumen = ctk.CTkLabel(master=pie, text="", font=fuentes.cuerpo(size=13),
                                        text_color=colores.TEXTO_SECUNDARIO)
        self.lbl_resumen.pack(side="left")

        ctk.CTkButton(master=pie, text="Volver al Menú Principal", width=200, height=38, corner_radius=10,
                      font=fuentes.boton(size=13), fg_color=colores.NEUTRO, hover_color=colores.NEUTRO_HOVER,
                      command=self.regresar_al_menu).pack(side="right", padx=(15, 0))

        self.btn_sig = ctk.CTkButton(master=pie, text="Siguiente ▶", width=110, height=38, corner_radius=8,
                                     font=fuentes.boton(size=13), fg_color=colores.ACENTO,
                                     hover_color=colores.ACENTO_HOVER, command=self.pagina_siguiente)
        self.btn_sig.pack(side="right", padx=(8, 0))
        self.lbl_pagina = ctk.CTkLabel(master=pie, text="Página 1 de 1", font=fuentes.seccion(size=13),
                                       text_color=colores.TEXTO_PRIMARIO)
        self.lbl_pagina.pack(side="right", padx=8)
        self.btn_ant = ctk.CTkButton(master=pie, text="◀ Anterior", width=110, height=38, corner_radius=8,
                                     font=fuentes.boton(size=13), fg_color=colores.ACENTO,
                                     hover_color=colores.ACENTO_HOVER, command=self.pagina_anterior)
        self.btn_ant.pack(side="right", padx=(0, 8))

        self.cb_tam = ctk.CTkComboBox(master=pie, values=TAMANOS_PAGINA, width=80, height=38, corner_radius=8,
                                      font=fuentes.cuerpo(size=13), state="readonly",
                                      command=self.cambiar_tamano_pagina)
        self.cb_tam.set(str(self.tam_pagina))
        self.cb_tam.pack(side="right", padx=(0, 20))
        ctk.CTkLabel(master=pie, text="Filas por página:", font=fuentes.cuerpo(size=12),
                     text_color=colores.TEXTO_SECUNDARIO).pack(side="right", padx=(0, 6))

        # Tabla
        contenedor = ctk.CTkFrame(master=main_card, fg_color=colores.BG_SUPERFICIE, corner_radius=12,
                                  border_width=1, border_color=colores.BORDE_SUAVE)
        contenedor.pack(fill="both", expand=True, padx=25, pady=(10, 0))

        self._configurar_estilo_tabla()
        columnas = ("id", "docente", "area", "fecha", "dia", "hora")
        self.tabla = ttk.Treeview(contenedor, columns=columnas, show="headings",
                                  style="Checadas.Treeview", selectmode="browse",
                                  takefocus=False)
        self.tabla.configure(selectmode="browse")
        encabezados = {
            "id": ("ID", 80, "center"),
            "docente": ("Docente", 320, "w"),
            "area": ("Área", 260, "w"),
            "fecha": ("Fecha", 120, "center"),
            "dia": ("Día", 120, "center"),
            "hora": ("Hora", 110, "center"),
        }
        for col, (texto, ancho, ancla) in encabezados.items():
            self.tabla.heading(col, text=texto, anchor=ancla)
            self.tabla.column(col, width=ancho, anchor=ancla, stretch=(col in ("docente", "area")))

        self.tabla.tag_configure("par", background=colores.BG_SUPERFICIE)
        self.tabla.tag_configure("impar", background=colores.BG_PANEL_ALT)

        scroll = ctk.CTkScrollbar(contenedor, command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y", padx=(0, 4), pady=6)
        self.tabla.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=6)


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()
    root.withdraw()
    ventana = VentanaRegistroChecadas(root)
    ventana.protocol("WM_DELETE_WINDOW", root.destroy)
    root.mainloop()
