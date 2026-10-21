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

class FormularioHorarioWidget(ctk.CTkFrame):
    """Componente aislado para la gestión visual del formulario de turnos."""
    def __init__(self, parent, dias_mapping, on_guardar):
        super().__init__(parent, corner_radius=12, fg_color=colores.BG_PANEL_ALT, border_width=1, border_color=colores.BORDE_SUAVE)
        self.dias_mapping = dias_mapping
        self.on_guardar = on_guardar
        self.id_horario_editando = None

        self._construir_interfaz()

    def _construir_interfaz(self):
        self.cmb_dia = ctk.CTkOptionMenu(
            self, values=list(self.dias_mapping.keys()), width=110, height=34,
            font=fuentes.cuerpo(size=12), fg_color=colores.BG_ENTRADA,
            button_color=colores.ACENTO, button_hover_color=colores.ACENTO_HOVER,
        )
        self.cmb_dia.pack(side="left", padx=(12, 6), pady=8)

        self.ent_entrada = ctk.CTkEntry(
            self, width=80, height=34, placeholder_text="07:00",
            font=fuentes.cuerpo(size=13), fg_color=colores.BG_ENTRADA, border_color=colores.BORDE,
        )
        self.ent_entrada.pack(side="left", padx=4, pady=8)
        aplicar_formato_hora(self.ent_entrada)

        self.ent_salida = ctk.CTkEntry(
            self, width=80, height=34, placeholder_text="12:00",
            font=fuentes.cuerpo(size=13), fg_color=colores.BG_ENTRADA, border_color=colores.BORDE,
        )
        self.ent_salida.pack(side="left", padx=4, pady=8)
        aplicar_formato_hora(self.ent_salida)

        self.btn_accion_horario = ctk.CTkButton(
            self, text="+ Agregar", command=self.on_guardar,
            height=34, corner_radius=9, font=fuentes.boton(size=12),
            fg_color=colores.EXITO, hover_color=colores.EXITO_HOVER, width=90
        )
        self.btn_accion_horario.pack(side="left", padx=6, pady=8)

        self.btn_cancelar_edicion = ctk.CTkButton(
            self, text="✕", width=34, height=34, corner_radius=9, font=fuentes.boton(size=12),
            fg_color=colores.NEUTRO, hover_color=colores.NEUTRO_HOVER
        )


