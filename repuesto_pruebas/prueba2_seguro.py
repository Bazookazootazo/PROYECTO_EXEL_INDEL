import math
import customtkinter as ctk
from gestion_docente import operaciones_bloque as ops
from gestion_docente.crud_docente import VentanaCrudProfesor
from gestion_docente.ventana_bloque import VentanaBloque
from gestion_docente.ventana_importar import VentanaImportar
from utilerias import database as db
from utilerias.campo_hora import aplicar_formato_hora
from utilerias.messagebox_variados import mostrar_advertencia, mostrar_error, mostrar_exito, mostrar_pregunta
from utilerias.paleta_colores import colores, fuentes

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class VentanaGestionDocentes(ctk.CTkToplevel):
    DIAS_MAPPING = {"Lunes": 1, "Martes": 2, "Miércoles": 3, "Jueves": 4, "Viernes": 5}
    ELEMENTOS_POR_PAGINA = 10

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.profesores_cache = []
        self.profesores_filtrados = []
        self.profesor_seleccionado = None       # Docente activo en vista individual (panel derecho)
        self.seleccion = set()                  # IDs marcados para acciones en bloque
        self.pagina_actual = 1
        self.pool_tarjetas = []
        
        self._configurar_ventana()
        self._construir_panel_izquierdo()
        self._construir_panel_derecho()
        self.cargar_lista_profesores()

    def _configurar_ventana(self):
        self.title("Gestión Docente y Horarios")
        self.geometry("1150x720")
        self.minsize(900, 600)
        self.configure(fg_color=colores.BG_VENTANA)
        self.after(10, lambda: self.wm_state('zoomed'))
        
        # Grid principal con distribución uniforme y responsiva
        self.grid_columnconfigure(0, weight=4, uniform="paneles")
        self.grid_columnconfigure(1, weight=5, uniform="paneles")
        self.grid_rowconfigure(0, weight=1)

    def _construir_panel_izquierdo(self):
        panel = ctk.CTkFrame(self, corner_radius=16, fg_color=colores.BG_PANEL, border_width=1, border_color=colores.BORDE)
        panel.grid(row=0, column=0, sticky="nsew", padx=(15, 7), pady=15)
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(5, weight=1)

        encabezado = ctk.CTkFrame(panel, fg_color="transparent")
        encabezado.grid(row=0, column=0, sticky="ew", padx=18, pady=(10, 6))
        
        ctk.CTkLabel(encabezado, text="👥  Gestión Docente", font=fuentes.seccion(size=17), text_color=colores.TEXTO_PRIMARIO).pack(anchor="w")
        ctk.CTkLabel(encabezado, text="Catálogo de profesores y horarios", font=fuentes.pequena(size=11), text_color=colores.TEXTO_SECUNDARIO).pack(anchor="w", pady=(2, 0))

        # Contenedor de botones de acciones principales
        btn_frame_acciones = ctk.CTkFrame(panel, fg_color="transparent")
        btn_frame_acciones.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 6))
        btn_frame_acciones.grid_columnconfigure(0, weight=1)
        btn_frame_acciones.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            btn_frame_acciones, text="+  Nuevo Docente", command=self.abrir_ventana_registro,
            font=fuentes.boton(size=13), height=38, corner_radius=10,
            fg_color=colores.ACENTO, hover_color=colores.ACENTO_HOVER,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 5))

        ctk.CTkButton(
            btn_frame_acciones, text="📁  Importar Datos", command=self.cargar_archivo_masivo,
            font=fuentes.boton(size=13), height=38, corner_radius=10,
            fg_color=colores.EXITO, hover_color=colores.EXITO_HOVER,
        ).grid(row=0, column=1, sticky="ew", padx=(5, 0))

        self.var_busqueda = ctk.StringVar()
        self.var_busqueda.trace_add("write", self.filtrar_profesores)
        ctk.CTkEntry(
            panel, textvariable=self.var_busqueda, placeholder_text="🔍  Buscar por nombre o área...",
            height=34, corner_radius=10, font=fuentes.cuerpo(size=12),
            fg_color=colores.BG_ENTRADA, border_color=colores.BORDE,
        ).grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 6))

        self._construir_barra_seleccion(panel)

        self.container_profesores = ctk.CTkFrame(panel, fg_color="transparent")
        self.container_profesores.grid(row=5, column=0, sticky="nsew", padx=10, pady=(0, 5))
        self.container_profesores.grid_columnconfigure(0, weight=1)

        for r in range(self.ELEMENTOS_POR_PAGINA):
            self.container_profesores.grid_rowconfigure(r, weight=0)

        self._crear_pool_tarjetas()

        nav_frame = ctk.CTkFrame(panel, fg_color="transparent")
        nav_frame.grid(row=6, column=0, sticky="ew", padx=15, pady=(4, 10))

        self.btn_prev = ctk.CTkButton(
            nav_frame, text="←  Anterior", width=90, height=32, corner_radius=8,
            font=fuentes.cuerpo(size=12), fg_color=colores.NEUTRO, hover_color=colores.NEUTRO_HOVER,
            command=self.pagina_anterior,
        )
        self.btn_prev.pack(side="left")
        
        self.lbl_paginacion = ctk.CTkLabel(nav_frame, text="Pág 1 / 1", font=fuentes.boton(size=12), text_color=colores.TEXTO_SECUNDARIO)
        self.lbl_paginacion.pack(side="left", expand=True)
        
        self.btn_next = ctk.CTkButton(
            nav_frame, text="Siguiente  →", width=90, height=32, corner_radius=8,
            font=fuentes.cuerpo(size=12), fg_color=colores.NEUTRO, hover_color=colores.NEUTRO_HOVER,
            command=self.pagina_siguiente,
        )
        self.btn_next.pack(side="right")

    def _crear_pool_tarjetas(self):
        """Crea el pool fijo de tarjetas optimizado para alojar las 10 celdas sin desbordamiento."""
        for i in range(self.ELEMENTOS_POR_PAGINA):
            card = ctk.CTkFrame(self.container_profesores, fg_color=colores.COLOR_TARJETA, corner_radius=8, border_width=1, border_color=colores.COLOR_TARJETA_BORDE, cursor="hand2", height=38)
            card.grid_propagate(False)
            card.grid(row=i, column=0, sticky="ew", pady=1, padx=2)
            card.grid_columnconfigure(0, weight=0)
            card.grid_columnconfigure(1, weight=1)
            card.grid_columnconfigure(2, weight=0)

            var_chk = ctk.BooleanVar(value=False)
            chk = ctk.CTkCheckBox(card, text="", variable=var_chk, width=24, checkbox_width=18, checkbox_height=18, corner_radius=4,
                                    fg_color=colores.ACENTO, hover_color=colores.ACENTO_HOVER, border_color=colores.BORDE_CLARO)
            chk.grid(row=0, column=0, rowspan=2, padx=(10, 0))

            lbl_nombre = ctk.CTkLabel(card, text="", anchor="w", font=fuentes.boton(size=12), text_color=colores.TEXTO_PRIMARIO, height=14)
            lbl_nombre.grid(row=0, column=1, sticky="ew", padx=(8, 10), pady=(3, 0))

            lbl_area = ctk.CTkLabel(card, text="", anchor="w", font=fuentes.pequena(size=10), text_color=colores.COLOR_TEXTO_AREA, height=12)
            lbl_area.grid(row=1, column=1, sticky="ew", padx=(8, 10), pady=(0, 3))

            btn_frame = ctk.CTkFrame(card, fg_color="transparent")
            btn_frame.grid(row=0, column=2, rowspan=2, sticky="e", padx=(0, 6))
            btn_frame.grid_columnconfigure((0, 1), weight=0)

            btn_edit = ctk.CTkButton(btn_frame, text="Editar", width=30, height=24, corner_radius=6, font=fuentes.pequena(size=10), fg_color=colores.COLOR_BTN_EDITAR, hover_color=colores.COLOR_BTN_EDITAR_HOVER)
            btn_edit.grid(row=0, column=0, padx=2)

            btn_del = ctk.CTkButton(btn_frame, text="Eliminar", width=30, height=24, corner_radius=6, font=fuentes.pequena(size=10), fg_color=colores.COLOR_BTN_ELIMINAR, hover_color=colores.COLOR_BTN_ELIMINAR_HOVER)
            btn_del.grid(row=0, column=1, padx=2)

            card.profesor_asociado = None

            def _on_card_click(event, c=card):
                if c.profesor_asociado:
                    self.seleccionar_profesor(c.profesor_asociado)

            card.bind("<Button-1>", _on_card_click)
            lbl_nombre.bind("<Button-1>", _on_card_click)
            lbl_area.bind("<Button-1>", _on_card_click)

            self.pool_tarjetas.append({
                "frame": card, "lbl_nombre": lbl_nombre, "lbl_area": lbl_area, 
                "btn_edit": btn_edit, "btn_del": btn_del, "btn_frame": btn_frame, 
                "chk": chk, "var_chk": var_chk
            })

    def _construir_panel_derecho(self):
        panel = ctk.CTkFrame(self, corner_radius=16, fg_color=colores.BG_PANEL, border_width=1, border_color=colores.BORDE)
        panel.grid(row=0, column=1, sticky="nsew", padx=(7, 15), pady=15)
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(3, weight=1)

        encabezado = ctk.CTkFrame(panel, fg_color="transparent")
        encabezado.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 10))

        frame_titulo = ctk.CTkFrame(encabezado, fg_color="transparent")
        frame_titulo.pack(fill="x")

        self.lbl_prof_seleccionado = ctk.CTkLabel(frame_titulo, text="🗓  Horario Semanal", font=fuentes.seccion(size=17), text_color=colores.TEXTO_PRIMARIO)
        self.lbl_prof_seleccionado.pack(side="left", anchor="w")

        btn_volver_menu = ctk.CTkButton(
            frame_titulo, text="Volver al Menú principal", width=120, height=32, corner_radius=8,
            font=fuentes.boton(size=12), fg_color=colores.NEUTRO,
            hover_color=colores.NEUTRO_HOVER, command=self.regresar_al_menu
        )
        btn_volver_menu.pack(side="right", anchor="e")

        ctk.CTkLabel(encabezado, text="Selecciona un docente de la lista para ver o editar su horario", font=fuentes.pequena(size=11), text_color=colores.TEXTO_SECUNDARIO).pack(anchor="w", pady=(2, 0))

        horario_form = ctk.CTkFrame(panel, corner_radius=12, fg_color=colores.BG_PANEL_ALT, border_width=1, border_color=colores.BORDE_SUAVE)
        horario_form.grid(row=1, column=0, sticky="ew", padx=15, pady=(4, 12))

        self.cmb_dia = ctk.CTkOptionMenu(
            horario_form, values=list(self.DIAS_MAPPING.keys()), width=120, height=34,
            font=fuentes.cuerpo(size=12), fg_color=colores.BG_ENTRADA,
            button_color=colores.ACENTO, button_hover_color=colores.ACENTO_HOVER,
        )
        self.cmb_dia.pack(side="left", padx=(12, 6), pady=8)

        self.ent_entrada = ctk.CTkEntry(
            horario_form, width=90, height=34, placeholder_text="07:00",
            font=fuentes.cuerpo(size=13), fg_color=colores.BG_ENTRADA, border_color=colores.BORDE,
        )
        self.ent_entrada.pack(side="left", padx=5, pady=8)
        aplicar_formato_hora(self.ent_entrada)

        self.ent_salida = ctk.CTkEntry(
            horario_form, width=90, height=34, placeholder_text="12:00",
            font=fuentes.cuerpo(size=13), fg_color=colores.BG_ENTRADA, border_color=colores.BORDE,
        )
        self.ent_salida.pack(side="left", padx=5, pady=8)
        aplicar_formato_hora(self.ent_salida)

        ctk.CTkButton(
            horario_form, text="+  Agregar Turno", command=self.guardar_horario,
            height=34, corner_radius=9, font=fuentes.boton(size=12),
            fg_color=colores.EXITO, hover_color=colores.EXITO_HOVER,
        ).pack(side="left", padx=(5, 12), fill="x", expand=True, pady=8)

        self.scroll_horarios = ctk.CTkScrollableFrame(panel, fg_color="transparent")
        self.scroll_horarios.grid(row=3, column=0, sticky="nsew", padx=10, pady=(0, 15))

    def regresar_al_menu(self):
        if self.parent:
            self.parent.wm_state('normal')
            self.parent.deiconify()
        self.destroy()

    def cargar_lista_profesores(self):
        try:
            self.profesores_cache = db.obtener_profesores()
        except Exception as e:
            mostrar_error("Error de Conexión", f"No se pudo conectar a la base de datos:\n{e}", master=self)
            return

        self.seleccion &= {p['id_profesor'] for p in self.profesores_cache}
        if self.profesor_seleccionado:
            actual = next((p for p in self.profesores_cache if p['id_profesor'] == self.profesor_seleccionado['id_profesor']), None)
            self.profesor_seleccionado = actual
            self.lbl_prof_seleccionado.configure(text=f"🗓  Horario: {actual['nombre'].title()}" if actual else "🗓  Horario Semanal")
            if not actual:
                self.cargar_horarios_profesor()

        self._aplicar_filtro()
        self.pagina_actual = min(self.pagina_actual, self.total_paginas())
        self.renderizar_pagina()

    def _aplicar_filtro(self):
        query = self.var_busqueda.get().strip().lower()
        self.profesores_filtrados = [p for p in self.profesores_cache if query in p['nombre'].lower() or query in p['area'].lower()] if query else self.profesores_cache.copy()

    def filtrar_profesores(self, *args):
        self._aplicar_filtro()
        self.pagina_actual = 1
        self.renderizar_pagina()

    def abrir_ventana_registro(self):
        VentanaCrudProfesor(self, on_success_callback=self.cargar_lista_profesores)

    def abrir_ventana_edicion(self, profesor):
        VentanaCrudProfesor(self, profesor_a_editar=profesor, on_success_callback=self.cargar_lista_profesores)

    def eliminar_docente(self, profesor):
        if not mostrar_pregunta("Confirmar Eliminación", f"¿Estás seguro de eliminar a {profesor['nombre']}?\nSe borrarán también todos sus horarios asignados.", master=self):
            return
        try:
            _, bloqueados = db.eliminar_profesores_en_bloque([profesor['id_profesor']])
        except Exception as e:
            mostrar_error("Error", ops.traducir_error(e), master=self)
            return
        self.cargar_lista_profesores()
        if bloqueados:
            mostrar_advertencia("No se pudo eliminar", f"{profesor['nombre'].title()} {bloqueados[profesor['id_profesor']]}; no se eliminó.", master=self)
        else:
            mostrar_exito("Éxito", "Eliminado correctamente.", master=self)

    def seleccionar_profesor(self, profesor):
        self.profesor_seleccionado = profesor
        self.lbl_prof_seleccionado.configure(text=f"🗓  Horario: {profesor['nombre'].title()}")
        self._pintar_tarjetas()
        self.cargar_horarios_profesor()

    def total_paginas(self):
        return math.ceil(len(self.profesores_filtrados) / self.ELEMENTOS_POR_PAGINA) or 1

    def renderizar_pagina(self):
        inicio = (self.pagina_actual - 1) * self.ELEMENTOS_POR_PAGINA
        pagina_items = self.profesores_filtrados[inicio:inicio + self.ELEMENTOS_POR_PAGINA]

        for i in range(self.ELEMENTOS_POR_PAGINA):
            item = self.pool_tarjetas[i]
            card = item["frame"]
            lbl_nombre = item["lbl_nombre"]
            lbl_area = item["lbl_area"]

            if i < len(pagina_items):
                prof = pagina_items[i]
                card.profesor_asociado = prof  
                
                estilo_tarjeta, color_area = self._estilo_tarjeta(prof)
                lbl_nombre.configure(text=f"{prof['nombre'].title()}")
                lbl_area.configure(text=f"{prof['area'].title()}")
                card.configure(**estilo_tarjeta, cursor="hand2")
                lbl_area.configure(text_color=color_area)

                item["var_chk"].set(prof['id_profesor'] in self.seleccion)
                item["chk"].configure(command=lambda i=prof['id_profesor'], v=item["var_chk"]: self.alternar_seleccion(i, v.get()))
                item["chk"].grid()

                item["btn_edit"].configure(command=lambda p=prof: self.abrir_ventana_edicion(p))
                item["btn_del"].configure(command=lambda p=prof: self.eliminar_docente(p))

                card.grid(row=i, column=0, sticky="ew", pady=2, padx=2)
                item["btn_frame"].grid()
            else:
                card.profesor_asociado = None
                lbl_nombre.configure(text="")
                lbl_area.configure(text="")
                item["btn_frame"].grid_remove()
                item["chk"].grid_remove()
                card.grid_remove()  # Oculta limpiamente las tarjetas sobrantes del pool

        total_pags = self.total_paginas()
        self.lbl_paginacion.configure(text=f"Pág {self.pagina_actual} / {total_pags}")

        self.btn_prev.configure(state="normal" if self.pagina_actual > 1 else "disabled")
        self.btn_next.configure(state="normal" if self.pagina_actual < total_pags else "disabled")

        self.container_profesores.update_idletasks()
        self._actualizar_barra_seleccion()

    def pagina_anterior(self):
        if self.pagina_actual > 1:
            self.pagina_actual -= 1
            self.renderizar_pagina()

    def pagina_siguiente(self):
        if self.pagina_actual < self.total_paginas():
            self.pagina_actual += 1
            self.renderizar_pagina()

    def cargar_horarios_profesor(self):
        for child in self.scroll_horarios.winfo_children():
            child.destroy()
        if not self.profesor_seleccionado:
            return
        horarios = db.obtener_horarios_profesor(self.profesor_seleccionado['id_profesor'])
        if not horarios:
            ctk.CTkLabel(self.scroll_horarios, text="📭  No hay horarios asignados", font=fuentes.cuerpo(size=13), text_color=colores.TEXTO_TENUE).pack(pady=20)
            return
        for h in horarios:
            row = ctk.CTkFrame(self.scroll_horarios, fg_color=colores.COLOR_TARJETA, corner_radius=10, border_width=1, border_color=colores.COLOR_TARJETA_BORDE, height=40)
            row.pack(fill="x", pady=4, padx=2)
            row.grid_columnconfigure(0, weight=1)
            
            texto_horario = f"🕑  {h['nombre_dia']}   ·   Entrada {h['hora_entrada']} hrs   ·   Salida {h['hora_salida']} hrs"
            ctk.CTkLabel(row, text=texto_horario, font=fuentes.cuerpo(size=13), text_color=colores.TEXTO_PRIMARIO, anchor="w").pack(side="left", padx=15, pady=8, fill="x", expand=True)
            ctk.CTkButton(row, text="Eliminar", width=70, height=28, corner_radius=7, font=fuentes.pequena(size=11), fg_color=colores.COLOR_BTN_ELIMINAR, hover_color=colores.COLOR_BTN_ELIMINAR_HOVER, command=lambda hid=h['id_horario']: self.borrar_horario(hid)).pack(side="right", padx=10)

    def guardar_horario(self):
        if not self.profesor_seleccionado:
            mostrar_advertencia("Atención", "Primero selecciona a alguien de la lista.", master=self)
            return
        try:
            entrada, salida = ops.validar_turno(self.ent_entrada.get(), self.ent_salida.get())
        except ValueError as e:
            mostrar_advertencia("Atención", str(e), master=self)
            return
        id_dia = self.DIAS_MAPPING[self.cmb_dia.get()]
        prof = self.profesor_seleccionado
        try:
            estado, existente = ops.revisar_turno(db.obtener_horarios_profesor(prof['id_profesor']), id_dia, entrada, salida)
            if estado == "repetido":
                mostrar_advertencia("Turno repetido", f"{prof['nombre'].title()} ya tiene ese turno el {self.cmb_dia.get()}.", master=self)
                return
            if estado == "traslape" and not mostrar_pregunta(
                    "Turno traslapado", f"{prof['nombre'].title()} ya tiene {self.cmb_dia.get()} {existente['hora_entrada']}–{existente['hora_salida']}, "
                    f"que se traslapa con {entrada}–{salida}.\n\n¿Agregarlo de todos modos?", master=self):
                return
            db.agregar_horario(prof['id_profesor'], id_dia, entrada, salida)
            self.ent_entrada.delete(0, 'end')
            self.ent_salida.delete(0, 'end')
            self.cargar_horarios_profesor()
        except Exception as e:
            mostrar_error("Error", f"No se pudo guardar el horario:\n{e}", master=self)

    def borrar_horario(self, id_horario):
        try:
            db.eliminar_horario(id_horario)
            self.cargar_horarios_profesor()
        except Exception as e:
            mostrar_error("Error", f"No se pudo eliminar el bloque:\n{e}", master=self)

    # ───────────── Selección múltiple y acciones en bloque ─────────────

    def _construir_barra_seleccion(self, panel):
        fila = ctk.CTkFrame(panel, fg_color="transparent")
        fila.grid(row=3, column=0, sticky="ew", padx=15, pady=(0, 6))
        fila.grid_columnconfigure(0, weight=1)

        self.var_todos = ctk.BooleanVar(value=False)
        self.chk_todos = ctk.CTkCheckBox(
            fila, text="Seleccionar todos los resultados", variable=self.var_todos, command=self.alternar_todos,
            checkbox_width=20, checkbox_height=20, corner_radius=5, fg_color=colores.ACENTO, hover_color=colores.ACENTO_HOVER,
            border_color=colores.BORDE_CLARO, font=fuentes.pequena(size=11), text_color=colores.TEXTO_SECUNDARIO,
        )
        self.chk_todos.grid(row=0, column=0, sticky="w")

        self.btn_limpiar_sel = ctk.CTkButton(
            fila, text="", height=24, corner_radius=7, font=fuentes.boton(size=11), fg_color="transparent",
            hover_color=colores.NEUTRO, text_color=colores.ACENTO, command=self.limpiar_seleccion,
        )
        self.btn_limpiar_sel.grid(row=0, column=1, sticky="e")

        self.barra_acciones = ctk.CTkFrame(panel, corner_radius=12, fg_color=colores.BG_PANEL_ALT, border_width=1, border_color=colores.BORDE_CLARO)
        self.barra_acciones.grid(row=4, column=0, sticky="ew", padx=15, pady=(0, 8))
        acciones = (("✏ Área/Tipo", "datos", colores.ACENTO, colores.ACENTO_HOVER),
                    ("＋ Turno", "asignar", colores.EXITO, colores.EXITO_HOVER),
                    ("－ Turno", "quitar", colores.ADVERTENCIA, colores.ADVERTENCIA_HOVER),
                    ("🧹 Limpiar", "limpiar", colores.NEUTRO, colores.NEUTRO_HOVER),
                    ("🗑 Eliminar", "eliminar", colores.PELIGRO, colores.PELIGRO_HOVER))
        for col, (texto, accion, color, hover) in enumerate(acciones):
            self.barra_acciones.grid_columnconfigure(col, weight=1, uniform="acciones")
            ctk.CTkButton(
                self.barra_acciones, text=texto, width=1, height=32, corner_radius=8, font=fuentes.boton(size=11),
                fg_color=color, hover_color=hover, command=lambda a=accion: self.abrir_accion_bloque(a),
            ).grid(row=0, column=col, sticky="ew", padx=4, pady=8)
        self.barra_acciones.grid_remove()

    def _estilo_tarjeta(self, prof):
        foco = bool(self.profesor_seleccionado and self.profesor_seleccionado['id_profesor'] == prof['id_profesor'])
        destacado = foco or prof['id_profesor'] in self.seleccion
        return (dict(fg_color=colores.COLOR_SELECCIONADO if destacado else colores.COLOR_TARJETA,
                     border_color=colores.COLOR_SELECCIONADO_BORDE if foco else colores.COLOR_TARJETA_BORDE,
                     border_width=2 if foco else 1),
                colores.COLOR_TEXTO_AREA_SEL if destacado else colores.COLOR_TEXTO_AREA)

    def _pintar_tarjetas(self):
        inicio = (self.pagina_actual - 1) * self.ELEMENTOS_POR_PAGINA
        for item, prof in zip(self.pool_tarjetas, self.profesores_filtrados[inicio:inicio + self.ELEMENTOS_POR_PAGINA]):
            estilo, color_area = self._estilo_tarjeta(prof)
            item["frame"].configure(**estilo)
            item["lbl_area"].configure(text_color=color_area)

    def alternar_seleccion(self, id_profesor, marcado):
        (self.seleccion.add if marcado else self.seleccion.discard)(id_profesor)
        self._pintar_tarjetas()
        self._actualizar_barra_seleccion()

    def alternar_todos(self):
        ids = {p['id_profesor'] for p in self.profesores_filtrados}
        self.seleccion = (self.seleccion | ids) if self.var_todos.get() else (self.seleccion - ids)
        self.renderizar_pagina()

    def limpiar_seleccion(self):
        self.seleccion.clear()
        self.renderizar_pagina()

    def _actualizar_barra_seleccion(self):
        n, total = len(self.seleccion), len(self.profesores_filtrados)
        self.chk_todos.configure(text=f"Seleccionar los {total} resultado(s)" if total != 1 else "Seleccionar el resultado")
        self.var_todos.set(total > 0 and all(p['id_profesor'] in self.seleccion for p in self.profesores_filtrados))
        if n:
            self.btn_limpiar_sel.configure(text=f"{n} seleccionado(s)   ✕ Limpiar")
            self.btn_limpiar_sel.grid()
            self.barra_acciones.grid()
        else:
            self.btn_limpiar_sel.grid_remove()
            self.barra_acciones.grid_remove()

    def abrir_accion_bloque(self, accion):
        profesores = [p for p in self.profesores_cache if p['id_profesor'] in self.seleccion]
        if not profesores:
            mostrar_advertencia("Atención", "Marca al menos un docente con la casilla de su tarjeta.", master=self)
            return
        try:
            horarios = ops.cargar_horarios(profesores)
        except Exception as e:
            mostrar_error("Error de Conexión", ops.traducir_error(e), master=self)
            return
        VentanaBloque(self, accion, profesores, horarios, on_success_callback=self._tras_bloque)

    def _tras_bloque(self):
        self.cargar_lista_profesores()
        if self.profesor_seleccionado:
            self.cargar_horarios_profesor()

    def cargar_archivo_masivo(self):
        VentanaImportar(self, on_success_callback=self.cargar_lista_profesores)

if __name__ == "__main__":
    app = VentanaGestionDocentes()
    app.mainloop()