class VentanaGestionDocentes(ctk.CTkToplevel):
    DIAS_MAPPING = {"Lunes": 1, "Martes": 2, "Miércoles": 3, "Jueves": 4, "Viernes": 5}
    MAX_POOL = 50

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.profesores_cache = []
        self.profesores_filtrados = []
        self.profesor_seleccionado = None       
        self.seleccion = set()                  
        self.pagina_actual = 1
        self.elementos_por_pagina = 10
        self.pool_tarjetas = []
        self.id_horario_editando = None         
        
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
        
        self.protocol("WM_DELETE_WINDOW", self.cerrar_ventana)

        self.grid_columnconfigure(0, weight=4, uniform="paneles")
        self.grid_columnconfigure(1, weight=5, uniform="paneles")
        self.grid_rowconfigure(0, weight=1)

    def cerrar_ventana(self):
        """Destruye la ventana y libera recursos de forma controlada."""
        self.destroy()

    def regresar_al_menu(self):
        if self.parent:
            self.parent.wm_state('normal')
            self.parent.deiconify()
        self.cerrar_ventana()

    def _construir_panel_izquierdo(self):
        panel = ctk.CTkFrame(self, corner_radius=16, fg_color=colores.BG_PANEL, border_width=1, border_color=colores.BORDE)
        panel.grid(row=0, column=0, sticky="nsew", padx=(15, 8), pady=15)
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(5, weight=1)

        encabezado = ctk.CTkFrame(panel, fg_color="transparent", height=45)
        encabezado.grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 8))
        encabezado.grid_propagate(False)

        ctk.CTkLabel(
            encabezado, text="Gestión docente", 
            font=fuentes.seccion(size=17), text_color=colores.TEXTO_PRIMARIO
        ).place(relx=0.5, rely=0.5, anchor="center")

        btn_frame_acciones = ctk.CTkFrame(panel, fg_color="transparent")
        btn_frame_acciones.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 6))
        btn_frame_acciones.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            btn_frame_acciones, text="Nuevo docente", command=self.abrir_ventana_registro,
            font=fuentes.boton(size=13), height=38, corner_radius=10,
            fg_color=colores.ACENTO, hover_color=colores.ACENTO_HOVER,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 5))

        ctk.CTkButton(
            btn_frame_acciones, text="Importar datos", command=self.cargar_archivo_masivo,
            font=fuentes.boton(size=13), height=38, corner_radius=10,
            fg_color=colores.EXITO, hover_color=colores.EXITO_HOVER,
        ).grid(row=0, column=1, sticky="ew", padx=(5, 0))

        self.var_busqueda = ctk.StringVar()
        self.var_busqueda.trace_add("write", self.filtrar_profesores)
        ctk.CTkEntry(
            panel, textvariable=self.var_busqueda, placeholder_text="Buscar por nombre o área...",
            placeholder_text_color=colores.TEXTO_SECUNDARIO,
            height=36, corner_radius=10, font=fuentes.cuerpo(size=12),
            fg_color=colores.BG_ENTRADA, border_color=colores.BORDE,
        ).grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 6))

        self._construir_barra_seleccion(panel)

        self.container_profesores = ctk.CTkScrollableFrame(panel, fg_color="transparent")
        self.container_profesores.grid(row=5, column=0, sticky="nsew", padx=10, pady=(0, 5))
        self.container_profesores.grid_columnconfigure(0, weight=1)

        for r in range(self.MAX_POOL):
            self.container_profesores.grid_rowconfigure(r, weight=0)

        self._crear_pool_tarjetas()

        nav_frame = ctk.CTkFrame(panel, fg_color="transparent")
        nav_frame.grid(row=6, column=0, sticky="ew", padx=15, pady=(4, 10))
        nav_frame.grid_columnconfigure(1, weight=1)

        self.btn_prev = ctk.CTkButton(
            nav_frame, text="←", width=36, height=32, corner_radius=8,
            font=fuentes.cuerpo(size=12), fg_color=colores.NEUTRO, hover_color=colores.NEUTRO_HOVER,
            command=self.pagina_anterior,
        )
        self.btn_prev.grid(row=0, column=0, sticky="w")
        
        centro_nav = ctk.CTkFrame(nav_frame, fg_color="transparent")
        centro_nav.grid(row=0, column=1, sticky="ew")
        
        self.lbl_paginacion = ctk.CTkLabel(centro_nav, text="Pág 1 / 1", font=fuentes.boton(size=12), text_color=colores.TEXTO_SECUNDARIO)
        self.lbl_paginacion.pack(side="left", padx=8)

        ctk.CTkLabel(centro_nav, text="Ver:", font=fuentes.pequena(size=10), text_color=colores.TEXTO_TENUE).pack(side="left", padx=(12, 2))
        self.cmb_limite = ctk.CTkOptionMenu(
            centro_nav, values=["10", "25", "50"], width=65, height=28,
            font=fuentes.pequena(size=11), fg_color=colores.BG_ENTRADA,
            button_color=colores.ACENTO, button_hover_color=colores.ACENTO_HOVER,
            command=self.cambiar_limite_paginacion
        )
        self.cmb_limite.set("10")
        self.cmb_limite.pack(side="left")

        self.btn_next = ctk.CTkButton(
            nav_frame, text="→", width=36, height=32, corner_radius=8,
            font=fuentes.cuerpo(size=12), fg_color=colores.NEUTRO, hover_color=colores.NEUTRO_HOVER,
            command=self.pagina_siguiente,
        )
        self.btn_next.grid(row=0, column=2, sticky="e")

    def _crear_pool_tarjetas(self):
        """Crea un pool estático de 50 tarjetas con enfoque obligatorio al hacer clic en Editar/Eliminar."""
        for i in range(self.MAX_POOL):
            card = ctk.CTkFrame(self.container_profesores, fg_color=colores.COLOR_TARJETA, corner_radius=8, border_width=1, border_color=colores.COLOR_TARJETA_BORDE, cursor="hand2", height=42)
            card.grid_propagate(False)
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

    def abrir_ventana_registro(self):
        if self.id_horario_editando is not None:
            if not mostrar_pregunta("Edición Pendiente", "Tiene un horario en proceso de edición sin guardar. ¿Desea descartar los cambios y registrar un nuevo docente?", master=self):
                return
            self.cancelar_edicion_horario()
        VentanaCrudProfesor(self, on_success_callback=self.cargar_lista_profesores)

    def cargar_archivo_masivo(self):
        if self.id_horario_editando is not None:
            if not mostrar_pregunta("Edición Pendiente", "Tiene un horario en proceso de edición sin guardar. ¿Desea descartar los cambios e importar datos?", master=self):
                return
            self.cancelar_edicion_horario()
        VentanaImportar(self, on_success_callback=self.cargar_lista_profesores)

    def abrir_ventana_edicion(self, profesor):
        if self.profesor_seleccionado and self.profesor_seleccionado['id_profesor'] != profesor['id_profesor']:
            if not mostrar_pregunta(
                "Cambio de Docente", 
                f"Actualmente está viendo los horarios de '{self.profesor_seleccionado['nombre'].title()}'.\n\n¿Desea cambiar el enfoque y editar a '{profesor['nombre'].title()}'?", 
                master=self
            ):
                return

        if self.id_horario_editando is not None:
            if not mostrar_pregunta("Edición Pendiente", "Tiene un horario en proceso de edición sin guardar. ¿Desea descartar los cambios y editar este docente?", master=self):
                return
            self.cancelar_edicion_horario()

        self.seleccionar_profesor(profesor)
        VentanaCrudProfesor(self, profesor_a_editar=profesor, on_success_callback=self.cargar_lista_profesores)

    def eliminar_docente(self, profesor):
        if self.profesor_seleccionado and self.profesor_seleccionado['id_profesor'] != profesor['id_profesor']:
            if not mostrar_pregunta(
                "Cambio de Docente", 
                f"Actualmente está viendo los horarios de '{self.profesor_seleccionado['nombre'].title()}'.\n\n¿Desea cambiar el enfoque y eliminar a '{profesor['nombre'].title()}'?", 
                master=self
            ):
                return

        if self.id_horario_editando is not None:
            if not mostrar_pregunta("Edición Pendiente", "Tiene un horario en proceso de edición sin guardar. ¿Desea descartar los cambios y proceder con la eliminación?", master=self):
                return
            self.cancelar_edicion_horario()

        self.seleccionar_profesor(profesor)

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
        """Selecciona un docente sincronizando el foco y protegiendo ediciones pendientes."""
        if self.id_horario_editando is not None:
            if not mostrar_pregunta("Edición Pendiente", "Tiene un horario en proceso de edición sin guardar. ¿Desea descartar los cambios y cambiar de docente?", master=self):
                return False
        
        self.profesor_seleccionado = profesor
        self.lbl_prof_seleccionado.configure(text=f"Horario: {profesor['nombre'].title()}")
        self.cancelar_edicion_horario()
        self._pintar_tarjetas()
        self.cargar_horarios_profesor()
        return True

    def cargar_horarios_profesor(self):
        for child in self.scroll_horarios.winfo_children():
            child.destroy()
        if not self.profesor_seleccionado:
            return
        horarios = db.obtener_horarios_profesor(self.profesor_seleccionado['id_profesor'])
        if not horarios:
            ctk.CTkLabel(self.scroll_horarios, text="No hay horarios asignados", font=fuentes.cuerpo(size=13), text_color=colores.TEXTO_TENUE).pack(pady=20)
            return
        for h in horarios:
            row = ctk.CTkFrame(self.scroll_horarios, fg_color=colores.COLOR_TARJETA, corner_radius=10, border_width=1, border_color=colores.COLOR_TARJETA_BORDE, height=40)
            row.pack(fill="x", pady=4, padx=2)
            row.grid_columnconfigure(0, weight=1)
            
            texto_horario = f"{h['nombre_dia']}  ·  Entrada {h['hora_entrada']} hrs  ·  Salida {h['hora_salida']} hrs"
            ctk.CTkLabel(row, text=texto_horario, font=fuentes.cuerpo(size=13), text_color=colores.TEXTO_PRIMARIO, anchor="w").pack(side="left", padx=15, pady=8, fill="x", expand=True)
            
            ctk.CTkButton(row, text="Eliminar", width=65, height=28, corner_radius=7, font=fuentes.pequena(size=11), fg_color=colores.COLOR_BTN_ELIMINAR, hover_color=colores.COLOR_BTN_ELIMINAR_HOVER, command=lambda hid=h['id_horario']: self.borrar_horario(hid)).pack(side="right", padx=10)
            ctk.CTkButton(row, text="Editar", width=55, height=28, corner_radius=7, font=fuentes.pequena(size=11), fg_color=colores.COLOR_BTN_EDITAR, hover_color=colores.COLOR_BTN_EDITAR_HOVER, command=lambda turno=h: self.iniciar_edicion_horario(turno)).pack(side="right", padx=2)

    def iniciar_edicion_horario(self, turno):
        self.id_horario_editando = turno['id_horario']
        self.form_horario.id_horario_editando = self.id_horario_editando
        self.cmb_dia.set(turno['nombre_dia'])
        self.ent_entrada.delete(0, 'end')
        self.ent_entrada.insert(0, turno['hora_entrada'])
        self.ent_salida.delete(0, 'end')
        self.ent_salida.insert(0, turno['hora_salida'])
        
        self.btn_accion_horario.configure(text="Guardar", fg_color=colores.ACENTO, hover_color=colores.ACENTO_HOVER)
        self.btn_cancelar_edicion.pack(side="left", padx=(0, 6), pady=8)

    def cancelar_edicion_horario(self):
        self.id_horario_editando = None
        self.form_horario.id_horario_editando = None
        self.ent_entrada.delete(0, 'end')
        self.ent_salida.delete(0, 'end')
        self.btn_accion_horario.configure(text="Agregar", fg_color=colores.EXITO, hover_color=colores.EXITO_HOVER)
        self.btn_cancelar_edicion.pack_forget()

    def guardar_o_actualizar_horario(self):
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
            if self.id_horario_editando is None:
                estado, existente = ops.revisar_turno(db.obtener_horarios_profesor(prof['id_profesor']), id_dia, entrada, salida)
                if estado == "repetido":
                    mostrar_advertencia("Turno repetido", f"{prof['nombre'].title()} ya tiene ese turno el {self.cmb_dia.get()}.", master=self)
                    return
                if estado == "traslape" and not mostrar_pregunta(
                        "Turno con conflicto de horario", f"{prof['nombre'].title()} ya tiene {self.cmb_dia.get()} {existente['hora_entrada']}–{existente['hora_salida']}, "
                        f"que coincide con {entrada}–{salida}.\n\n¿Agregarlo de todos modos?", master=self):
                    return
                db.agregar_horario(prof['id_profesor'], id_dia, entrada, salida)
            else:
                db.actualizar_horario(self.id_horario_editando, id_dia, entrada, salida)
                self.cancelar_edicion_horario()

            self.ent_entrada.delete(0, 'end')
            self.ent_salida.delete(0, 'end')
            self.cargar_horarios_profesor()
        except Exception as e:
            mostrar_error("Error", f"No se pudo guardar el horario:\n{e}", master=self)

    def borrar_horario(self, id_horario):
        try:
            db.eliminar_horario(id_horario)
            if self.id_horario_editando == id_horario:
                self.cancelar_edicion_horario()
            self.cargar_horarios_profesor()
        except Exception as e:
            mostrar_error("Error", f"No se pudo eliminar el bloque:\n{e}", master=self)

    def _construir_barra_seleccion(self, panel):
        fila = ctk.CTkFrame(panel, fg_color="transparent")
        fila.grid(row=3, column=0, sticky="ew", padx=15, pady=(0, 4))
        fila.grid_columnconfigure(0, weight=1)
        fila.grid_columnconfigure(1, weight=0)

        self.var_todos = ctk.BooleanVar(value=False)
        self.chk_todos = ctk.CTkCheckBox(
            fila, text="Seleccionar todos los resultados", variable=self.var_todos, command=self.alternar_todos,
            checkbox_width=18, checkbox_height=18, corner_radius=4, fg_color=colores.ACENTO, hover_color=colores.ACENTO_HOVER,
            border_color=colores.BORDE_CLARO, font=fuentes.pequena(size=11), text_color=colores.TEXTO_SECUNDARIO,
        )
        self.chk_todos.grid(row=0, column=0, sticky="w")

        # Frame derecho para contador y botón limpiar selección
        der_sel_frame = ctk.CTkFrame(fila, fg_color="transparent")
        der_sel_frame.grid(row=0, column=1, sticky="e")

        self.lbl_contador_sel = ctk.CTkLabel(
            der_sel_frame, text="", font=fuentes.pequena(size=10), text_color=colores.TEXTO_SECUNDARIO
        )
        self.lbl_contador_sel.pack(side="left", padx=(0, 6))

        self.btn_limpiar_sel = ctk.CTkButton(
            der_sel_frame, text="Limpiar", width=55, height=22, corner_radius=5,
            font=fuentes.pequena(size=10), fg_color=colores.NEUTRO, hover_color=colores.NEUTRO_HOVER,
            command=self.limpiar_seleccion
        )
        self.btn_limpiar_sel.pack(side="left")

        self.barra_acciones = ctk.CTkFrame(panel, corner_radius=10, fg_color=colores.BG_PANEL_ALT, border_width=1, border_color=colores.BORDE_CLARO)
        self.barra_acciones.grid(row=4, column=0, sticky="ew", padx=15, pady=(0, 6))
        
        acciones = (
            ("Datos", "datos", colores.ACENTO, colores.ACENTO_HOVER),
            ("Agregar horario(s)", "asignar", colores.EXITO, colores.EXITO_HOVER),
            ("Quitar horario(s)", "quitar", colores.ADVERTENCIA, colores.ADVERTENCIA_HOVER),
            ("Eliminar", "eliminar", colores.PELIGRO, colores.PELIGRO_HOVER)
        )
        
        for col, (texto, accion, color, hover) in enumerate(acciones):
            self.barra_acciones.grid_columnconfigure(col, weight=1, uniform="acciones")
            ctk.CTkButton(
                self.barra_acciones, text=texto, width=1, height=30, corner_radius=7, font=fuentes.boton(size=11),
                fg_color=color, hover_color=hover, command=lambda a=accion: self.abrir_accion_bloque(a),
            ).grid(row=0, column=col, sticky="ew", padx=3, pady=6)
        self.barra_acciones.grid_remove()

    def limpiar_seleccion(self):
        """Limpia todos los elementos seleccionados globalmente."""
        self.seleccion.clear()
        self.var_todos.set(False)
        self.renderizar_pagina()
        self._actualizar_barra_seleccion()

    def _estilo_tarjeta(self, prof):
        foco = bool(self.profesor_seleccionado and self.profesor_seleccionado['id_profesor'] == prof['id_profesor'])
        destacado = foco or prof['id_profesor'] in self.seleccion
        return (dict(fg_color=colores.COLOR_SELECCIONADO if destacado else colores.COLOR_TARJETA,
                     border_color=colores.COLOR_SELECCIONADO_BORDE if foco else colores.COLOR_TARJETA_BORDE,
                     border_width=2 if foco else 1),
                colores.COLOR_TEXTO_AREA_SEL if destacado else colores.COLOR_TEXTO_AREA)

    def _pintar_tarjetas(self):
        inicio = (self.pagina_actual - 1) * self.elementos_por_pagina
        fin = inicio + self.elementos_por_pagina
        for item, prof in zip(self.pool_tarjetas[:self.elementos_por_pagina], self.profesores_filtrados[inicio:fin]):
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

    def _actualizar_barra_seleccion(self):
        n, total = len(self.seleccion), len(self.profesores_filtrados)
        self.chk_todos.configure(text=f"Seleccionar los {total} resultado(s)" if total != 1 else "Seleccionar el resultado")
        self.var_todos.set(total > 0 and all(p['id_profesor'] in self.seleccion for p in self.profesores_filtrados))
        
        if n:
            self.barra_acciones.grid()
            self.lbl_contador_sel.configure(text=f"{n} sel.")
            self.lbl_contador_sel.pack(side="left", padx=(0, 6))
            self.btn_limpiar_sel.pack(side="left")
        else:
            self.barra_acciones.grid_remove()
            self.lbl_contador_sel.pack_forget()
            self.btn_limpiar_sel.pack_forget()

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
        self.seleccion.clear()
        self.cargar_lista_profesores()

    def _construir_panel_derecho(self):
        panel = ctk.CTkFrame(self, corner_radius=16, fg_color=colores.BG_PANEL, border_width=1, border_color=colores.BORDE)
        panel.grid(row=0, column=1, sticky="nsew", padx=(7, 15), pady=15)
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(3, weight=1)

        encabezado = ctk.CTkFrame(panel, fg_color="transparent", height=45)
        encabezado.grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 8))
        encabezado.grid_propagate(False)

        self.lbl_prof_seleccionado = ctk.CTkLabel(encabezado, text="Horario Semanal", font=fuentes.seccion(size=17), text_color=colores.TEXTO_PRIMARIO)
        self.lbl_prof_seleccionado.place(relx=0.5, rely=0.5, anchor="center")

        btn_volver_menu = ctk.CTkButton(
            encabezado, text="Volver al menú", width=120, height=32, corner_radius=8,
            font=fuentes.boton(size=12), fg_color=colores.NEUTRO,
            hover_color=colores.NEUTRO_HOVER, command=self.regresar_al_menu
        )
        btn_volver_menu.place(relx=1.0, rely=0.5, anchor="e")
        
        self.form_horario = FormularioHorarioWidget(
            panel, 
            dias_mapping=self.DIAS_MAPPING, 
            on_guardar=self.guardar_o_actualizar_horario
        )
        self.form_horario.grid(row=1, column=0, sticky="ew", padx=15, pady=(4, 12))

        self.cmb_dia = self.form_horario.cmb_dia
        self.ent_entrada = self.form_horario.ent_entrada
        self.ent_salida = self.form_horario.ent_salida
        self.btn_accion_horario = self.form_horario.btn_accion_horario
        self.btn_cancelar_edicion = self.form_horario.btn_cancelar_edicion
        self.btn_cancelar_edicion.configure(command=self.cancelar_edicion_horario)

        self.scroll_horarios = ctk.CTkScrollableFrame(panel, fg_color="transparent")
        self.scroll_horarios.grid(row=3, column=0, sticky="nsew", padx=10, pady=(0, 15))

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
            self.lbl_prof_seleccionado.configure(text=f"Horario: {actual['nombre'].title()}" if actual else "Horario semanal")
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
        self._resetear_scroll()

    def cambiar_limite_paginacion(self, valor):
        self.elementos_por_pagina = int(valor)
        self.pagina_actual = 1
        self.renderizar_pagina()
        self._resetear_scroll()

    def total_paginas(self):
        return math.ceil(len(self.profesores_filtrados) / self.elementos_por_pagina) or 1

    def renderizar_pagina(self):
        inicio = (self.pagina_actual - 1) * self.elementos_por_pagina
        pagina_items = self.profesores_filtrados[inicio:inicio + self.elementos_por_pagina]

        for i in range(self.MAX_POOL):
            item = self.pool_tarjetas[i]
            card = item["frame"]
            lbl_nombre = item["lbl_nombre"]
            lbl_area = item["lbl_area"]

            if i < len(pagina_items):
                prof = pagina_items[i]
                card.profesor_asociado = prof
                
                estilo_tarjeta, color_area = self._estilo_tarjeta(prof)
                lbl_nombre.configure(text=f"{prof['nombre'].title()}")
                lbl_turno = prof.get('turno', 'Matutino')
                lbl_area.configure(text=f"{prof['area'].title()}  •  {lbl_turno}")
                card.configure(**estilo_tarjeta, cursor="hand2")
                lbl_area.configure(text_color=color_area)

                item["var_chk"].set(prof['id_profesor'] in self.seleccion)
                item["chk"].configure(command=lambda i=prof['id_profesor'], v=item["var_chk"]: self.alternar_seleccion(i, v.get()))
                item["chk"].grid()

                item["btn_edit"].configure(command=lambda p=prof: self.abrir_ventana_edicion(p))
                item["btn_del"].configure(command=lambda p=prof: self.eliminar_docente(p))

                card.grid(row=i, column=0, sticky="ew", pady=1, padx=2)
                item["btn_frame"].grid()
            else:
                card.profesor_asociado = None
                lbl_nombre.configure(text="")
                lbl_area.configure(text="")
                item["btn_frame"].grid_remove()
                item["chk"].grid_remove()
                card.grid_remove()

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
            self._resetear_scroll()

    def pagina_siguiente(self):
        if self.pagina_actual < self.total_paginas():
            self.pagina_actual += 1
            self.renderizar_pagina()
            self._resetear_scroll()

    def _resetear_scroll(self):
        """Devuelve el scroll del contenedor de profesores de vuelta al inicio (arriba)."""
        try:
            self.container_profesores._parent_canvas.yview_moveto(0)
        except Exception:
            pass